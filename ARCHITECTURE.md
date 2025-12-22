# EVE Co-Pilot Architecture

> **Back to:** [CLAUDE.md](CLAUDE.md)

---

## System Overview

EVE Co-Pilot is a production and trading analysis tool for EVE Online. It combines real-time market data, manufacturing calculations, and combat intelligence to identify profitable opportunities.

### High-Level Architecture

```
                                    +------------------+
                                    |   EVE Online     |
                                    |   ESI API        |
                                    +--------+---------+
                                             |
                    +------------------------+------------------------+
                    |                        |                        |
            +-------v-------+       +--------v--------+      +--------v--------+
            | Market Data   |       | Character Data  |      | Universe Data   |
            | (Orders,      |       | (Wallet, Assets,|      | (Systems, Sov,  |
            |  Prices)      |       |  Skills, Jobs)  |      |  FW, Killmails) |
            +-------+-------+       +--------+--------+      +--------+--------+
                    |                        |                        |
                    +------------------------+------------------------+
                                             |
                                    +--------v--------+
                                    |   FastAPI       |
                                    |   Backend       |
                                    |   (Port 8000)   |
                                    +--------+--------+
                                             |
                    +------------------------+------------------------+
                    |                        |                        |
            +-------v-------+       +--------v--------+      +--------v--------+
            | PostgreSQL    |       | Cron Jobs       |      | Discord         |
            | (eve_sde +    |       | (Price updates, |      | Webhooks        |
            |  App Tables)  |       |  Killmails)     |      | (Alerts)        |
            +---------------+       +-----------------+      +-----------------+
                                             |
                                    +--------v--------+
                                    |   React         |
                                    |   Frontend      |
                                    |   (Port 5173)   |
                                    +-----------------+
```

---

## Components

### 1. Backend (FastAPI)

**Location:** `/home/cytrex/eve_copilot/main.py`

Single FastAPI application serving REST API endpoints.

**Routers:**
| Router | Prefix | Purpose |
|--------|--------|---------|
| `auth.py` | `/api/auth` | EVE SSO authentication |
| `character.py` | `/api/character` | Character data (wallet, assets, skills) |
| `bookmarks.py` | `/api/bookmarks` | Bookmark management |
| `production.py` | `/api/production` | Manufacturing cost calculations |
| `production_chains.py` | `/api/production/chains` | Production chain analysis |
| `production_economics.py` | `/api/production/economics` | Economic opportunities |
| `production_workflow.py` | `/api/production/workflow` | Production job management |
| `market.py` | `/api/market` | Market data and arbitrage |
| `items.py` | `/api/items`, `/api/materials`, `/api/route`, `/api/cargo` | Item search, materials, navigation |
| `shopping.py` | `/api/shopping` | Shopping list management |
| `hunter.py` | `/api/hunter` | Market opportunity scanning |
| `mining.py` | `/api/mining` | Mining route planning |
| `war.py` | `/api/war` | Combat intelligence (War Room) |
| `dashboard.py` | `/api/dashboard` | Dashboard opportunities and portfolio |
| `research.py` | `/api/research` | Skill recommendations and research |
| `mcp.py` | `/mcp/tools` | MCP tool integration |

### 2. Services

**Core Services:**
| Service | File | Purpose |
|---------|------|---------|
| ESI Client | `esi_client.py` | EVE API calls with rate limiting |
| Auth | `auth.py` | OAuth2 flow, token management |
| Character | `character.py` | Wallet, assets, skills, orders |
| Market | `market_service.py` | Price caching and retrieval |
| Production | `production_simulator.py` | Manufacturing cost calculation |
| Shopping | `shopping_service.py` | Shopping list CRUD |
| Bookmarks | `bookmark_service.py` | Bookmark CRUD |
| Route | `route_service.py` | A* pathfinding between systems |
| Cargo | `cargo_service.py` | Volume calculation, ship recommendations |
| Notifications | `notification_service.py` | Discord webhooks |
| Dashboard | `services/dashboard_service.py` | Dashboard data aggregation |
| Portfolio | `services/portfolio_service.py` | Character portfolio analysis |
| Research | `services/research_service.py` | Skill recommendations |

**Production Services (services/production/):**
| Service | File | Purpose |
|---------|------|---------|
| Chain Service | `chain_service.py` | Production chain analysis |
| Chain Repository | `chain_repository.py` | Database access for chains |
| Economics Service | `economics_service.py` | Economic analysis |
| Economics Repository | `economics_repository.py` | Economic data access |
| Workflow Service | `workflow_service.py` | Production job management |
| Workflow Repository | `workflow_repository.py` | Job data persistence |

