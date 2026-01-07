# EVE Co-Pilot

Comprehensive intelligence and industry platform for EVE Online. Two frontends: public combat intelligence dashboard and internal production tools.

## 🌐 Live Public Dashboard

**[🚀 https://eve.infinimind-creations.com](https://eve.infinimind-creations.com)**

Free real-time combat intelligence dashboard with:
- 📊 **24-Hour Battle Reports** - Track combat activity across New Eden
- 🗺️ **3D Galaxy Combat Map** - Interactive visualization of all battles
- 💰 **War Profiteering** - Most destroyed items and market opportunities
- ⚔️ **Alliance Wars** - Active conflicts and combat statistics
- 🛣️ **Trade Route Safety** - Danger analysis for cargo routes

**No login required. Updates daily from zKillboard + ESI.**

---

![EVE Online](https://img.shields.io/badge/EVE-Online-orange)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![React](https://img.shields.io/badge/React-18-61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6)
![License](https://img.shields.io/badge/License-MIT-green)
![Website](https://img.shields.io/website?url=https%3A%2F%2Feve.infinimind-creations.com&label=Dashboard)

---

## 🔧 Internal Tools (Private)

Industry and market analysis tools for authenticated users:

**Production & Manufacturing:**
- Production planner with ME/TE calculations
- Material chain analysis and visualization
- Regional economics and profitability
- Production workflow management

**Market Analysis:**
- Cross-region arbitrage finder with routing
- Automated market hunter for profitable opportunities
- Live market data with order depth analysis

**Shopping & Logistics:**
- Shopping wizard with price comparison
- Multi-region route optimization
- Cargo calculations and transport recommendations
- Build vs buy decision analysis

**Character Management:**
- EVE SSO OAuth2 integration
- Wallet, assets, and industry jobs
- Corporation support (wallets, members)
- Skill requirements and recommendations

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
| **SEO & Marketing** | [docs/SEO-SUBMISSION.md](docs/SEO-SUBMISSION.md) |
| **GitHub Visibility** | [docs/GITHUB-VISIBILITY.md](docs/GITHUB-VISIBILITY.md) |

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
- **GitHub Issues:** https://github.com/CytrexSGR/Eve-Online-Copilot/issues
- **EVE Online:** https://www.eveonline.com

---

**Built by capsuleers, for capsuleers.** 🚀
