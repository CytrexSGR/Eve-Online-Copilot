-- Migration 004: Production System Tables
-- Date: 2025-12-17
-- Description: Creates tables for the new production system (chains, economics, workflow)

-- ============================================================================
-- PRODUCTION CHAINS TABLES
-- ============================================================================

-- Direct Material Dependencies (1:1 mapping from SDE)
CREATE TABLE IF NOT EXISTS production_dependencies (
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
CREATE TABLE IF NOT EXISTS production_chains (
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

-- ============================================================================
-- PRODUCTION ECONOMICS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS production_economics (
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
CREATE OR REPLACE VIEW production_economics_calculated AS
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

-- ============================================================================
-- PRODUCTION WORKFLOW TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS production_jobs (
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
CREATE TABLE IF NOT EXISTS production_job_materials (
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

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE production_dependencies IS 'Direct material dependencies from EVE SDE blueprints';
COMMENT ON TABLE production_chains IS 'Pre-calculated complete production chains to raw materials';
COMMENT ON TABLE production_economics IS 'Economic data (costs, prices, ROI) per item and region';
COMMENT ON TABLE production_jobs IS 'User production job tracking';
COMMENT ON TABLE production_job_materials IS 'Materials needed for production jobs with make-or-buy decisions';

COMMENT ON COLUMN production_dependencies.is_raw_material IS 'True if material has no further production dependencies (Minerals, PI, etc.)';
COMMENT ON COLUMN production_chains.base_quantity IS 'Total quantity without ME - apply ME reduction at query time';
COMMENT ON COLUMN production_chains.path IS 'Production path for debugging: "648->12345->34" (Drake->Blueprint->Tritanium)';
COMMENT ON COLUMN production_economics.material_cost IS 'Total cost of all required materials at ME 0';
COMMENT ON COLUMN production_economics.base_job_cost IS 'Average manufacturing job cost for the region';
COMMENT ON COLUMN production_economics.base_production_time IS 'Production time in seconds without TE or skills';
