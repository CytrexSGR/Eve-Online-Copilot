# Production System Design

**Date:** 2025-12-17
**Status:** Approved for Implementation
**Author:** Claude Code with User Direction

## Overview

Complete redesign of the production system into three independent, specialized modules that transform EVE SDE raw data into a production-optimized database structure.

## Problem Statement

Current system recalculates production chains on every request using raw EVE SDE tables. This is inefficient and doesn't scale. We need a persistent, queryable production database that:

1. Pre-calculates material dependencies
2. Tracks economics per region
3. Manages production workflows
4. Enables make-or-buy decisions by users

## System Architecture

### Three Independent Modules

**1. Production Chains** - Material dependency graph to raw materials
- Maps complete production chains from finished products (Drake) through intermediate products (Components) to raw materials (Minerals)
- Stores both direct dependencies (`production_dependencies`) and pre-calculated complete chains (`production_chains`)
- Static data, changes only with CCP blueprint updates

**2. Production Economics** - Economic data per item and region
- Calculates production costs (Materials + Job Costs)
- Compares with market prices
- Provides ROI data
- Extends existing `manufacturing_opportunities` with detailed analysis and multi-region support
- Dynamic data, updates every 30 minutes

**3. Production Workflow** - Production job management
- Tracks active production jobs
- Material inventory management
- Answers "What can I build with my assets?"
- Character-specific with skill consideration
- Event-driven updates

### Update Strategy

- **Chains:** Static, rebuild on-demand via admin API when CCP updates blueprints
- **Economics:** Dynamic, update cycle analogous to `regional_price_fetcher` (every 30 min), uses existing `market_prices_cache`
- **Workflow:** Event-driven, updates on user actions (create job, complete job)

### Batch Processing

Bottom-up hierarchy ensures all dependencies are available:

1. Raw Materials (Minerals, PI, Ice)
2. Basic Components (Construction Parts, etc.)
3. T1 Items (Ships, Modules, Ammo)
4. T2 Items
5. T3 & Special Items

Each batch is testable and deployable incrementally.

## Database Schema

### Production Chains Tables

```sql
-- Direct Material Dependencies (1:1 mapping from SDE)
CREATE TABLE production_dependencies (
  id SERIAL PRIMARY KEY,
  item_type_id INT NOT NULL,           -- Item being produced
  material_type_id INT NOT NULL,       -- Material required
  base_quantity INT NOT NULL,          -- Quantity without ME
  activity_id INT NOT NULL,            -- 1=Manufacturing, 3=Research, 8=Invention
  is_raw_material BOOLEAN DEFAULT false, -- True if material has no further dependencies
  created_at TIMESTAMP DEFAULT NOW(),

  FOREIGN KEY (item_type_id) REFERENCES "invTypes"("typeID"),
  FOREIGN KEY (material_type_id) REFERENCES "invTypes"("typeID")
);

CREATE INDEX idx_prod_deps_item ON production_dependencies(item_type_id);
CREATE INDEX idx_prod_deps_material ON production_dependencies(material_type_id);

-- Pre-calculated complete chains to raw materials
CREATE TABLE production_chains (
  id SERIAL PRIMARY KEY,
  item_type_id INT NOT NULL,            -- Final product (e.g. Drake)
  raw_material_type_id INT NOT NULL,    -- Raw material (e.g. Tritanium)
  base_quantity DECIMAL(20,2) NOT NULL, -- Total quantity WITHOUT ME
  chain_depth INT NOT NULL,             -- Number of production steps
  path TEXT,                            -- "648->12345->34" for debugging
  created_at TIMESTAMP DEFAULT NOW(),

  FOREIGN KEY (item_type_id) REFERENCES "invTypes"("typeID"),
  FOREIGN KEY (raw_material_type_id) REFERENCES "invTypes"("typeID")
);

CREATE INDEX idx_prod_chains_item ON production_chains(item_type_id);
CREATE UNIQUE INDEX idx_prod_chains_unique ON production_chains(item_type_id, raw_material_type_id);
```

