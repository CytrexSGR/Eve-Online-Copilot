# EVE Co-Pilot Evolution Plan
**From API Backend to AI Gaming Assistant**

## 🎯 Vision

Transform EVE Co-Pilot from a REST API backend into a full AI gaming assistant with:
- 🎤 **Voice Interface** - Talk to your copilot while playing
- 🤖 **LLM Integration** - Natural language understanding via MCP
- 🌐 **Web Frontend** - Modern chat interface with audio
- 📊 **Real-time Updates** - Live market data and alerts
- 🎮 **In-Game Assistant** - Contextual help and automation

---

## 📊 Current State Analysis

### ✅ What We Have

**Backend (FastAPI):**
- 118 API endpoints across 16 routers
- Real-time ESI data integration
- PostgreSQL database with EVE SDE
- Character authentication (OAuth2)
- Production, market, war room analytics

**MCP Integration (Basic):**
- 17 MCP tools (14% coverage)
- Node.js proxy for Claude Desktop
- Character/market/production basics

**Frontend:**
- React 18 + TypeScript dashboard
- 15 pages (lazy-loaded)
- Market scanner, production planner, shopping wizard
- War room analytics

### ❌ What's Missing

**MCP Coverage:**
- 101 endpoints not exposed via MCP (86%)
- No War Room MCP tools
- No Shopping/Dashboard/Research tools
- No bulk operations support

**AI Integration:**
- No web-based LLM interface
- No audio input/output
- No conversation memory
- No context awareness
- No streaming responses

**Real-time Features:**
- No WebSocket support
- No live notifications
- No price alerts
- No job completion alerts

---

## 🏗️ Architecture Design

### Target Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     User Interfaces                           │
├──────────────┬──────────────────────┬────────────────────────┤
│  Web Chat    │  Voice Interface     │  Claude Desktop MCP    │
│  (Browser)   │  (Audio I/O)         │  (Existing)            │
└──────┬───────┴──────────┬───────────┴────────────┬───────────┘
       │                  │                        │
       │    WebSocket     │    WebRTC/WS           │    stdio
       │                  │                        │
┌──────▼──────────────────▼────────────────────────▼───────────┐
│              AI Copilot Server (New)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  LLM Integration Layer                                │   │
│  │  - Anthropic Claude API                               │   │
│  │  - OpenAI (optional)                                  │   │
│  │  - Local LLMs (Ollama, optional)                      │   │
│  │  - Conversation memory (Redis)                        │   │
│  │  - Context management                                 │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                         │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │  MCP Server (Enhanced)                                │   │
│  │  - 118 MCP tools (full API coverage)                  │   │
│  │  - Tool categories (Market, War, Production, etc.)    │   │
│  │  - Batch operations                                   │   │
│  │  - Smart tool chaining                                │   │
│  └──────────────────┬───────────────────────────────────┘   │
└────────────────────┬┘                                        │
                     │                                          │
