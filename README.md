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
- `GET /api/war/top-ships` - Most destroyed ships

### Research
- `GET /api/research/skills-for-item/{type_id}` - Required skills
- `GET /api/research/recommendations/{character_id}` - Skill recommendations

Full API documentation available at `/docs` when running.

## Cron Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| batch_calculator | */5 min | Calculate manufacturing opportunities |
| regional_price_fetcher | */30 min | Update regional market prices |
| market_hunter | */5 min | Scan for profitable items |
| killmail_fetcher | Daily 06:00 | Download killmail data |
| sov_tracker | */30 min | Update sovereignty campaigns |
| fw_tracker | */30 min | Update faction warfare status |

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
