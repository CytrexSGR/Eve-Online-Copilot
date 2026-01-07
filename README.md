# EVE Co-Pilot

![Alpha](https://img.shields.io/badge/Status-Alpha-yellow?style=for-the-badge) ![Under Development](https://img.shields.io/badge/Under-Development-orange?style=for-the-badge)

Comprehensive intelligence and industry platform for EVE Online. Two frontends: public combat intelligence dashboard and internal production tools.

> ⚠️ **Alpha Software**: This project is in active development. Features may be incomplete, data may be inaccurate, and breaking changes can occur. Use at your own risk!

## 🌐 Live Public Dashboard (Alpha)

**[🚀 https://eve.infinimind-creations.com](https://eve.infinimind-creations.com)** ⚠️ Alpha Version

Free real-time combat intelligence dashboard with:
- 📊 **24-Hour Battle Reports** - Track combat activity across New Eden
- 🗺️ **3D Galaxy Combat Map** - Interactive visualization of all battles
- 💰 **War Profiteering** - Most destroyed items and market opportunities
- ⚔️ **Alliance Wars** - Active conflicts and combat statistics
- 🛣️ **Trade Route Safety** - Danger analysis for cargo routes

**No login required. Updates daily from zKillboard + ESI.**

## 📱 Live Telegram Alerts

**[📢 Join: t.me/infinimind_eve](https://t.me/infinimind_eve)**

Get real-time combat intelligence delivered directly to your phone:

### 🚨 Combat Hotspot Alerts (Real-time)
Instant notifications when combat spikes are detected (5+ kills in 5 minutes):
- 📍 System location with security status and region
- 🔥 Kill count and activity rate
- 💰 Total ISK destroyed with ship breakdowns
- 🎯 Intelligent danger level (🟢 LOW → 🔴 EXTREME)
- ⚔️ Attacking forces (alliances/corps involved)
- 💀 Top 5 most expensive ship losses
- 🚨 Gate camp detection with confidence rating

### 📊 Scheduled Reports
- **Battle Reports** - Every hour: 24h combat statistics, hot zones, peak activity
- **Alliance Wars** - Every 30 minutes: Active conflicts, K/D ratios, efficiency ratings
- **War Profiteering** - Every 6 hours: Most destroyed items, market opportunities

**Alert cooldown:** 10 minutes per system to prevent spam during extended battles.

---

![Status](https://img.shields.io/badge/Status-Alpha-yellow)
![EVE Online](https://img.shields.io/badge/EVE-Online-orange)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![React](https://img.shields.io/badge/React-18-61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6)
![License](https://img.shields.io/badge/License-MIT-green)
![Website](https://img.shields.io/website?url=https%3A%2F%2Feve.infinimind-creations.com&label=Live)
![Telegram](https://img.shields.io/badge/Telegram-Join%20Alerts-2CA5E0?logo=telegram)

---

## 🎮 Core Features

### 🏭 Production & Manufacturing
- **Production Planner** - Calculate manufacturing costs with ME/TE bonuses, regional pricing
- **Material Chain Analysis** - Full recursive breakdown of all materials needed (raw → components → final product)
- **Regional Economics** - Compare profitability across all regions, identify best manufacturing locations
- **Production Workflow** - Track multiple production jobs, batch processing, job status management
- **Material Classifier** - Difficulty scoring for material acquisition (market availability, price volatility)

### 💰 Market Intelligence
- **Arbitrage Finder** - Cross-region price differences with route planning and profit calculations
- **Market Hunter** - Automated scanning of 2000+ T1 items for profitable manufacturing opportunities
- **Live Market Data** - Real-time ESI API integration with order depth analysis and market spread
- **Price History** - Historical price tracking, trend analysis, volatility scoring
- **Market Gaps** - Identify supply shortages and high-demand items

### 📦 Shopping & Logistics
- **Shopping Wizard** - Guided list creation with automatic best-price finding across regions
- **Multi-Region Price Comparison** - Compare prices for entire shopping lists across trade hubs
- **Route Optimization** - A* pathfinding for multi-stop shopping routes with jump/distance calculations
- **Cargo Calculator** - Volume calculations, transport ship recommendations (Iterons, DST, Freighters)
- **Build vs Buy Analysis** - Automatic comparison of manufacturing vs purchasing with material recursion
- **Material Expansion** - Recursive blueprint breakdown with option to build or buy sub-components

### ⚔️ Combat Intelligence (Public Dashboard)
- **24-Hour Battle Reports** - Total kills, ISK destroyed, peak activity hours, regional breakdown
- **3D Galaxy Map** - Interactive Three.js visualization with real-time hotspot updates
- **War Profiteering** - Track most destroyed items, market opportunities from combat losses
- **Alliance Wars** - Active conflicts, kill/loss statistics, efficiency ratings, war zones
- **Trade Route Safety** - Danger scoring based on recent kills along trade corridors
- **Capital Tracking** - Monitor Titan, Supercarrier, Carrier, Dreadnought, and FAX losses
- **Doctrine Detection** - Identify fleet compositions from loss patterns

### 👤 Character Management
- **EVE SSO OAuth2** - Secure authentication with multiple character support
- **Multi-Character Portfolio** - Aggregate view of wallets, assets, skills across all characters
- **Wallet Tracking** - Real-time balance monitoring, transaction history
- **Asset Management** - View all character/corp assets with location filtering
- **Industry Jobs** - Monitor manufacturing, research, copying, invention jobs
- **Corporation Support** - Corp wallet divisions, member lists, roles
- **Skill Planning** - Required skills for items, training time calculations, skill recommendations

### 🗺️ Navigation & Routes
- **A* Route Calculator** - Optimal pathfinding between any two systems
- **Trade Hub Routes** - Pre-calculated distances to major hubs (Jita, Amarr, Dodixie, Rens, Hek)
- **Danger Scoring** - Route safety based on recent combat activity (kills/hour, ship types destroyed)
- **Shopping Routes** - Optimized multi-stop paths for shopping lists
- **System Search** - Fast lookup of systems, regions, constellations

---

## 🤖 AI Agent (Conversational Interface)

Natural language interface to all 115 EVE tools through Claude AI:

**Features:**
- Multi-turn conversations with full session history
- Automatic tool selection for EVE operations
- Plan detection for complex multi-step workflows
- Configurable autonomy levels (L0-L3)
- Real-time WebSocket event streaming
- Full audit trail and replay capability

**Example:**
```
User: "What profitable items can I manufacture in Jita?"
Agent: [Analyzes market data, production costs, returns recommendations]

User: "Create shopping list for 10 Caracals"
Agent: [Detects multi-tool plan, requests approval based on autonomy level]
```

See [Agent Documentation](docs/agent/) for details.

---

## 🏗️ Tech Stack

**Backend:**
- FastAPI 0.104+ with async/await
- PostgreSQL 16 (EVE SDE data + application state)
- Redis (session cache)
- ESI API integration with rate limiting
- MCP (Model Context Protocol) - 115 tools

**Public Frontend** (`/public-frontend`):
- React 18 + TypeScript 5
- Three.js - 3D galaxy visualization
- Vite - Build tooling
- Auto-refresh every 60s

**Internal Frontend** (`/frontend`):
- React 18 + TypeScript 5
- React Query - Data caching
- Lazy-loaded pages with code splitting
- Keyboard shortcuts

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 16
- Redis (optional, for agent sessions)

### Setup

```bash
# Clone repository
git clone https://github.com/CytrexSGR/Eve-Online-Copilot.git
cd Eve-Online-Copilot

# Backend setup
pip install -r requirements.txt
cp config.example.py config.py
# Edit config.py with your database credentials

# Start backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Public frontend setup (separate terminal)
cd public-frontend
npm install
npm run dev

# Internal frontend setup (separate terminal)
cd frontend
npm install
npm run dev
```

### Access Points
- **Public Dashboard:** http://localhost:5173
- **Internal Tools:** http://localhost:5174
- **API Docs:** http://localhost:8000/docs
- **Agent Interface:** http://localhost:5174/agent

---

## 📊 Data Sources

- **zKillboard** - Combat data (daily killmail downloads)
- **ESI API** - EVE Online official API
- **EVE SDE** - Static Data Export (PostgreSQL)
- **Discord Webhooks** - Combat alerts and notifications

---

## 📚 Documentation

| Topic | Location |
|-------|----------|
| **Development Guide** | [CLAUDE.md](CLAUDE.md) |
| **Architecture** | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **Agent Runtime** | [docs/agent/](docs/agent/) |
| **Backend Development** | [CLAUDE.backend.md](CLAUDE.backend.md) |
| **Frontend Development** | [CLAUDE.frontend.md](CLAUDE.frontend.md) |

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🔗 Links

- **Live Dashboard:** https://eve.infinimind-creations.com
- **Telegram Alerts:** https://t.me/infinimind_eve
- **GitHub Issues:** https://github.com/CytrexSGR/Eve-Online-Copilot/issues
- **EVE Online:** https://www.eveonline.com

---

**Built by capsuleers, for capsuleers.** 🚀