┌────────────────────▼─────────────────────────────────────────┐
│              Existing FastAPI Backend                         │
│  - 118 REST endpoints                                         │
│  - Database (PostgreSQL)                                      │
│  - ESI Integration                                            │
│  - Auth (OAuth2)                                              │
└───────────────────────────────────────────────────────────────┘
```

### Component Breakdown

#### 1. AI Copilot Server (New Service)
**Technology:** Python + FastAPI + WebSockets
**Port:** 8001
**Responsibilities:**
- LLM conversation management
- Context awareness (current system, character, etc.)
- Audio transcription (Whisper API)
- Text-to-speech (ElevenLabs / OpenAI TTS)
- WebSocket connections
- Session management

#### 2. Enhanced MCP Server
**Expand:** `/mcp/tools/` endpoints
**Add:** 101 new MCP tools
**Features:**
- Full API coverage (118 tools)
- Tool categorization
- Batch operations
- Smart defaults
- Error handling with retries

#### 3. Web Chat Interface
**Technology:** React + TypeScript + Vite
**Features:**
- ChatGPT-like interface
- Markdown rendering
- Code syntax highlighting
- Voice input button
- Audio playback
- Conversation history
- Context panel (current character, region, etc.)

#### 4. Audio Pipeline
**Input:** Browser MediaRecorder → WebSocket → Whisper API
**Output:** OpenAI TTS / ElevenLabs → Audio stream → Browser
**Features:**
- Push-to-talk / Voice activation
- Noise cancellation
- Low latency (<500ms)

---

## 📋 Implementation Plan

### Phase 1: MCP Tool Expansion (Week 1-2)

**Goal:** Complete MCP tool coverage for all 118 endpoints

**Tasks:**
1. ✅ **Audit Current Coverage** (Done: 17/118 tools)
2. **Generate MCP Tool Definitions**
   - Create tool schemas for all endpoints
   - Group by category (Market, Production, War, Shopping, etc.)
   - Add examples and best practices

3. **Implement Missing Tools:**
   - War Room: 16 tools (losses, demand, campaigns, fw, alerts)
   - Shopping: 26 tools (lists, items, wizard, cargo)
   - Dashboard: 5 tools (opportunities, portfolio, projects)
   - Research: 2 tools (skills, recommendations)
   - Production Chains: 3 tools
   - Production Economics: 3 tools
   - Production Workflow: 3 tools
   - Items & Materials: 6 tools
   - Bookmarks: 9 tools
   - Mining: 3 tools
   - Market (expanded): 5 tools

4. **Add Batch Operations:**
   - `batch_get_market_stats` - Multiple items at once
   - `batch_production_cost` - Multiple items
   - `analyze_portfolio` - All characters at once
   - `scan_opportunities` - Multi-category scan

5. **Smart Tool Chains:**
   - `plan_production_run` - Combines search, cost, materials, shopping
   - `find_best_arbitrage` - Scans all groups automatically
   - `war_room_summary` - Aggregates all war data

**Deliverables:**
- `routers/mcp.py` updated with 118 tools
- `mcp_tools.json` with complete definitions
- Documentation in `docs/MCP_TOOLS.md`
- Test suite for MCP tools

---

### Phase 2: AI Copilot Server (Week 3-4)

**Goal:** Build the LLM integration layer

**File Structure:**
```
copilot_server/
├── main.py                 # FastAPI app with WebSocket
├── llm/
│   ├── anthropic_client.py # Claude API integration
│   ├── openai_client.py    # OpenAI (optional)
│   ├── conversation.py     # Context management
│   └── memory.py           # Redis-based memory
├── audio/
│   ├── transcription.py    # Whisper API
│   ├── tts.py              # Text-to-speech
│   └── stream.py           # Audio streaming
├── mcp/
│   ├── client.py           # MCP tool calling
│   ├── tools.py            # Tool registry
│   └── planner.py          # Multi-tool orchestration
└── websocket/
    ├── handler.py          # WebSocket connections
    ├── sessions.py         # Session management
    └── auth.py             # User authentication
```

**API Design:**
```python
# WebSocket connection
ws://localhost:8001/copilot/ws/{session_id}