### Production Economics Table

```sql
CREATE TABLE production_economics (
  id SERIAL PRIMARY KEY,
  type_id INT NOT NULL,
  region_id INT NOT NULL,

  -- Costs (base values)
  material_cost DECIMAL(20,2) NOT NULL,      -- Cost of all materials (ME 0)
  base_job_cost DECIMAL(20,2) NOT NULL,      -- Average system cost for region

  -- Market prices
  market_sell_price DECIMAL(20,2),           -- Lowest sell order
  market_buy_price DECIMAL(20,2),            -- Highest buy order

  -- Time
  base_production_time INT NOT NULL,         -- Seconds without TE/Skills

  -- Metadata
  market_volume_daily BIGINT DEFAULT 0,      -- Trading volume (optional)
  updated_at TIMESTAMP DEFAULT NOW(),

  FOREIGN KEY (type_id) REFERENCES "invTypes"("typeID"),
  UNIQUE(type_id, region_id)
);

CREATE INDEX idx_prod_econ_type ON production_economics(type_id);
CREATE INDEX idx_prod_econ_region ON production_economics(region_id);
CREATE INDEX idx_prod_econ_updated ON production_economics(updated_at);

-- View for calculated values (profit, ROI)
CREATE VIEW production_economics_calculated AS
SELECT
  id,
  type_id,
  region_id,
  material_cost,
  base_job_cost,
  material_cost + base_job_cost AS total_cost,
  market_sell_price,
  market_buy_price,
  market_sell_price - (material_cost + base_job_cost) AS profit_sell,
  market_buy_price - (material_cost + base_job_cost) AS profit_buy,
  CASE
    WHEN (material_cost + base_job_cost) > 0
    THEN ((market_sell_price - (material_cost + base_job_cost)) / (material_cost + base_job_cost) * 100)
    ELSE 0
  END AS roi_sell_percent,
  CASE
    WHEN (material_cost + base_job_cost) > 0
    THEN ((market_buy_price - (material_cost + base_job_cost)) / (material_cost + base_job_cost) * 100)
    ELSE 0
  END AS roi_buy_percent,
  base_production_time,
  updated_at
FROM production_economics;
```

### Production Workflow Tables

```sql
CREATE TABLE production_jobs (
  id SERIAL PRIMARY KEY,
  character_id BIGINT NOT NULL,

  -- Item & Blueprint
  item_type_id INT NOT NULL,
  blueprint_type_id INT NOT NULL,
  me_level INT NOT NULL DEFAULT 0,           -- Material Efficiency 0-10
  te_level INT NOT NULL DEFAULT 0,           -- Time Efficiency 0-20
  runs INT NOT NULL,

  -- Location
  facility_id BIGINT,                        -- Structure/Station ID
  system_id INT,                             -- Solar System

  -- Status
  status VARCHAR(20) NOT NULL DEFAULT 'planned', -- 'planned', 'active', 'completed', 'cancelled'

  -- Economics
  total_cost DECIMAL(20,2),
  expected_revenue DECIMAL(20,2),
  actual_revenue DECIMAL(20,2),              -- After sale

  -- Timestamps
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),

  FOREIGN KEY (item_type_id) REFERENCES "invTypes"("typeID"),
  FOREIGN KEY (blueprint_type_id) REFERENCES "invTypes"("typeID")
);

CREATE INDEX idx_prod_jobs_char ON production_jobs(character_id);
CREATE INDEX idx_prod_jobs_status ON production_jobs(status);
CREATE INDEX idx_prod_jobs_item ON production_jobs(item_type_id);

-- Job Materials (instead of JSONB)
CREATE TABLE production_job_materials (
  id SERIAL PRIMARY KEY,
  job_id INT NOT NULL,
  material_type_id INT NOT NULL,
  quantity_needed INT NOT NULL,
  decision VARCHAR(10) NOT NULL,             -- 'make' or 'buy'
  cost_per_unit DECIMAL(20,2),
  total_cost DECIMAL(20,2),
  acquired BOOLEAN DEFAULT false,

  FOREIGN KEY (job_id) REFERENCES production_jobs(id) ON DELETE CASCADE,
  FOREIGN KEY (material_type_id) REFERENCES "invTypes"("typeID")
);

CREATE INDEX idx_prod_job_mats_job ON production_job_materials(job_id);
```

