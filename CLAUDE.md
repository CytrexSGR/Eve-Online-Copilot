# EVE Co-Pilot Development Guidelines

> **Domain-Specific Guides:**
> - [ARCHITECTURE.md](ARCHITECTURE.md) - System Architecture Overview
> - [CLAUDE.backend.md](CLAUDE.backend.md) - Backend Development (FastAPI, Database, ESI)
> - [CLAUDE.frontend.md](CLAUDE.frontend.md) - Frontend Development (React, TypeScript, Vite)

---

## System Credentials

- **Sudo Password:** Aug2012#
- **Database:** eve_sde / User: eve / Password: EvE_Pr0ject_2024
- **GitHub Token:** See `/home/cytrex/Userdocs/.env` (GITHUB_TOKEN)

---

## Language Policy

- **Chat/Communication:** German
- **Code, Documentation, Commits:** English

---

## Core Principles

**Do it right the first time.** Shortcuts create exponentially more work later.

**Oberste Direktive: NICHT RATEN. NACHSCHAUEN!**

Think before acting. Use the right tool. Document your solutions. Test before committing.

---

## Skills & Specialized Agents

**Policy: Proactive Usage - No Permission Required**

When a task matches a specialized skill, use it directly without asking:

**Available Skills:**
- `superpowers:brainstorming` - Refine ideas before coding
- `superpowers:systematic-debugging` - Debug with root cause analysis
- `superpowers:test-driven-development` - Write tests first
- `superpowers:verification-before-completion` - Verify before claiming done
- `python-development:fastapi-pro` - FastAPI patterns and async
- `javascript-typescript:typescript-pro` - TypeScript and React patterns

**Decision Rule:** If a skill fits the task better than manual approach, use it immediately.

---

## Quick Start

```bash
# Start Backend
cd /home/cytrex/eve_copilot
/home/cytrex/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Start Frontend (separate terminal)
cd /home/cytrex/eve_copilot/frontend
npm run dev -- --host 0.0.0.0

# Access Points
# - Frontend:  http://localhost:5173 (dev) / http://77.24.99.81:5173
# - Backend:   http://localhost:8000 / http://77.24.99.81:8000
# - API Docs:  http://localhost:8000/docs
```

---

## Project Structure

```
/home/cytrex/eve_copilot/
├── CLAUDE.md                    # This file - Main development guide
├── CLAUDE.backend.md            # Backend development guide
├── CLAUDE.frontend.md           # Frontend development guide
├── ARCHITECTURE.md              # System architecture overview
│
├── # Core Application
├── main.py                      # FastAPI app, routes, CORS
├── config.py                    # All configuration (DB, ESI, Discord, War Room)
├── database.py                  # PostgreSQL connection & SDE queries
│
├── # Services
├── auth.py                      # EVE SSO OAuth2 authentication
├── character.py                 # Character data API (wallet, assets, skills)
├── esi_client.py                # ESI API client with rate limiting
├── market_service.py            # Market price caching
├── production_simulator.py      # Manufacturing calculations
├── shopping_service.py          # Shopping list management
├── bookmark_service.py          # Bookmark management
├── material_classifier.py       # Material difficulty scoring
├── route_service.py             # A* route calculation & navigation
├── cargo_service.py             # Cargo volume calculator
├── notification_service.py      # Discord webhook notifications
├── services.py                  # Legacy business logic
│
├── # War Room Services
├── killmail_service.py          # EVE Ref Killmail Processing
├── sovereignty_service.py       # ESI Sov Campaigns
├── fw_service.py                # ESI Faction Warfare
├── war_analyzer.py              # Demand Analysis, Doctrines
│
├── routers/                     # API Router Modules
│   ├── shopping.py              # /api/shopping/* endpoints
│   ├── hunter.py                # /api/hunter/* endpoints
│   ├── mining.py                # /api/mining/* endpoints
│   ├── war.py                   # /api/war/* endpoints
│   └── mcp.py                   # /mcp/tools/* endpoints
│
├── jobs/                        # Cron Jobs
│   ├── batch_calculator.py      # Manufacturing opportunities (*/5 min)
│   ├── regional_price_fetcher.py # Regional market prices (*/30 min)
│   ├── market_hunter.py         # Opportunity scanning
│   ├── killmail_fetcher.py      # Daily Killmail Download
│   ├── sov_tracker.py           # Sov Campaign Updates
│   ├── fw_tracker.py            # FW Status Updates
│   └── cron_*.sh                # Cron wrapper scripts
│
├── migrations/                  # SQL Migrations
│   ├── 001_bookmarks.sql
│   ├── 002_shopping.sql
│   └── 003_war_room.sql
│
├── frontend/                    # React + TypeScript + Vite
│   ├── src/
│   │   ├── App.tsx              # Routes & navigation
│   │   ├── api.ts               # Axios API client
│   │   ├── pages/               # Page components
│   │   │   ├── ArbitrageFinder.tsx
│   │   │   ├── Bookmarks.tsx
│   │   │   ├── ItemDetail.tsx
│   │   │   ├── MarketScanner.tsx
│   │   │   ├── MaterialsOverview.tsx
│   │   │   ├── ProductionPlanner.tsx
│   │   │   ├── ShoppingPlanner.tsx
│   │   │   └── WarRoom.tsx
│   │   ├── components/          # Reusable components
│   │   │   ├── AddToListModal.tsx
│   │   │   ├── BookmarkButton.tsx
│   │   │   ├── CollapsiblePanel.tsx
│   │   │   ├── CombatStatsPanel.tsx
│   │   │   └── ConflictAlert.tsx
│   │   └── utils/format.ts      # Formatting utilities
│   └── dist/                    # Production build
│
├── docs/
│   ├── plans/                   # Implementation plans
│   └── session-summary-*.md     # Session handover documents
│
├── logs/                        # Cron job logs
└── tokens.json                  # EVE SSO token storage
```

