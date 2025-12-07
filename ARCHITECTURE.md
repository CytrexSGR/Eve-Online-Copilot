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
| `shopping.py` | `/api/shopping` | Shopping list management |
| `hunter.py` | `/api/hunter` | Market opportunity scanning |
| `mining.py` | `/api/mining` | Mining route planning |
| `war.py` | `/api/war` | Combat intelligence (War Room) |
| `mcp.py` | `/mcp/tools` | MCP tool integration |

**Core Endpoints in main.py:**
- `/api/auth/*` - EVE SSO authentication
- `/api/character/*` - Character data
- `/api/production/*` - Manufacturing calculations
- `/api/market/*` - Market data and arbitrage
- `/api/bookmarks/*` - Bookmark management
- `/api/route/*` - Navigation and routing
- `/api/cargo/*` - Cargo calculations

### 2. Services

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

| Page | File | Purpose |
|------|------|---------|
| Market Scanner | `MarketScanner.tsx` | Find manufacturing opportunities |
| Production Planner | `ProductionPlanner.tsx` | Plan production runs |
| Shopping Planner | `ShoppingPlanner.tsx` | Manage shopping lists |
| Arbitrage Finder | `ArbitrageFinder.tsx` | Find trade opportunities |
| Bookmarks | `Bookmarks.tsx` | Manage saved items |
| Materials Overview | `MaterialsOverview.tsx` | Material availability |
| Item Detail | `ItemDetail.tsx` | Detailed item view with combat stats |
| War Room | `WarRoom.tsx` | Combat intelligence dashboard |

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

- ESI responses cached in `esi_client.py` (TTL: varies by endpoint)
- Regional prices cached in `market_prices` table (30 min refresh)
- Manufacturing opportunities pre-calculated (5 min refresh)

### Rate Limiting

- ESI client implements exponential backoff
- Bulk operations batched to avoid rate limits
- Price fetcher uses parallel requests with throttling

### Database Queries

- Complex queries use indexed columns
- SDE tables pre-indexed (EVE provides)
- App tables indexed on type_id, region_id

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

**Last Updated:** 2025-12-07
