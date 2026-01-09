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
- **Frontend UI Text:** English (all user-facing text in the web interfaces)

---

## Core Principles

**Do it right the first time.** Shortcuts create exponentially more work later.

**Oberste Direktive: NICHT RATEN. NACHSCHAUEN!**

Think before acting. Use the right tool. Document your solutions. Test before committing.

---

## UI/UX Design Guidelines

### Dark Mode - MANDATORY

**IMPORTANT: All frontend interfaces MUST use dark mode by default.**

EVE Online is a space game with a dark aesthetic. All UI components should follow these dark mode principles:

**Color Palette:**
- **Background:** `#0d1117` (deep space dark)
- **Surface:** `#161b22` (cards, panels)
- **Surface Elevated:** `#21262d` (hover states, elevated cards)
- **Border:** `#30363d` (subtle borders)
- **Text Primary:** `#e6edf3` (high contrast, readable)
- **Text Secondary:** `#8b949e` (muted text, labels)
- **Text Tertiary:** `#6e7681` (disabled, very subtle)
- **Accent Blue:** `#58a6ff` (primary actions, links)
- **Accent Purple:** `#bc8cff` (special highlights)
- **Success:** `#3fb950` (profit, positive values)
- **Warning:** `#d29922` (moderate alerts)
- **Danger:** `#f85149` (errors, critical alerts)

**Typography:**
- Use clear, readable fonts with proper contrast
- Minimum font size: 14px for body text
- Headlines should be bold (700) with good spacing

**Spacing & Layout:**
- Generous padding and margins (minimum 16px)
- Clear visual hierarchy with shadows and borders
- Cards should have subtle shadows for depth

**Accessibility:**
- All text must meet WCAG AA contrast standards (4.5:1 for normal text)
- Interactive elements must have clear hover/focus states
- Use semantic HTML for better accessibility

---

## Git & GitHub - MANDATORY

**Repository:** https://github.com/CytrexSGR/Eve-Online-Copilot

**IMPORTANT: After completing any task that changes code or documentation:**

1. **Stage changes:** `git add -A`
2. **Commit with descriptive message:** Follow conventional commits (feat/fix/docs/refactor)
3. **Push to GitHub:** `git push origin main`