### 3. War Room Services

| Service | File | Purpose |
|---------|------|---------|
| Killmail | `killmail_service.py` | Download and parse EVE Ref killmails |
| Sovereignty | `sovereignty_service.py` | Track sov campaigns from ESI |
| Faction Warfare | `fw_service.py` | Track FW hotspots |
| War Analyzer | `war_analyzer.py` | Demand analysis, doctrine detection |

### 4. Database (PostgreSQL)

**Container:** `eve_db`
**Database:** `eve_sde`

#### Schema Overview

```
+-------------------+     +-------------------+     +-------------------+
| invTypes          |     | market_prices     |     | shopping_lists    |
| (EVE SDE)         |     | (App Data)        |     | (App Data)        |
+-------------------+     +-------------------+     +-------------------+
| typeID (PK)       |     | type_id           |     | id (PK)           |
| typeName          |     | region_id         |     | name              |
| groupID           |     | lowest_sell       |     | created_at        |
| volume            |     | highest_buy       |     +-------------------+
+-------------------+     | sell_volume       |              |
        |                 | updated_at        |              |
        v                 +-------------------+              v
+-------------------+                              +-------------------+
| industryActivity  |                              | shopping_list_    |
| Materials         |                              | items             |
+-------------------+                              +-------------------+
| typeID            |                              | id (PK)           |
| materialTypeID    |                              | list_id (FK)      |
| quantity          |                              | type_id           |
+-------------------+                              | quantity          |
                                                   +-------------------+

+-------------------+     +-------------------+     +-------------------+
| combat_ship_      |     | system_region_    |     | fw_system_        |
| losses            |     | map               |     | status            |
+-------------------+     +-------------------+     +-------------------+
| id (PK)           |     | system_id (PK)    |     | system_id (PK)    |
| type_id           |     | region_id         |     | faction_id        |
| region_id         |     | system_name       |     | contested_percent |
| system_id         |     | security          |     | updated_at        |
| quantity          |     +-------------------+     +-------------------+
| kill_date         |
+-------------------+
```

### 5. Frontend (React + TypeScript)

**Location:** `/home/cytrex/eve_copilot/frontend/`
**Framework:** Vite + React + TypeScript

#### Pages

| Page | File | Route | Purpose |
|------|------|-------|---------|
| Dashboard | `Dashboard.tsx` | `/` | Main dashboard with opportunities |
| Item Detail | `ItemDetail.tsx` | `/item/:typeId` | Detailed item view with combat stats |
| Arbitrage Finder | `ArbitrageFinder.tsx` | `/arbitrage` | Find trade opportunities |
| Production Planner | `ProductionPlanner.tsx` | `/production` | Plan production runs with new chains API |
| Bookmarks | `Bookmarks.tsx` | `/bookmarks` | Manage saved items |
| Materials Overview | `MaterialsOverview.tsx` | `/materials` | Material availability |
| Shopping Wizard | `ShoppingWizard.tsx` | `/shopping` | Guided shopping list creation |
| Shopping Planner | `ShoppingPlanner.tsx` | `/shopping-lists` | Manage shopping lists |
| War Room | `WarRoom.tsx` | `/war-room` | Combat intelligence dashboard |
| War Room - Ships Destroyed | `WarRoomShipsDestroyed.tsx` | `/war-room/ships-destroyed` | Ship losses by region |
| War Room - Market Gaps | `WarRoomMarketGaps.tsx` | `/war-room/market-gaps` | Market gaps with production economics |
| War Room - Top Ships | `WarRoomTopShips.tsx` | `/war-room/top-ships` | Most destroyed ships galaxy-wide |
| War Room - Combat Hotspots | `WarRoomCombatHotspots.tsx` | `/war-room/combat-hotspots` | Combat activity heatmap |
| War Room - FW Hotspots | `WarRoomFWHotspots.tsx` | `/war-room/fw-hotspots` | Faction warfare activity |
| War Room - Galaxy Summary | `WarRoomGalaxySummary.tsx` | `/war-room/galaxy-summary` | Region-wide summary |

#### Components

| Component | Purpose |
|-----------|---------|
| `CollapsiblePanel.tsx` | Expandable content sections |
| `CombatStatsPanel.tsx` | Display combat statistics |
| `ConflictAlert.tsx` | Route danger warnings |
| `AddToListModal.tsx` | Add items to shopping lists |
| `BookmarkButton.tsx` | Quick bookmark toggle |