# REST endpoints
POST /copilot/chat              # Send message
GET  /copilot/sessions          # List sessions
POST /copilot/sessions          # Create session
GET  /copilot/context           # Get current context
POST /copilot/context           # Update context
POST /copilot/audio/transcribe  # Audio → Text
POST /copilot/audio/synthesize  # Text → Audio
```

**Key Features:**
1. **Conversation Management:**
   - Thread-based conversations
   - Context window management (100k tokens)
   - Automatic summarization
   - Conversation export

2. **Tool Orchestration:**
   - Automatic MCP tool selection
   - Multi-tool workflows
   - Error recovery
   - Result aggregation

3. **Context Awareness:**
   - Current character (auto-detect or user-set)
   - Current region (default Jita)
   - Recent activity
   - Active projects

4. **Audio Pipeline:**
   - Whisper API for STT
   - OpenAI TTS or ElevenLabs
   - Streaming audio
   - Voice activity detection

**Deliverables:**
- Working AI Copilot Server on port 8001
- WebSocket connection handler
- LLM integration with tool calling
- Audio transcription pipeline
- Documentation

---

### Phase 3: Web Chat Interface (Week 5-6)

**Goal:** Modern chat UI with audio support

**File Structure:**
```
frontend_chat/
├── src/
│   ├── App.tsx             # Main app with WebSocket
│   ├── components/
│   │   ├── Chat/
│   │   │   ├── ChatWindow.tsx      # Message display
│   │   │   ├── ChatInput.tsx       # Text + Voice input
│   │   │   ├── Message.tsx         # Single message
│   │   │   └── AudioPlayer.tsx     # Audio playback
│   │   ├── Context/
│   │   │   ├── ContextPanel.tsx    # Current state
│   │   │   ├── CharacterSelect.tsx # Switch characters
│   │   │   └── RegionSelect.tsx    # Switch regions
│   │   └── Sidebar/
│   │       ├── SessionList.tsx     # Past conversations
│   │       └── Settings.tsx        # Preferences
│   ├── hooks/
│   │   ├── useWebSocket.ts         # WebSocket connection
│   │   ├── useAudio.ts             # Audio recording
│   │   └── useChat.ts              # Chat state
│   ├── services/
│   │   ├── api.ts                  # API client
│   │   ├── audio.ts                # Audio utilities
│   │   └── websocket.ts            # WebSocket client
│   └── types/
│       ├── message.ts              # Message types
│       └── context.ts              # Context types
```

**UI Design:**

```
┌────────────────────────────────────────────────────────────┐
│  EVE Co-Pilot                          [⚙️] [Character] [?] │
├──────────┬─────────────────────────────────────────────────┤
│Sessions  │  Chat Window                                    │
│          │  ┌────────────────────────────────────────────┐ │
│• Today   │  │ 🤖 How can I help with EVE Online today?  │ │
│  Market  │  │                                            │ │
│  Prod    │  └────────────────────────────────────────────┘ │
│          │  ┌────────────────────────────────────────────┐ │
│• Yester  │  │ 👤 Is it profitable to build Hobgoblin?   │ │
│  War     │  └────────────────────────────────────────────┘ │
│          │  ┌────────────────────────────────────────────┐ │
│[+ New]   │  │ 🤖 Let me check that for you...           │ │
│          │  │                                            │ │
│          │  │ [Market Stats Table]                       │ │
│          │  │ Production Cost: 24,500 ISK                │ │
│          │  │ Sell Price: 32,000 ISK                     │ │
│          │  │ Profit: 7,500 ISK (30.6%)                  │ │
│          │  │                                            │ │
│          │  │ Yes! It's profitable with ME 10.           │ │
│          │  └────────────────────────────────────────────┘ │
│          │                                                │
│          ├────────────────────────────────────────────────┤
│          │  Context: Cytrex @ Jita            [Tools: 3] │
│          ├────────────────────────────────────────────────┤
│          │  [Type message...] [🎤] [Send]                │
└──────────┴─────────────────────────────────────────────────┘
```

**Features:**
- ChatGPT-like interface
- Markdown rendering with syntax highlighting
- Tool call visualization (show which tools were used)
- Audio recording with visual feedback
- Context panel (character, region, recent activity)
- Session management
- Dark mode (EVE-themed)
- Mobile responsive

**Deliverables:**
- Working web chat interface
- WebSocket integration
- Audio recording & playback
- Context management UI
- Session history
- Documentation

---

### Phase 4: Integration & Testing (Week 7)

**Goal:** Connect all components and test end-to-end

**Tasks:**
1. **System Integration:**
   - Deploy all services together
   - Configure CORS and WebSocket
   - Set up reverse proxy (Nginx)
   - SSL certificates

2. **Testing:**
   - End-to-end conversation flows
   - Tool calling accuracy
   - Audio quality testing
   - Latency measurements
   - Error handling

3. **Optimization:**
   - Response time optimization
   - Audio compression
   - WebSocket connection pooling
   - LLM prompt optimization

4. **Documentation:**
   - User guide
   - API documentation
   - Deployment guide
   - Troubleshooting guide

**Deliverables:**
- Fully integrated system
- Test results
- Performance benchmarks
- Complete documentation

---

## 🛠️ Technology Stack

### AI Copilot Server
- **Framework:** FastAPI + WebSockets
- **LLM:** Anthropic Claude API (Sonnet 4.5)
- **Audio STT:** OpenAI Whisper API
- **Audio TTS:** OpenAI TTS or ElevenLabs
- **Memory:** Redis (conversation context)
- **Deployment:** Docker + Docker Compose

### Web Chat Frontend
- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite
- **UI:** TailwindCSS
- **WebSocket:** native WebSocket API
- **Audio:** MediaRecorder API
- **State:** TanStack Query + Zustand
- **Markdown:** react-markdown
- **Syntax:** Prism.js

### Infrastructure
- **Reverse Proxy:** Nginx
- **SSL:** Let's Encrypt
- **Monitoring:** Prometheus + Grafana (optional)
- **Logging:** Structured logging (JSON)

---

## 📊 MCP Tool Categories

### 1. Market Tools (12 tools)
- `search_item`, `get_item_info`
- `get_market_stats`, `compare_market_prices`
- `find_arbitrage`, `enhanced_arbitrage`
- `batch_market_stats` (new)
- `scan_market_opportunities` (new)

### 2. Production Tools (14 tools)
- `get_production_cost`, `simulate_build`
- `get_production_chains`, `get_chain_materials`
- `get_economics_opportunities`, `get_economics_regions`
- `create_production_job`, `list_production_jobs`
- `batch_production_cost` (new)
- `plan_production_run` (new - multi-tool chain)

### 3. War Room Tools (16 tools)
- `get_war_losses`, `get_war_demand`
- `get_war_heatmap`, `get_war_campaigns`
- `get_war_fw_hotspots`, `get_war_fw_vulnerable`
- `get_war_doctrines`, `get_war_conflicts`
- `get_war_top_ships`, `get_war_alerts`
- `get_system_danger`, `get_safe_route`
- `get_item_combat_stats`
- `update_sov_campaigns`, `update_fw_status`
- `war_room_summary` (new - aggregated)

### 4. Shopping Tools (26 tools)
- All existing shopping list operations
- Wizard operations
- Cargo calculations
- Regional comparisons
- `smart_shopping_list` (new - auto-optimization)

### 5. Character Tools (12 tools)
- All existing character operations
- `get_character_summary` (new - aggregated)
- `batch_character_info` (new - all characters)

### 6. Dashboard Tools (5 tools)
- `get_opportunities`, `get_portfolio`
- `get_projects`, `get_character_summary`

### 7. Research Tools (2 tools)
- `get_skills_for_item`
- `get_skill_recommendations`

### 8. Utility Tools (10 tools)
- `search_systems`, `calculate_route`
- `get_regions`, `get_trade_hubs`
- `calculate_cargo`, `recommend_transport`
- `get_bookmarks`, `create_bookmark`

---

## 💰 Cost Estimation

### API Costs (Monthly)
- **Claude API (Sonnet 4.5):** ~$50-200 (depending on usage)
- **Whisper API:** ~$10-30 (audio transcription)
- **OpenAI TTS:** ~$10-30 (voice synthesis)
- **Total:** ~$70-260/month for moderate usage

### Infrastructure
- **Current:** Already running (no additional cost)
- **Redis:** Can use free tier or local instance
- **SSL:** Free (Let's Encrypt)

---

## 🎯 Success Metrics

### Phase 1 (MCP)
- ✅ 118/118 endpoints have MCP tools (100%)
- ✅ All tools tested and documented
- ✅ Average tool execution time <500ms

### Phase 2 (AI Server)
- ✅ LLM response time <2s (excluding tool execution)
- ✅ Audio transcription latency <500ms
- ✅ WebSocket connection stability >99%
- ✅ Tool calling accuracy >95%

### Phase 3 (Web UI)
- ✅ Chat interface loads <1s
- ✅ Voice recording works on Chrome/Firefox
- ✅ Mobile responsive design
- ✅ User satisfaction (subjective)

### Phase 4 (Integration)
- ✅ End-to-end conversation success rate >95%
- ✅ Zero critical bugs in production
- ✅ Complete documentation
- ✅ User adoption (you using it daily!)

---

## 🚀 Quick Start (After Implementation)

### Start All Services
```bash
# Start backend
cd /home/cytrex/eve_copilot
uvicorn main:app --host 0.0.0.0 --port 8000

# Start AI Copilot Server
cd copilot_server
uvicorn main:app --host 0.0.0.0 --port 8001

# Start Web Chat
cd frontend_chat
npm run dev
```

### Access Points
- **Web Chat:** http://localhost:5174
- **AI Copilot API:** http://localhost:8001
- **Backend API:** http://localhost:8000
- **Claude Desktop:** Use existing MCP proxy

---

## 📝 Next Steps

1. **Review this plan** - Adjust based on your priorities
2. **Choose Phase 1 starting point** - MCP tool expansion
3. **Set up development environment** - Create `copilot_server/` directory
4. **Start implementation** - One phase at a time

**Estimated Total Time:** 7 weeks for full implementation
**Recommended Approach:** Incremental development with working prototypes at each phase

---

**Created:** 2025-12-22
**Status:** Planning Phase
**Next Action:** Begin Phase 1 - MCP Tool Expansion