---

## Database

**PostgreSQL 16** (Docker container: `eve_db`)

```bash
# Connect
echo 'Aug2012#' | sudo -S docker exec eve_db psql -U eve -d eve_sde

# Connection Details
Host: localhost:5432
Database: eve_sde
User: eve
Password: EvE_Pr0ject_2024
```

### Key Tables

| Table | Description |
|-------|-------------|
| `market_prices` | Regional prices (type_id, region_id, lowest_sell, highest_buy) |
| `market_prices_cache` | Global adjusted prices from ESI |
| `manufacturing_opportunities` | Pre-calculated profitable items |
| `shopping_lists` / `shopping_list_items` | Shopping list management |
| `bookmarks` / `bookmark_lists` | Bookmark management |
| `system_region_map` | System to Region mapping (8437 systems) |
| `combat_ship_losses` | Ship losses per day/region/system |
| `combat_item_losses` | Item/Module losses |
| `alliance_conflicts` | Alliance conflict tracking |
| `sovereignty_campaigns` | Sov Timer data |
| `fw_system_status` | Faction Warfare status |
| `invTypes`, `invGroups` | EVE SDE item data |
| `industryActivityMaterials` | Blueprint material requirements |
| `mapSolarSystems` | Solar system data |
| `mapSolarSystemJumps` | Jump connections |

---

## EVE Online Data

### Regions (Trade Hubs)

| Region Key | Region ID | Hub |
|------------|-----------|-----|
| the_forge | 10000002 | Jita |
| domain | 10000043 | Amarr |
| heimatar | 10000030 | Rens |
| sinq_laison | 10000032 | Dodixie |
| metropolis | 10000042 | Hek |

### Characters

| Name | Character ID |
|------|--------------|
| Artallus | 526379435 |
| Cytrex | 1117367444 |
| Cytricia | 110592475 |

### Corporation

- **Name:** Minimal Industries [MINDI]
- **ID:** 98785281
- **Home System:** Isikemi (HighSec 0.78, 3 jumps from Jita)

### EVE SSO

- **Client ID:** b4dbf38efae04055bc7037a63bcfd33b
- **Callback:** http://77.24.99.81:8000/api/auth/callback
- **Token Storage:** `/home/cytrex/eve_copilot/tokens.json`

---

## Cron Jobs