## API Design

### Router Structure

```
routers/
├── production_chains.py    # Dependency graph & material lists
├── production_economics.py # Profitability analysis
└── production_workflow.py  # Job management
```

### Production Chains API

**GET /api/production/chains/{type_id}**
- Query: `?format=tree|flat`
- Returns: Complete dependency tree to raw materials
- Format tree: Hierarchical structure
- Format flat: Simple list

**GET /api/production/chains/{type_id}/materials**
- Query: `?me=10&runs=1`
- Returns: Flattened material list with ME adjustments
- Perfect for shopping lists

**GET /api/production/chains/{type_id}/direct**
- Returns: Only direct dependencies (1 level)

### Production Economics API

**GET /api/production/economics/{type_id}**
- Query: `?region_id=10000002&me=10&te=20`
- Returns: Profitability analysis for item
- Includes: costs, market prices, profit, ROI, production time

**GET /api/production/economics/opportunities**
- Query: `?region_id=10000002&min_roi=15&min_profit=1000000&limit=50`
- Returns: Profitable items matching filters
- Extends current `manufacturing_opportunities`

**GET /api/production/economics/{type_id}/regions**
- Returns: Multi-region comparison
- Shows best region for production

### Production Workflow API

**POST /api/production/workflow/jobs**
- Creates new production job
- Body: character_id, item_type_id, blueprint details, materials with make-or-buy decisions

**GET /api/production/workflow/jobs**
- Query: `?character_id=X&status=active`
- Returns: List of jobs

**PATCH /api/production/workflow/jobs/{job_id}**
- Updates job status
- Body: status, actual_revenue, etc.

**GET /api/production/workflow/buildable**
- Query: `?character_id=X`
- Returns: Items character can build with available assets

## Batch Processing

### Batch Hierarchy

```python
BATCH_HIERARCHY = [
    # Level 0: Raw Materials
    {
        "name": "raw_materials",
        "categories": [6, 1031, 1032, 1033, 1034, 1035],  # Minerals
        "market_groups": [1857, 1033]  # PI Materials, Ice Products
    },

    # Level 1: Basic Components
    {
        "name": "basic_components",
        "categories": [1136],  # Components
        "market_groups": [334, 873]  # Construction Components, Advanced Components
    },

    # Level 2: T1 Ships & Modules
    {
        "name": "t1_items",
        "categories": [6, 7, 8, 18],  # Ships, Modules, Charges, Drones
        "tech_level": 1
    },

    # Level 3: T2 Items
    {
        "name": "t2_items",
        "categories": [6, 7, 8, 18],
        "tech_level": 2
    },

    # Level 4: T3 & Special
    {
        "name": "advanced_items",
        "categories": [6],  # T3 Ships
        "tech_level": 3
    }
]
```

### Execution

```bash
python3 -m jobs.production_chain_builder --batch=raw_materials
python3 -m jobs.production_chain_builder --batch=basic_components
python3 -m jobs.production_chain_builder --batch=t1_items
# etc.
```

## Integration with Existing System

### Reuse Existing Components

1. **Pricing:** Uses `market_prices_cache` and `market_service.py`
   - No new pricing system needed

2. **ESI Client:** `esi_client.py` for character data (Assets, Skills, Blueprints)
   - `production_workflow` uses existing auth

3. **Database Connection:** `database.py` connection pool
   - All new services use `get_db_connection()`