**Commit Message Format:**
```
type: Short description

- Detail 1
- Detail 2

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

**Types:** feat, fix, docs, refactor, test, chore, security

**DO NOT FORGET:** Every session should end with all changes committed and pushed. Check with `git status` before ending.

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

# Start Internal Frontend (separate terminal)
cd /home/cytrex/eve_copilot/frontend
npm run dev -- --host 0.0.0.0

# Start Public Frontend (separate terminal)
cd /home/cytrex/eve_copilot/public-frontend
npm run dev -- --host 0.0.0.0

# Start ectmap (separate terminal)
cd /home/cytrex/eve_copilot/ectmap
npm run dev

# Access Points
# - Internal Frontend:  http://localhost:5173 / http://192.168.178.108:5173
# - Public Frontend:    http://localhost:5173 / http://192.168.178.108:5173  (same port)
# - ectmap:             http://localhost:3001 / http://192.168.178.108:3001
# - Backend:            http://localhost:8000 / http://192.168.178.108:8000
# - API Docs:           http://localhost:8000/docs
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
├── services/zkillboard/         # zkillboard Live Stream Integration
│   └── live_service.py          # Real-time battle tracking & zkillboard RedisQ
│
├── routers/                     # API Router Modules
│   ├── auth.py                  # /api/auth/* endpoints
│   ├── character.py             # /api/character/* endpoints
│   ├── bookmarks.py             # /api/bookmarks/* endpoints
│   ├── production.py            # /api/production/* endpoints
│   ├── production_chains.py     # /api/production/chains/* endpoints
│   ├── production_economics.py  # /api/production/economics/* endpoints
│   ├── production_workflow.py   # /api/production/workflow/* endpoints
│   ├── market.py                # /api/market/* endpoints
│   ├── items.py                 # /api/items/*, /api/materials/*, /api/route/* endpoints
│   ├── shopping.py              # /api/shopping/* endpoints
│   ├── hunter.py                # /api/hunter/* endpoints
│   ├── mining.py                # /api/mining/* endpoints
│   ├── war.py                   # /api/war/* endpoints
│   ├── dashboard.py             # /api/dashboard/* endpoints
│   ├── research.py              # /api/research/* endpoints
│   └── mcp.py                   # /mcp/tools/* endpoints
│
├── services/                    # New Services Directory
│   ├── dashboard_service.py     # Dashboard data aggregation
│   ├── portfolio_service.py     # Portfolio analysis
│   ├── research_service.py      # Skill recommendations
│   └── production/              # Production services
│       ├── chain_service.py     # Production chain analysis
│       ├── chain_repository.py  # Chain data access
│       ├── economics_service.py # Economic analysis
│       ├── economics_repository.py # Economics data access
│       ├── workflow_service.py  # Production job management
│       └── workflow_repository.py # Job persistence
│
├── jobs/                        # Cron Jobs
│   ├── batch_calculator.py      # Manufacturing opportunities (*/5 min)
│   ├── regional_price_fetcher.py # Regional market prices (*/30 min)
│   ├── market_hunter.py         # Opportunity scanning
│   ├── killmail_fetcher.py      # Daily Killmail Download
│   ├── sov_tracker.py           # Sov Campaign Updates
│   ├── fw_tracker.py            # FW Status Updates
│   ├── battle_cleanup.py        # Battle cleanup (*/30 min)
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
│   │   ├── pages/               # Page components (all lazy-loaded)
│   │   │   ├── Dashboard.tsx             # Main dashboard (NEW)
│   │   │   ├── ArbitrageFinder.tsx       # Trade opportunities
│   │   │   ├── ProductionPlanner.tsx     # Production planning with chains API
│   │   │   ├── Bookmarks.tsx             # Saved items
│   │   │   ├── ItemDetail.tsx            # Item details & combat stats
│   │   │   ├── MaterialsOverview.tsx     # Material availability
│   │   │   ├── ShoppingPlanner.tsx       # Shopping lists management
│   │   │   ├── WarRoom.tsx               # Combat intelligence hub
│   │   │   ├── WarRoomShipsDestroyed.tsx # Ship losses by region
│   │   │   ├── WarRoomMarketGaps.tsx     # Market gaps with economics
│   │   │   ├── WarRoomTopShips.tsx       # Most destroyed ships
│   │   │   ├── WarRoomCombatHotspots.tsx # Combat heatmap
│   │   │   ├── WarRoomFWHotspots.tsx     # FW activity
│   │   │   └── WarRoomGalaxySummary.tsx  # Region summary
│   │   ├── components/          # Reusable components
│   │   │   ├── shopping/             # Shopping components
│   │   │   │   └── ShoppingWizard.tsx  # Guided shopping (NEW)
│   │   │   ├── AddToListModal.tsx
│   │   │   ├── BookmarkButton.tsx
│   │   │   ├── CollapsiblePanel.tsx
│   │   │   ├── CombatStatsPanel.tsx
│   │   │   ├── ConflictAlert.tsx
│   │   │   └── ShortcutsHelp.tsx     # Keyboard shortcuts help (NEW)
│   │   ├── hooks/               # Custom hooks
│   │   │   └── useKeyboardShortcuts.ts # Global shortcuts (NEW)
│   │   └── utils/format.ts      # Formatting utilities
│   └── dist/                    # Production build
│
├── public-frontend/             # Public Combat Intelligence Dashboard (Port 5173)
│   ├── src/
│   │   ├── App.tsx              # Routes & navigation
│   │   ├── pages/               # Page components (all lazy-loaded)
│   │   │   ├── Home.tsx                    # Main dashboard
│   │   │   ├── BattleReport.tsx            # 24h battle report with ectmap
│   │   │   ├── BattleMap2D.tsx             # Interactive 2D battle map
│   │   │   ├── BattleDetail.tsx            # Individual battle details
│   │   │   ├── WarProfiteering.tsx         # Market opportunities
│   │   │   ├── AllianceWars.tsx            # Alliance conflicts
│   │   │   ├── TradeRoutes.tsx             # Route safety
│   │   │   └── NotFound.tsx                # 404 page
│   │   ├── components/          # Reusable components
│   │   │   ├── Layout.tsx                  # Main layout with navigation
│   │   │   ├── RefreshIndicator.tsx        # Auto-refresh status
│   │   │   ├── BattleStatsCards.tsx        # Live battle statistics
│   │   │   ├── LiveBattles.tsx             # Active battles feed
│   │   │   └── TelegramMirror.tsx          # Telegram alerts mirror
│   │   ├── services/api.ts      # API client (reportsApi, battleApi)
│   │   ├── hooks/               # Custom React hooks
│   │   │   ├── useReports.ts               # Reports data fetching
│   │   │   └── useAutoRefresh.ts           # Auto-refresh functionality
│   │   └── types/reports.ts     # TypeScript types
│   └── dist/                    # Production build
│
├── ectmap/                      # EVE Online Universe Map (Port 3001)
│   ├── app/
│   │   ├── components/
│   │   │   └── StarMap.tsx      # Canvas-based map with battle overlay
│   │   ├── api/battles/
│   │   │   └── route.ts         # Battle data endpoint (proxies to backend:8000)
│   │   └── page.tsx             # Main map page
│   └── # Next.js 16 (Turbopack) - Third-party ectmap integration
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
*/30 * * * * cron_battle_cleanup.sh      # Battle cleanup (end old battles)
0 6 * * *    cron_killmail_fetcher.sh    # Daily killmail download
*/10 * * * * cron_goaccess_update.sh     # GoAccess web analytics report

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
- `GET /api/character/{id}/portrait` - Character portrait image URL

### Dashboard & Portfolio
- `GET /api/dashboard/opportunities` - Market opportunities overview
- `GET /api/dashboard/opportunities/{category}` - Opportunities by category
- `GET /api/dashboard/characters/summary` - All characters summary
- `GET /api/dashboard/characters/portfolio` - Portfolio analysis
- `GET /api/dashboard/projects` - Active projects

### Research & Skills
- `GET /api/research/skills-for-item/{type_id}` - Required skills for item
- `GET /api/research/recommendations/{character_id}` - Skill recommendations

### Production & Market
- `GET /api/production/optimize/{type_id}?me=10` - Regional production analysis
- `GET /api/production/cost/{type_id}` - Production cost calculation
- `POST /api/production/cost` - Batch production cost
- `POST /api/simulation/build` - Simulate production run
- `GET /api/simulation/build/{type_id}` - Get simulation for item

### Production Chains
- `GET /api/production/chains/{type_id}` - Full production chain tree
- `GET /api/production/chains/{type_id}/materials` - All materials needed
- `GET /api/production/chains/{type_id}/direct` - Direct materials only

### Production Economics
- `GET /api/production/economics/opportunities` - Economic opportunities
- `GET /api/production/economics/{type_id}` - Item economics analysis
- `GET /api/production/economics/{type_id}/regions` - Regional economics

### Production Workflow
- `POST /api/production/workflow/jobs` - Create production job
- `GET /api/production/workflow/jobs` - List production jobs
- `PATCH /api/production/workflow/jobs/{job_id}` - Update job status

### Market
- `GET /api/market/stats/{region_id}/{type_id}` - Market statistics
- `GET /api/market/compare/{type_id}` - Multi-region price comparison
- `GET /api/market/arbitrage/{type_id}` - Arbitrage opportunities
- `GET /api/arbitrage/enhanced/{type_id}` - Enhanced arbitrage with routing
- `POST /api/trade/arbitrage` - Custom arbitrage calculation
- `GET /api/trade/arbitrage` - Saved arbitrage results
- `POST /api/cache/clear` - Clear market cache

### Market Hunter
- `GET /api/hunter/categories` - Available item categories
- `GET /api/hunter/market-tree` - Market group hierarchy
- `GET /api/hunter/scan` - Scan profitable manufacturing opportunities
- `GET /api/hunter/opportunities` - Pre-calculated opportunities

### Shopping Lists
- `GET /api/shopping/lists` - Get all lists
- `POST /api/shopping/lists` - Create list
- `GET /api/shopping/lists/{id}` - Get list details
- `PATCH /api/shopping/lists/{id}` - Update list
- `DELETE /api/shopping/lists/{id}` - Delete list
- `POST /api/shopping/lists/{id}/items` - Add item to list
- `PATCH /api/shopping/items/{item_id}` - Update item
- `DELETE /api/shopping/items/{item_id}` - Remove item
- `POST /api/shopping/items/{item_id}/purchased` - Mark as purchased
- `DELETE /api/shopping/items/{item_id}/purchased` - Unmark purchased
- `PATCH /api/shopping/items/{item_id}/region` - Change purchase region
- `PATCH /api/shopping/items/{item_id}/runs` - Update blueprint runs
- `PATCH /api/shopping/items/{item_id}/build-decision` - Set build/buy decision
- `POST /api/shopping/items/{item_id}/calculate-materials` - Calculate material needs
- `POST /api/shopping/items/{item_id}/apply-materials` - Apply materials to list
- `GET /api/shopping/items/{item_id}/with-materials` - Get item with materials
- `POST /api/shopping/lists/{id}/add-production/{type_id}` - Add production materials
- `GET /api/shopping/lists/{id}/export` - Export list to EVE format
- `GET /api/shopping/lists/{id}/by-region` - Group items by region
- `GET /api/shopping/lists/{id}/regional-comparison` - Compare regional prices
- `GET /api/shopping/lists/{id}/cargo-summary` - Calculate cargo requirements
- `GET /api/shopping/lists/{id}/transport-options` - Get transport ship options
- `GET /api/shopping/route` - Calculate shopping route
- `GET /api/shopping/orders/{type_id}` - Get market orders for item
- `POST /api/shopping/wizard/calculate-materials` - Wizard: calculate materials
- `POST /api/shopping/wizard/compare-regions` - Wizard: compare regions

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
- `GET /api/war/campaigns/update` - Manually update sov campaigns
- `GET /api/war/fw/hotspots` - FW hotspots
- `GET /api/war/fw/vulnerable` - Vulnerable FW systems
- `GET /api/war/fw/update` - Manually update FW status
- `GET /api/war/doctrines/{region_id}` - Doctrine detection
- `GET /api/war/conflicts` - Alliance conflicts
- `GET /api/war/system/{system_id}/danger` - System danger score
- `GET /api/war/summary` - Regional combat summary
- `GET /api/war/top-ships` - Most destroyed ships galaxy-wide
- `GET /api/war/route/safe/{from}/{to}` - Route with danger scores
- `GET /api/war/item/{type_id}/stats` - Combat stats for item with detailed breakdown
- `GET /api/war/alerts` - War room alerts

### Live Battle Tracking
- `GET /api/war/battles/active?limit=1000` - Get active battles
- `GET /api/war/battle/{battle_id}/kills?limit=500` - Get kills for specific battle
- `GET /api/war/battle/{battle_id}/ship-classes?group_by=category` - Ship class breakdown
- `GET /api/war/telegram/recent?limit=5` - Recent Telegram battle alerts
- `GET /api/war/live/kills?system_id={id}&limit=20` - Live kills in system
- `GET /api/war/system/{system_id}/kills?limit=500&hours=24` - System kills by timeframe
- `GET /api/war/system/{system_id}/ship-classes?hours=24&group_by=category` - System ship classes
- `GET /api/war/map/systems` - All systems with coordinates for map rendering
- `GET /api/war/pilot-intelligence` - 24h battle report (public frontend)

### Items & Materials
- `GET /api/items/search` - Search items by name
- `GET /api/items/{type_id}` - Get item details
- `GET /api/groups/search` - Search item groups
- `GET /api/regions` - List all regions
- `GET /api/materials/{type_id}/composition` - Material composition
- `GET /api/materials/{type_id}/volumes` - Material availability

### Agent Runtime (Phase 7: Tool Execution & Agentic Loop) ✅
- `POST /agent/session` - Create new agent session
- `GET /agent/session/{session_id}` - Get session state
- `DELETE /agent/session/{session_id}` - Delete session
- `POST /agent/chat` - Send message to agent (with persistence)
- `POST /agent/chat/stream` - Stream agent response via SSE with tool execution
- `GET /agent/chat/history/{session_id}` - Get chat history (paginated)
- `POST /agent/execute` - Approve and execute pending plan
- `POST /agent/reject` - Reject pending plan
- `WS /agent/stream/{session_id}` - WebSocket event streaming

**Phase 7 Features (PRODUCTION-READY):**
- ✅ Autonomous tool execution from LLM streaming responses
- ✅ Multi-turn agentic loop: LLM → Tools → LLM until final answer
- ✅ Sub-second tool performance (190x faster with direct service calls)
- ✅ Authorization checks respecting user autonomy levels (L0-L3)
- ✅ Plan approval flow for high-risk operations
- ✅ Retry logic with exponential backoff (3 attempts)
- ✅ Real-time event broadcasting via WebSocket
- ✅ Support for both Anthropic Claude and OpenAI GPT
- ✅ 90/115 MCP tools refactored for optimal performance
- ✅ 21/21 tests passing, browser testing successful

**Phase 6 Features:**
- ✅ Message persistence to PostgreSQL (`agent_messages` table)
- ✅ Real-time streaming via Server-Sent Events (SSE)
- ✅ Chat history retrieval with pagination
- ✅ Authorization and validation middleware
- ✅ Error recovery with automatic retry
- ✅ Token usage tracking

**Documentation:**
- [Phase 7 Tool Execution](docs/agent/phase7-tool-execution.md) - Comprehensive feature guide
- [Phase 7 Usage Examples](docs/agent/phase7-usage-examples.md) - Real-world scenarios
- [Phase 7 Browser Testing Report](docs/agent/phase7-browser-testing-report.md) - Production verification
- [Phase 6 API Documentation](docs/agent/phase6-api-documentation.md) - Foundation
- [Phase 6 Usage Examples](docs/agent/phase6-usage-examples.md)
- [Phase 6 Completion Report](docs/agent/phase6-completion.md)

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

**Last Updated:** 2026-01-08