```bash
# View current cron jobs
crontab -l

# Active jobs:
*/5 * * * *  cron_batch_calculator.sh    # Manufacturing opportunities
*/30 * * * * cron_regional_prices.sh     # Regional market prices
*/5 * * * *  cron_market_hunter.sh       # Market hunter scanning
*/30 * * * * cron_sov_tracker.sh         # Sovereignty campaigns
*/30 * * * * cron_fw_tracker.sh          # Faction Warfare status
0 6 * * *    cron_killmail_fetcher.sh    # Daily killmail download

# Logs
tail -f /home/cytrex/eve_copilot/logs/*.log
```

---

## Development Principles

### 1. Validate Assumptions

Don't assume service works. Test it:
```bash
curl http://localhost:8000/api/production/optimize/648 | python3 -m json.tool
```

### 2. Use Existing Patterns

Don't reinvent. Check existing code first:
- API endpoints: `main.py` + `routers/`
- ESI calls: `esi_client.py`
- Database queries: existing services
- Auth: `auth.py`

### 3. Fix Root Cause, Not Symptoms

- Bad: Add cache because API is slow
- Good: Find why API is slow, optimize query

### 4. Keep Root Folder Clean

- Bad: `/test.py`, `/debug.md`
- Good: `/tests/test_feature.py`, `/docs/analysis.md`

### 5. Parallel Over Sequential

When using tools: Do multiple reads/writes in one message. 3x faster.

---

## Common Tasks

### Add New API Endpoint

1. Add route in `main.py` or create router in `routers/`
2. Register router in `main.py` if new
3. Test with curl or `/docs`
4. Update frontend if needed

### Add New Frontend Page

1. Create component in `frontend/src/pages/`
2. Add route in `App.tsx`
3. Add navigation link

### Run Database Migration

```bash
echo 'Aug2012#' | sudo -S docker exec eve_db psql -U eve -d eve_sde -f /path/to/migration.sql
```

### Build Frontend for Production

```bash
cd /home/cytrex/eve_copilot/frontend
npm run build
```

---

## Troubleshooting

### Backend won't start

```bash
lsof -i :8000
pkill -f uvicorn
```

### Frontend won't start

```bash
lsof -i :5173
cd frontend && npm install
```

### Database connection failed

```bash
echo 'Aug2012#' | sudo -S docker ps | grep eve_db
echo 'Aug2012#' | sudo -S docker start eve_db
```

### ESI API rate limited

- Check `esi_client.py` rate limit state
- Wait for reset (usually 60 seconds)

### Token expired

```bash
curl http://localhost:8000/api/auth/characters
curl -X POST http://localhost:8000/api/auth/refresh/{character_id}
```

---

## Quick Reference

| Need to... | Command/Location |
|------------|------------------|
| Start backend | `uvicorn main:app --reload` |
| Start frontend | `npm run dev -- --host 0.0.0.0` |
| Check API docs | http://localhost:8000/docs |
| Connect to DB | `sudo -S docker exec eve_db psql -U eve -d eve_sde` |
| View cron logs | `tail -f logs/*.log` |
| Build frontend | `npm run build` |
| Check ESI status | https://esi.evetech.net/status.json |

---

## Configuration (config.py)

### Market Hunter Settings

```python
HUNTER_MIN_ROI = 15.0           # Minimum ROI percentage
HUNTER_MIN_PROFIT = 500000      # Minimum profit in ISK
HUNTER_TOP_CANDIDATES = 20      # Max candidates to return
HUNTER_DEFAULT_ME = 10          # Default material efficiency
```

### War Room Settings

```python
WAR_DATA_RETENTION_DAYS = 30
WAR_DOCTRINE_MIN_FLEET_SIZE = 10
WAR_HEATMAP_MIN_KILLS = 5
WAR_EVEREF_BASE_URL = "https://data.everef.net/killmails"
```

### Discord Notifications

Webhook configured in `config.py` for alerts.

---

## API Endpoints

### Authentication
- `GET /api/auth/login` - Initiate EVE SSO login
- `GET /api/auth/callback` - OAuth2 callback handler
- `GET /api/auth/characters` - List authenticated characters
- `POST /api/auth/refresh/{character_id}` - Refresh character token
- `DELETE /api/auth/character/{character_id}` - Remove character
- `GET /api/auth/scopes` - List available ESI scopes