4. **Cron Infrastructure:** Analogous to `batch_calculator.py`
   - `jobs/production_economics_updater.py` runs every 30 min
   - Uses existing logging structure

### Extends Existing Features

- `manufacturing_opportunities` becomes view on `production_economics`
- `production_simulator.py` uses `production_chains` instead of live calculation
- Shopping Lists can directly use `production_chains/{type_id}/materials`

## Service Layer Structure

```python
# services/production/chain_service.py
class ProductionChainService:
    def get_chain_tree(type_id: int, format: str = 'tree')
    def get_materials_list(type_id: int, me: int = 0, runs: int = 1)
    def get_direct_dependencies(type_id: int)
    def rebuild_chain(type_id: int)  # Admin function

# services/production/economics_service.py
class ProductionEconomicsService:
    def get_economics(type_id: int, region_id: int, me: int = 0, te: int = 0)
    def find_opportunities(region_id: int, min_roi: float, min_profit: float)
    def compare_regions(type_id: int)
    def update_economics(type_id: int, region_id: int)  # Cron job

# services/production/workflow_service.py
class ProductionWorkflowService:
    def create_job(character_id: int, job_data: dict)
    def get_jobs(character_id: int, status: str = None)
    def update_job(job_id: int, updates: dict)
    def get_buildable_items(character_id: int)
```

## Rollout Plan

### Phase 1: Schema & Batch Processing (Week 1)
- Migration: Create tables
- Implement: Batch builder script
- Run: Build chains for raw_materials + basic_components
- Test: Verify chain accuracy

### Phase 2: Chain API (Week 2)
- Implement: `ProductionChainService` + Repository
- Implement: `routers/production_chains.py`
- Test: API endpoints
- Deploy: Documentation

### Phase 3: Economics System (Week 3)
- Implement: `ProductionEconomicsService`
- Implement: Update cron job
- Implement: `routers/production_economics.py`
- Migrate: `manufacturing_opportunities` → View
- Run: Initial economics calculation

### Phase 4: Workflow System (Week 4)
- Implement: `ProductionWorkflowService`
- Implement: `routers/production_workflow.py`
- Test: End-to-end job creation
- Deploy: Frontend integration preparation

### Phase 5: Integration & Optimization (Week 5+)
- Refactor: `production_simulator.py` uses new chain data
- Frontend: Production Planner UI
- Performance: Index optimization
- Documentation: API docs update

## Key Design Decisions

### Why separate tables instead of JSONB?
- Better query performance
- Proper indexing
- Data integrity via foreign keys
- Easier to extend

### Why base_quantity only without pre-calculated ME?
- ME varies per blueprint (0-10)
- Apply ME at query time for flexibility
- Less storage, easier updates

### Why VIEW for calculated values?
- Profit/ROI can be calculated from base data
- Avoids update complexity
- Always consistent

### Why separate economics updater?
- Chains change rarely (CCP updates)
- Economics change frequently (market prices)
- Different update frequencies = different jobs

### Why user decides make-or-buy?
- Different strategies: min_cost vs max_roi vs fastest
- No single "correct" answer
- System provides data, user provides strategy

## Success Metrics

- **Phase 1:** All chains built for 10,000+ items
- **Phase 2:** Chain API responds in <100ms
- **Phase 3:** Economics updated every 30 min for top 1000 items
- **Phase 4:** 10+ jobs created and tracked successfully
- **Phase 5:** Production simulator 10x faster than current

## Migration Strategy

1. New tables run parallel to existing system
2. Gradual migration of features to new APIs
3. Old `production_simulator.py` remains available
4. Once stable, deprecate old system
5. No downtime required

## Notes

- Material Efficiency (ME) reduces material usage: ME 10 = 10% reduction
- Time Efficiency (TE) reduces production time: TE 20 = 20% reduction
- Job cost varies by system based on system cost index
- Raw materials: Items with no further production dependencies (Minerals, PI, etc.)
- Chain depth: Number of production steps from item to raw material