### 6. Cron Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `batch_calculator.py` | */5 min | Calculate manufacturing opportunities |
| `regional_price_fetcher.py` | */30 min | Update regional market prices |
| `market_hunter.py` | */5 min | Scan for profitable items |
| `sov_tracker.py` | */30 min | Update sovereignty campaigns |
| `fw_tracker.py` | */30 min | Update FW system status |
| `killmail_fetcher.py` | Daily 06:00 | Download previous day's killmails |

---

## Data Flows

### 1. Market Price Flow

```
ESI Market API → regional_price_fetcher.py → market_prices table
                                                    ↓
                                           Production calculations
                                                    ↓
                                           manufacturing_opportunities
```

### 2. Authentication Flow

```
User → /api/auth/login → EVE SSO → /api/auth/callback → tokens.json
                                                              ↓
                                                        ESI API calls
                                                        (wallet, assets, etc.)
```

### 3. War Room Data Flow

```
EVE Ref → killmail_fetcher.py → combat_ship_losses + combat_item_losses
                                            ↓
ESI Sov → sov_tracker.py → sovereignty_campaigns
                                            ↓
ESI FW → fw_tracker.py → fw_system_status
                                            ↓
                                    war_analyzer.py
                                            ↓
                                    /api/war/* endpoints
```

### 4. Shopping List Flow

```
User selects item → /api/production/optimize/{type_id} → Material list
                                                              ↓
                                            /api/shopping/lists/{id}/add-production
                                                              ↓
                                                    shopping_list_items
```

---

## External Dependencies

### EVE Online APIs

| API | Purpose | Rate Limit |
|-----|---------|------------|
| ESI (esi.evetech.net) | Official game API | ~400/min |
| EVE Ref (data.everef.net) | Killmail bulk data | No limit |
| EVE Image Server | Item icons | No limit |

### Infrastructure

| Service | Container | Port |
|---------|-----------|------|
| PostgreSQL | eve_db | 5432 |
| Backend | (host) | 8000 |
| Frontend | (host) | 5173 |

---

## Security Considerations

### Token Storage

- OAuth2 tokens stored in `tokens.json`
- Tokens include refresh tokens for long-term access
- Character IDs used to isolate data access

### API Access

- CORS configured for frontend origin
- No authentication required for public endpoints
- Character-specific endpoints require valid token

### Database

- Credentials in `config.py` (not in git)
- Docker container network isolation
- No external access to database port

---

## Performance Characteristics

### Caching

**Backend:**
- ESI responses cached in `esi_client.py` (TTL: varies by endpoint)
- Regional prices cached in `market_prices` table (30 min refresh)
- Manufacturing opportunities pre-calculated (5 min refresh)

**Frontend:**
- React Query caching (5 min staleTime, 10 min gcTime)
- Optimistic updates for mutations
- No refetch on window focus (reduces load)
- Code splitting via lazy loading for all pages

### Rate Limiting

- ESI client implements exponential backoff
- Bulk operations batched to avoid rate limits
- Price fetcher uses parallel requests with throttling

### Database Queries

- Complex queries use indexed columns
- SDE tables pre-indexed (EVE provides)
- App tables indexed on type_id, region_id

### Frontend Optimization

- **Code Splitting:** All pages lazy-loaded with React.lazy()
- **Bundle Size:** Reduced by dynamic imports
- **React Query:** Aggressive caching reduces API calls
- **Keyboard Shortcuts:** Efficient navigation without mouse

---

## Future Considerations

### Planned Improvements

1. **Docker Containerization** - Package entire application in Docker
2. **Git Repository** - Version control for code
3. **Route Safety in Shopping** - Danger warnings during route planning
4. **2D Galaxy Map** - Visual heatmap for War Room
5. **Production Timing Warnings** - Alert when battles imminent

### Technical Debt

- `services.py` contains legacy code that could be split
- Some endpoints in `main.py` should move to routers
- Frontend lacks proper TypeScript interfaces for API responses

---

## Quick Reference

### Start Application

```bash
# Backend
cd /home/cytrex/eve_copilot
/home/cytrex/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd /home/cytrex/eve_copilot/frontend
npm run dev -- --host 0.0.0.0
```

### Database Access

```bash
echo 'Aug2012#' | sudo -S docker exec eve_db psql -U eve -d eve_sde
```

### Logs

```bash
tail -f /home/cytrex/eve_copilot/logs/*.log
```

---

**Last Updated:** 2025-12-22