### Character Data
- `GET /api/character/{id}/wallet` - Character wallet balance
- `GET /api/character/{id}/assets` - Character assets
- `GET /api/character/{id}/skills` - Character skills
- `GET /api/character/{id}/skillqueue` - Skill training queue
- `GET /api/character/{id}/orders` - Active market orders
- `GET /api/character/{id}/industry` - Industry jobs
- `GET /api/character/{id}/blueprints` - Owned blueprints
- `GET /api/character/{id}/info` - Character info
- `GET /api/character/{id}/corporation/wallet` - Corp wallet
- `GET /api/character/{id}/corporation/info` - Corp info
- `GET /api/character/{id}/corporation/journal/{division}` - Corp journal

### Production & Market
- `GET /api/production/optimize/{type_id}?me=10` - Regional production analysis
- `GET /api/market/compare/{type_id}` - Multi-region price comparison
- `GET /api/market/arbitrage/{type_id}` - Arbitrage opportunities
- `POST /api/simulation/build` - Simulate production run
- `GET /api/simulation/build/{type_id}` - Get simulation for item

### Market Hunter
- `GET /api/hunter/categories` - Available item categories
- `GET /api/hunter/market-tree` - Market group hierarchy
- `GET /api/hunter/scan` - Scan profitable manufacturing opportunities
- `GET /api/hunter/opportunities` - Pre-calculated opportunities

### Shopping Lists
- `GET /api/shopping/lists` - Get all lists
- `POST /api/shopping/lists` - Create list
- `GET /api/shopping/lists/{id}` - Get list details
- `DELETE /api/shopping/lists/{id}` - Delete list
- `POST /api/shopping/lists/{id}/add-production/{type_id}` - Add materials
- `POST /api/shopping/lists/{id}/items` - Add item
- `PATCH /api/shopping/lists/{id}/items/{item_id}` - Update item
- `DELETE /api/shopping/lists/{id}/items/{item_id}` - Remove item

### Bookmarks
- `POST /api/bookmarks` - Create bookmark
- `GET /api/bookmarks` - Get all bookmarks
- `GET /api/bookmarks/check/{type_id}` - Check if item is bookmarked
- `PATCH /api/bookmarks/{id}` - Update bookmark
- `DELETE /api/bookmarks/{id}` - Delete bookmark
- `POST /api/bookmarks/lists` - Create bookmark list
- `GET /api/bookmarks/lists` - Get bookmark lists
- `POST /api/bookmarks/lists/{list_id}/items/{bookmark_id}` - Add to list
- `DELETE /api/bookmarks/lists/{list_id}/items/{bookmark_id}` - Remove from list

### Routes & Navigation
- `GET /api/route/hubs` - Get trade hub systems
- `GET /api/route/distances/{from_system}` - Distances to all hubs
- `GET /api/route/{from_system}/{to_system}` - Calculate route
- `GET /api/systems/search` - Search solar systems

### Cargo & Logistics
- `POST /api/cargo/calculate` - Calculate cargo volume & trips
- `GET /api/cargo/item/{type_id}` - Get item volume info

### Mining
- `GET /api/mining/find-mineral` - Find ore locations for mineral
- `GET /api/mining/route-planner` - Plan mining route
- `GET /api/mining/ore-info` - Ore composition data

### War Room
- `GET /api/war/losses/{region_id}` - Combat losses
- `GET /api/war/demand/{region_id}` - Demand analysis with market gaps
- `GET /api/war/heatmap` - Galaxy heatmap data
- `GET /api/war/campaigns` - Sov timer/battles
- `GET /api/war/fw/hotspots` - FW hotspots
- `GET /api/war/doctrines/{region_id}` - Doctrine detection
- `GET /api/war/conflicts` - Alliance conflicts
- `GET /api/war/route/safe/{from}/{to}` - Route with danger scores
- `GET /api/war/item/{type_id}/stats` - Combat stats for item

### Materials & Utility
- `GET /api/materials/{type_id}/volumes` - Material availability
- `POST /api/cache/clear` - Clear price cache

Full API docs: http://localhost:8000/docs

---

## Navigation

| Topic | Location |
|-------|----------|
| System Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Backend Development | [CLAUDE.backend.md](CLAUDE.backend.md) |
| Frontend Development | [CLAUDE.frontend.md](CLAUDE.frontend.md) |
| API Documentation | http://localhost:8000/docs |
| Implementation Plans | `docs/plans/` |

---

**Last Updated:** 2025-12-07
