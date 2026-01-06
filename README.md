# EVE Co-Pilot

A comprehensive industry and market analysis tool for EVE Online. Built with FastAPI backend and React/TypeScript frontend.

![EVE Online](https://img.shields.io/badge/EVE-Online-orange)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![React](https://img.shields.io/badge/React-18-61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

### Dashboard
- **Market Opportunities** - Overview of profitable manufacturing opportunities
- **Character Portfolio** - Multi-character asset and wallet tracking
- **Active Projects** - Production job monitoring and management

### Market Analysis
- **Arbitrage Finder** - Cross-region trade opportunities with routing
- **Market Hunter** - Automated scanning for profitable T1 products
- **Live Market Data** - Real-time prices via ESI API with order depth analysis
- **Enhanced Arbitrage** - Route planning and cargo calculations

### Production Tools
- **Production Planner** - Manufacturing cost calculator with ME/TE bonuses
- **Production Chains** - Full material chain analysis and visualization
- **Production Economics** - Regional economic opportunities and analysis
- **Production Workflow** - Job tracking and batch production management
- **Material Classifier** - Difficulty scoring for material acquisition

### Shopping Tools
- **Shopping Wizard** - Guided shopping list creation with best prices
- **Shopping Lists** - Multi-region price comparison with route optimization
- **Cargo Calculator** - Volume calculations and transport ship recommendations
- **Build/Buy Decisions** - Automatic comparison of building vs buying
- **Material Expansion** - Recursive material breakdown for blueprints

### War Room (Combat Intelligence)
- **Galaxy Summary** - Region-wide combat activity overview
- **Ships Destroyed** - Track combat losses by region/system
- **Market Gaps** - Identify supply shortages with production economics
- **Top Ships** - Most destroyed ships galaxy-wide
- **Combat Hotspots** - Heatmap of combat activity
- **Doctrine Detection** - Identify fleet compositions from loss patterns
- **Sovereignty Tracking** - Monitor sov campaigns and timers
- **Faction Warfare** - FW system status and hotspots
- **Alliance Conflicts** - Track ongoing wars and combat demand
- **Live Killmail Stream** - Real-time killmails from zKillboard (NEW!)
- **Hotspot Alerts** - Discord notifications for combat spikes (NEW!)
- **War Profiteering** - Track destroyed item demand in real-time (NEW!)

### Character Management
- **OAuth2 Authentication** - Secure EVE SSO integration
- **Wallet & Assets** - View character finances and inventory
- **Industry Jobs** - Monitor manufacturing and research
- **Corporation Support** - Access corp wallets and member lists
- **Character Portraits** - Display character images

### Research & Skills
- **Skill Requirements** - View required skills for items
- **Skill Recommendations** - Character-specific training suggestions

### Navigation
- **Route Calculator** - A* pathfinding between systems
- **Trade Hub Routes** - Optimal paths through major hubs
- **Danger Scoring** - Route safety based on recent combat activity
- **Shopping Routes** - Optimized multi-stop shopping paths

### Performance
- **Code Splitting** - Lazy-loaded pages for faster initial load
- **React Query Caching** - Aggressive caching reduces API calls
- **Keyboard Shortcuts** - Fast navigation without mouse

### Agent Runtime

**Status:** Phase 5 Complete ✅ - INITIAL RELEASE READY 🚀

Conversational AI agent with session management, multi-tool plan detection, approval workflow, real-time frontend UI, chat interface, and advanced monitoring features.

#### Phase 1: Core Infrastructure (Complete ✅)
- ✅ **Multi-turn Conversations** - Persistent session management with full history
- ✅ **Hybrid Storage** - Redis cache (< 10ms) + PostgreSQL audit trail
- ✅ **MCP Tool Integration** - Access to 115 EVE Online tools via conversation
- ✅ **Session Persistence** - Sessions survive server restarts
- ✅ **REST API** - `POST /agent/chat`, `GET /agent/session/{id}`, `DELETE /agent/session/{id}`

See [Phase 1 Completion Report](docs/agent/phase1-completion.md) for details.

#### Phase 2: Plan Detection & Approval (Complete ✅)
- ✅ **Multi-Tool Plan Detection** - Automatically detects when LLM proposes 3+ tool workflows
- ✅ **Auto-Execute Decision Matrix** - L0-L3 autonomy levels control auto-execution
- ✅ **Plan Approval/Rejection API** - `POST /agent/execute`, `POST /agent/reject`
- ✅ **Plan Lifecycle Tracking** - PostgreSQL storage with full audit trail
- ✅ **Risk Level Analysis** - Determines max risk level across all plan steps
- ✅ **Full Test Coverage** - 21 tests (100% passing)

See [Phase 2 Completion Report](docs/agent/phase2-completion.md) for details.

#### Phase 3: Real-time Events & Authorization (Complete ✅)
- ✅ **Event System** - 19 event types across session, planning, execution, and control
- ✅ **EventBus** - In-memory real-time event distribution with session isolation
- ✅ **Event Repository** - PostgreSQL audit trail with full timeline reconstruction
- ✅ **WebSocket Streaming** - `WS /agent/stream/{session_id}` for real-time updates
- ✅ **Authorization Integration** - Per-tool blacklist + dangerous pattern detection
- ✅ **Retry Logic** - Exponential backoff with configurable retry policies
- ✅ **Full Test Coverage** - 31 tests (100% passing)

See [Phase 3 Completion Report](docs/agent/phase3-completion.md) for details.

#### Phase 4: Frontend Integration (Complete ✅)
- ✅ **React Components** - Event stream display, plan approval card, progress indicators
- ✅ **WebSocket Client** - Real-time event streaming with auto-reconnect
- ✅ **TypeScript Types** - Complete type system matching backend (19 event types)
- ✅ **Agent Dashboard** - Session management, autonomy level selection, event monitoring
- ✅ **Plan Approval UI** - Interactive plan review with approve/reject workflow
- ✅ **Retry Visualization** - Visual feedback for retry attempts with exponential backoff
- ✅ **Dark Mode** - Consistent EVE Online aesthetic with color-coded events
- ✅ **Full Test Coverage** - 9 tests (100% passing)

See [Phase 4 Completion Report](docs/agent/phase4-completion.md) for details.

#### Phase 5: Chat Interface & Advanced Features (Complete ✅)
- ✅ **Chat Components** - Message input with Ctrl+Enter, conversation history, markdown rendering
- ✅ **Markdown Support** - Syntax highlighting, tables, code blocks (react-markdown + highlight.js)
- ✅ **Character Selection** - Select EVE character (Artallus, Cytrex, Cytricia) for sessions
- ✅ **Event Filtering** - Multi-select dropdown for 19 event types with select all/clear all
- ✅ **Event Search** - Search by event type and payload content with clear button
- ✅ **Session Persistence** - localStorage support for session ID and autonomy level
- ✅ **Keyboard Shortcuts** - Ctrl+K (search), Ctrl+L (clear), Ctrl+/ (help), Esc (clear filters)
- ✅ **Streaming Support** - useStreamingMessage hook for real-time LLM responses
- ✅ **Full Test Coverage** - 68 tests (100% passing)

See [Phase 5 Completion Report](docs/agent/phase5-completion.md) for details.

**Access:** Navigate to `/agent` in the frontend to use the Agent Dashboard

#### Future Enhancements (Phase 6+)
- ⏳ **Backend Chat Integration** - Wire chat UI to `/agent/chat` endpoint with message history
- ⏳ **SSE Streaming** - Server-Sent Events for streaming LLM responses
- ⏳ **Authorization UI** - Tool blacklist management interface
- ⏳ **Multi-Session** - Switch between multiple agent sessions
- ⏳ **Analytics Dashboard** - Performance metrics and insights
- ⏳ **Collaboration** - Share sessions with team members

**What it does:**
- Create conversational sessions with AI agent
- Execute EVE Online operations through natural language
- Automatic tool selection from 115 available MCP tools
- Intelligent plan detection for complex multi-tool workflows
- Human-in-the-loop approval based on autonomy level and risk
- Full conversation history and audit trail
- Character-specific sessions with autonomy levels

**Example:**
```
User: "What profitable items can I manufacture in Jita?"
Agent: [Queries market data, analyzes production costs, returns recommendations]

User: "Create shopping list for 10 Caracals"
Agent: [Detects 3+ tool plan → waits for approval if L1/L2, auto-executes if L3]
```

**Auto-Execute Decision Matrix:**

| Autonomy Level | READ_ONLY Plan | WRITE_LOW_RISK Plan | WRITE_HIGH_RISK Plan |
|----------------|----------------|---------------------|----------------------|
| L0 (READ_ONLY) | ❌ Approve      | ❌ Approve           | ❌ Approve            |
| L1 (RECOMMENDATIONS) | ✅ Auto-Execute | ❌ Approve      | ❌ Approve            |
| L2 (ASSISTED)  | ✅ Auto-Execute | ✅ Auto-Execute     | ❌ Approve            |
| L3 (SUPERVISED) | ✅ Auto-Execute | ✅ Auto-Execute    | ✅ Auto-Execute       |

## Tech Stack

**Backend:**
- Python 3.11+ / FastAPI
- PostgreSQL 16 (EVE SDE + custom tables)
- ESI API integration with rate limiting

**Frontend:**
- React 18 / TypeScript 5
- Vite for development with code splitting
- TanStack Query (React Query v5)
- React Router v6
- Lucide React icons

## Documentation

- **[User Guide](docs/USER_GUIDE.md)** - Complete user guide with screenshots
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment instructions
- **[API Documentation](docs/api/README.md)** - Detailed API reference
- **[Architecture](ARCHITECTURE.md)** - System architecture overview
- **Developer Guides:**
  - [Main Development Guide](CLAUDE.md) - Core principles and workflows
  - [Backend Development](CLAUDE.backend.md) - FastAPI, Database, ESI
  - [Frontend Development](CLAUDE.frontend.md) - React, TypeScript, Vite

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 16 (Docker recommended)
- EVE Developer Application ([Register here](https://developers.eveonline.com/))

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/CytrexSGR/Eve-Online-Copilot.git
cd Eve-Online-Copilot
```

2. **Configure the application**
```bash
cp config.example.py config.py
# Edit config.py with your credentials:
# - Database connection
# - EVE SSO Client ID & Secret
# - Discord webhook (optional)
```

3. **Install backend dependencies**
```bash
pip install fastapi uvicorn psycopg2-binary requests aiohttp
```

4. **Install frontend dependencies**
```bash
cd frontend
npm install
```

5. **Start the database**
```bash
docker run -d --name eve_db \
  -e POSTGRES_USER=eve \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=eve_sde \
  -p 5432:5432 \
  postgres:16
```

6. **Import EVE SDE** (Static Data Export)
   - Download from [Fuzzwork](https://www.fuzzwork.co.uk/dump/)
   - Import into PostgreSQL

7. **Run migrations**
```bash
psql -U eve -d eve_sde -f migrations/001_bookmarks.sql
psql -U eve -d eve_sde -f migrations/002_shopping.sql
psql -U eve -d eve_sde -f migrations/003_war_room.sql
```

### Running the Application

**Backend:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Project Structure

```
eve_copilot/
├── main.py                 # FastAPI application
├── config.py               # Configuration
├── database.py             # PostgreSQL connection
├── esi_client.py           # ESI API client
├── auth.py                 # EVE SSO OAuth2
├── character.py            # Character & corp API
│
├── # Core Services
├── market_service.py       # Market price caching
├── production_simulator.py # Manufacturing calculations
├── shopping_service.py     # Shopping list management
├── route_service.py        # A* route calculation
├── killmail_service.py     # Combat loss analysis
├── war_analyzer.py         # Demand & doctrine detection
│
├── services/               # New service modules
│   ├── dashboard_service.py
│   ├── portfolio_service.py
│   ├── research_service.py
│   └── production/         # Production services
│       ├── chain_service.py
│       ├── economics_service.py
│       └── workflow_service.py
│
├── routers/                # API route modules (16 routers)
│   ├── auth.py
│   ├── character.py
│   ├── production.py
│   ├── production_chains.py
│   ├── production_economics.py
│   ├── production_workflow.py
│   ├── market.py
│   ├── shopping.py
│   ├── dashboard.py
│   ├── research.py
│   └── war.py
│
├── jobs/                   # Cron jobs
│   ├── batch_calculator.py
│   ├── regional_price_fetcher.py
│   ├── market_hunter.py
│   ├── killmail_fetcher.py
│   ├── sov_tracker.py
│   └── fw_tracker.py
│
├── migrations/             # SQL migrations
│
└── frontend/               # React application
    └── src/
        ├── pages/          # 15 page components (lazy-loaded)
        ├── components/     # Reusable components
        ├── hooks/          # Custom hooks (keyboard shortcuts)
        └── api.ts          # API client
```

## API Overview

### Authentication
- `GET /api/auth/login` - Initiate EVE SSO login
- `GET /api/auth/callback` - OAuth2 callback
- `GET /api/auth/characters` - List authenticated characters

### Dashboard & Portfolio
- `GET /api/dashboard/opportunities` - Market opportunities
- `GET /api/dashboard/characters/portfolio` - Portfolio analysis
- `GET /api/dashboard/projects` - Active projects

### Production
- `GET /api/production/optimize/{type_id}` - Regional production analysis
- `GET /api/production/chains/{type_id}` - Full production chain
- `GET /api/production/economics/{type_id}` - Economic analysis
- `POST /api/production/workflow/jobs` - Create production job

### Market
- `GET /api/market/compare/{type_id}` - Multi-region price comparison
- `GET /api/market/arbitrage/{type_id}` - Arbitrage opportunities
- `GET /api/arbitrage/enhanced/{type_id}` - Enhanced arbitrage with routing

### Shopping
- `GET /api/shopping/lists` - Get shopping lists
- `POST /api/shopping/lists/{id}/add-production/{type_id}` - Add materials
- `GET /api/shopping/lists/{id}/regional-comparison` - Compare regions
- `POST /api/shopping/wizard/calculate-materials` - Wizard calculation

### War Room
- `GET /api/war/losses/{region_id}` - Combat losses
- `GET /api/war/demand/{region_id}` - Demand analysis with market gaps
- `GET /api/war/doctrines/{region_id}` - Doctrine detection
- `GET /api/war/campaigns` - Sovereignty campaigns
- `GET /api/war/campaigns/update` - Update sov campaigns
- `GET /api/war/fw/hotspots` - FW hotspots
- `GET /api/war/fw/vulnerable` - Vulnerable FW systems
- `GET /api/war/fw/update` - Update FW status
- `GET /api/war/system/{system_id}/danger` - System danger score
- `GET /api/war/top-ships` - Most destroyed ships
- `GET /api/war/alerts` - War alerts
- `GET /api/war/live/kills` - Live killmail stream (zKillboard + ESI)
- `GET /api/war/live/hotspots` - Active combat hotspots (last hour)
- `GET /api/war/live/demand/{item_type_id}` - Real-time item destruction demand
- `GET /api/war/live/demand/top` - Most destroyed items (24h)
- `GET /api/war/live/stats` - Live service statistics

### Research
- `GET /api/research/skills-for-item/{type_id}` - Required skills
- `GET /api/research/recommendations/{character_id}` - Skill recommendations

Full API documentation available at `/docs` when running.

## Background Services

### Cron Jobs
| Job | Schedule | Description |
|-----|----------|-------------|
| batch_calculator | */5 min | Calculate manufacturing opportunities |
| regional_price_fetcher | */30 min | Update regional market prices |
| market_hunter | */5 min | Scan for profitable items |
| killmail_fetcher | Daily 06:00 | Download killmail archives (EVE Ref) |
| sov_tracker | */30 min | Update sovereignty campaigns |
| fw_tracker | */30 min | Update faction warfare status |

### Long-running Services
| Service | Type | Description |
|---------|------|-------------|
| zkill_live_listener | Daemon | Real-time killmail stream from zKillboard |

**Start Live Listener:**
```bash
# In background (recommended with systemd or screen)
python3 -m jobs.zkill_live_listener --verbose

# Or in screen session
screen -dmS zkill python3 -m jobs.zkill_live_listener --verbose
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

EVE Online and all related logos and images are trademarks or registered trademarks of CCP hf. This application is not affiliated with or endorsed by CCP hf.

## Acknowledgments

- [EVE ESI](https://esi.evetech.net/) - EVE Swagger Interface
- [Fuzzwork](https://www.fuzzwork.co.uk/) - EVE Static Data Export
- [EVE Ref](https://everef.net/) - Killmail data
