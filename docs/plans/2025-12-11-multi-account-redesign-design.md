# EVE Co-Pilot 2.0 - Multi-Account Redesign

**Date:** 2025-12-11
**Status:** Design Phase
**Authors:** Cytrex, Claude

---

## Executive Summary

EVE Co-Pilot 2.0 redesigns the application to optimize for **flexible 3-account management** with two distinct usage modes:

- **Quick Mode (Dashboard)** - Fast decisions, immediate actions
- **Deep Analysis Mode** - Detailed planning, multi-character coordination

### Key Problems Solved

1. **Unpraktische UI** - 14 separate pages → 5 activity-based sections
2. **Kein Multi-Account Überblick** - Isolated characters → Aggregated dashboard
3. **Unflexible Workflows** - Fixed paths → Context-aware modes
4. **Versteckte War Room Intel** - Separate section → Integrated demand alerts

---

## Design Goals

### Primary Goals
1. **Schneller Überblick** - See all 3 characters, opportunities, and alerts on one screen
2. **Flexible Workflows** - Support both quick actions and deep analysis
3. **War Room Integration** - Surface combat intelligence as profitable opportunities
4. **Character Context** - Only ask "which character?" when necessary

### User Priorities (from requirements)
1. Industrie (Production, Shopping)
2. Handel (Trading, Arbitrage)
3. Forschung (Research - integrated with production goals)
4. Mining (Location finding)
5. PVE (excluded - YAGNI)

---

## Architecture Overview

### Navigation Structure

```
🏠 Dashboard          → Quick Actions + Multi-Char Overview
🏭 Industrie          → Production + Shopping + Materials
💰 Handel             → Market Scanner + Arbitrage
⚔️ War Room          → Combat Intel + Demand + Hotspots
⚙️ Management        → Characters + Research + Mining + Bookmarks
```

**Changes from Current:**
- 14 pages → 5 main sections with sub-tabs
- Bookmarks moved to Management
- War Room alerts integrated into Dashboard
- Research gets dedicated UI (was API-only)

---

## Dashboard Design (Quick Mode)

### Layout Priority

```
┌─────────────────────────────────────────────────────────┬──────────────────┐
│                                                         │  War Room        │
│  OPPORTUNITIES FEED (60% height)                        │  Alerts          │
│                                                         │  ─────────────   │
│  Top 5 Profitable Actions (Industrie → Handel → War)   │  ⚠️ Sinq Laison │
│                                                         │  150 Gilas lost  │
│  [Item Card] [Item Card] [Item Card]                   │  Only 20 market  │
│  [Item Card] [Item Card]                               │                  │
│                                                         │  Top 3 War Items │
│                                                         │  ─────────────   │
├─────────────────────────────────────────────────────────┤                  │
│  CHARACTER OVERVIEW (20% height)                        │  Active Projects │
│                                                         │  ─────────────   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │  Shopping Lists  │
│  │ Artallus │  │ Cytrex   │  │ Cytricia │             │  Bookmarks       │
│  │ 250M ISK │  │ 180M ISK │  │ 95M ISK  │             │  Recent Builds   │
│  │ Isikemi  │  │ Jita     │  │ Dodixie  │             │                  │
│  │ Building │  │ Trading  │  │ Idle     │             │                  │
│  └──────────┘  └──────────┘  └──────────┘             │                  │
└─────────────────────────────────────────────────────────┴──────────────────┘
```

### Opportunities Feed

**Each Opportunity Card Shows:**
- Item Name + Icon
- Profit (absolute ISK) + ROI (percentage)
- Category Badge: 🏭 Production | 💰 Trade | ⚔️ War Demand
- Quick Action Button: "Build Now" | "Trade Now" | "View Details"

**Interaction Flow:**
1. User clicks "Build Now"
2. Character Selector appears: [Artallus ▼]
3. User selects character
4. System opens Production Planner pre-filled with item + character

**Data Source:**
- Combines existing: Market Scanner + Arbitrage + War Room Demand
- Sorted by user priorities (Industrie first)
- Filtered by profitability thresholds (configurable)

### Character Overview

**Each Character Card Shows:**
- ISK Balance (wallet)
- Current Location (system name)
- Active Status: "Building X - 2h left" | "Trading" | "Idle"
- Skill Queue: "Next: Advanced Industry V - 15d 3h"

**Interactions:**
- **Hover** → Tooltip with Assets summary, Active Orders count
- **Click** → Opens Character Detail in Management section

### War Room Alerts (Sidebar)

**Demand Alerts (Top):**
- Real-time alerts from combat losses
- Format: "⚠️ {Region}: {Count} {Ship} destroyed, only {Market_Stock} available"
- Click → Opens War Room Demand Analysis for that region

**Top 3 War Opportunities:**
- Items with highest demand-to-supply ratio
- Shows estimated profit per unit
- Click → Adds to Opportunities Feed or opens Production Planner

### Active Projects (Sidebar)

**Shows:**
- Shopping Lists in progress (with completion %)
- Recent Bookmarks (last 5)
- Recent Productions (completed in last 24h)

**Click Behavior:**
- Shopping List → Opens Shopping Planner
- Bookmark → Opens Item Detail
- Production → Shows production history

---

## Industrie Section (Deep Analysis)

### Sub-Tabs

**Tab 1: Production Planner**
- Current functionality maintained
- **New:** Character Selector at top
- **New:** "Calculate for all 3 characters" checkbox → shows which char has best setup (skills, assets)
- **New:** "Push to Dashboard" button → adds profitable items to Opportunities Feed

**Tab 2: Shopping Lists**
- Current multi-step wizard maintained
- **New:** Multi-Character mode → "Create list for: [Artallus] [Cytrex] [Cytricia]" checkboxes
- **New:** Batch operations → "Apply region change to all items"
- **New:** Transport planning → "Char A buys, Char B hauls, Char C builds" workflow

**Tab 3: Materials Overview**
- Current functionality maintained
- **New:** Filter by character → "Show materials available to [selected char]"
- **New:** Aggregated view → "Total materials across all 3 chars"

---

## Handel Section (Deep Analysis)

### Sub-Tabs

**Tab 1: Market Scanner**
- Current functionality maintained (pre-calculated opportunities)
- **New:** "Push to Dashboard" for selected items
- **New:** Character skill filter → "Show only items {character} can build"

**Tab 2: Arbitrage Finder**
- Current 3-panel layout maintained
- **New:** Character selector → Shows which char has ISK/cargo space for trade
- **New:** "Assign to character" → Creates shopping list for that char
- **New:** Route visualization with character location highlighting

---

## War Room Section (Deep Analysis)

### Sub-Tabs

**Tab 1: Demand Dashboard** (NEW - replaces multiple pages)
- **Top Section:** Regional selector + Time range (24h, 7d, 30d)
- **Middle:** Top 10 ships destroyed with:
  - Destruction count
  - Market stock
  - Gap ratio (destroyed/stock)
  - Estimated profit (gap * avg price)
- **Bottom:** Production recommendations → "Build these for max profit"

**Tab 2: Combat Hotspots**
- Current heatmap functionality
- **New:** Route danger overlay → "Your characters' locations" marked
- **New:** Opportunity scoring → Systems with high combat + low market stock nearby

**Tab 3: Intelligence**
- Combines: Sov Campaigns + FW Hotspots + Galaxy Summary
- Current functionality maintained
- **New:** "Watch Region" → Adds region to Dashboard War Alerts

---

## Management Section

### Sub-Tabs

**Tab 1: Characters**
- **3-Column Layout:** One column per character
- Each shows:
  - Wallet balance + transactions
  - Assets by location (grouped by station)
  - Active orders (buy/sell)
  - Industry jobs (running + history)
  - Corporation info

**Interactions:**
- Click asset → "Use in production" → Opens Production Planner
- Click order → "Modify" → Opens market interface (future)

**Tab 2: Research** (NEW)

**Skills for Production:**
- Input: Item name or blueprint
- Output: Required skills per character with training time
- Example: "T2 Ammo requires: Advanced Small Projectile Turret - Artallus needs 15d 3h"

**Skill Recommendations:**
- Analyzes your production history + current opportunities
- Suggests: "Train Cytrex in Advanced Industry V for +10% profit on current builds"

**Skill Queue Viewer:**
- Current ESI skill queue display (already exists in backend)
- Shows all 3 characters side-by-side

**Tab 3: Mining**
- Current location finder maintained
- **New:** Character location overlay → "Nearest {mineral} to {character}"
- **New:** Fleet coordination → "Optimal mining locations for 3 characters in same system"

**Tab 4: Bookmarks**
- Current functionality moved from main nav
- **New:** Shared bookmarks → "Mark as shared with corp/fleet"
- **New:** Bookmark categories → Industry, Trade, Combat, Mining

---

## Technical Architecture

### Backend Changes

#### New API Endpoints

```python
# Dashboard Aggregation
GET /api/dashboard/opportunities
Response: {
  "production": [...],  # Top manufacturing opportunities
  "trade": [...],       # Top arbitrage opportunities
  "war_demand": [...]   # Top combat demand opportunities
}

GET /api/dashboard/characters/summary
Response: [
  {
    "character_id": 526379435,
    "name": "Artallus",
    "isk_balance": 250000000,
    "location": {"system_id": 30001365, "system_name": "Isikemi"},
    "active_jobs": [{...}],
    "skill_queue": [{...}]
  },
  ...
]

GET /api/dashboard/war-alerts
Response: [
  {
    "region_id": 10000032,
    "region_name": "Sinq Laison",
    "ship_type_id": 16236,
    "ship_name": "Gila",
    "destroyed_count": 150,
    "market_stock": 20,
    "alert_level": "high"
  },
  ...
]

# Multi-Character Operations
GET /api/characters/portfolio
Response: {
  "total_isk": 525000000,
  "total_assets_value": 1200000000,
  "characters": [...]
}

POST /api/production/start
Body: {
  "character_id": 526379435,
  "type_id": 645,
  "runs": 10,
  "me_level": 10
}

POST /api/shopping/create
Body: {
  "character_ids": [526379435, 1117367444],
  "name": "Thorax Production",
  "items": [...]
}

# Research Planning (NEW)
GET /api/research/skills-for-item/{type_id}
Query: ?character_id=526379435
Response: {
  "required_skills": [
    {
      "skill_id": 3380,
      "skill_name": "Advanced Industry",
      "required_level": 5,
      "character_level": 4,
      "training_time_seconds": 1296000  # 15 days
    },
    ...
  ]
}

GET /api/research/recommendations/{character_id}
Response: [
  {
    "skill_id": 3380,
    "skill_name": "Advanced Industry",
    "reason": "Increases production efficiency for your top 5 builds",
    "estimated_profit_increase": 15000000,  # 15M ISK per month
    "training_time_seconds": 1296000
  },
  ...
]
```

#### New Services

**`dashboard_service.py`** (NEW)
- Aggregates opportunities from Market Hunter, Arbitrage, War Analyzer
- Sorts by user priorities (Industrie → Handel → War)
- Caches results for 5 minutes
- Filters by profitability thresholds

**`portfolio_service.py`** (NEW)
- Aggregates character data (wallets, assets, jobs)
- Calculates total portfolio value
- Tracks character locations

**`research_service.py`** (NEW)
- Parses blueprint requirements → required skills
- Compares with character skills from ESI
- Calculates training time using skill attributes
- Generates skill recommendations based on production history

**Enhanced `war_analyzer.py`**
- New method: `get_dashboard_alerts()` → Top 3 alerts for sidebar
- New method: `get_demand_opportunities()` → Profitable war items

### Frontend Changes

#### New Routes

```typescript
// App.tsx
<Route path="/" element={<Dashboard />} />
<Route path="/industrie" element={<Industrie />}>
  <Route path="production" element={<ProductionPlanner />} />
  <Route path="shopping" element={<ShoppingLists />} />
  <Route path="materials" element={<MaterialsOverview />} />
</Route>
<Route path="/handel" element={<Handel />}>
  <Route path="scanner" element={<MarketScanner />} />
  <Route path="arbitrage" element={<ArbitrageFinder />} />
</Route>
<Route path="/war-room" element={<WarRoom />}>
  <Route path="demand" element={<DemandDashboard />} />
  <Route path="hotspots" element={<CombatHotspots />} />
  <Route path="intelligence" element={<Intelligence />} />
</Route>
<Route path="/management" element={<Management />}>
  <Route path="characters" element={<Characters />} />
  <Route path="research" element={<Research />} />
  <Route path="mining" element={<Mining />} />
  <Route path="bookmarks" element={<Bookmarks />} />
</Route>
```

#### New Components

```typescript
// Dashboard Components
components/dashboard/
  OpportunitiesFeed.tsx          // Main opportunities list
  OpportunityCard.tsx            // Single opportunity card
  CharacterOverview.tsx          // 3 character cards
  CharacterCard.tsx              // Single character card
  WarRoomAlerts.tsx              // War alerts sidebar
  ActiveProjects.tsx             // Shopping/bookmarks sidebar

// Shared Components
components/shared/
  CharacterSelector.tsx          // Dropdown for char selection
  QuickActionButton.tsx          // "Build Now" etc buttons
  CategoryBadge.tsx              // 🏭 Production | 💰 Trade | ⚔️ War

// Research Components (NEW)
components/research/
  SkillPlanner.tsx               // Skills for production item
  SkillRecommendations.tsx       // AI skill suggestions
  SkillQueueViewer.tsx           // Current skill queues
  SkillComparisonTable.tsx       // Compare skills across 3 chars

// Enhanced Components
components/production/
  ProductionPlanner.tsx          // Add char selector + multi-char comparison

components/shopping/
  ShoppingWizard.tsx             // Add multi-char mode
```

#### New Hooks

```typescript
// Dashboard Data
hooks/dashboard/
  useOpportunities.ts            // Fetch aggregated opportunities
  useCharacterSummary.ts         // Fetch 3-char overview
  useWarAlerts.ts                // Fetch war room alerts
  useActiveProjects.ts           // Fetch shopping lists + bookmarks

// Research Data
hooks/research/
  useSkillsForItem.ts            // Required skills for item
  useSkillRecommendations.ts     // Skill training suggestions
  useSkillQueue.ts               // Current skill queue

// Character Management
hooks/characters/
  useCharacterPortfolio.ts       // Aggregated portfolio
  useCharacterSelector.ts        // Local storage for last used char
```

#### State Management

**TanStack React Query** (existing)
- New queries: `useOpportunities`, `useCharacterPortfolio`, `useWarAlerts`
- Cache time: 5 minutes for opportunities, 1 minute for character data
- Automatic refetching on window focus

**Character Selection State:**
```typescript
// localStorage key: "lastUsedCharacter"
// Schema: { production: 526379435, shopping: 1117367444, ... }
// Used to remember which char user prefers for each action
```

---

## Data Flow

### Dashboard Opportunities Flow

```
Market Hunter (*/5 min) ──┐
Arbitrage Calculator   ───├──→ dashboard_service.py ──→ GET /api/dashboard/opportunities
War Analyzer (*/30 min)──┘          │
                                    │
                                    └──→ Frontend: OpportunitiesFeed.tsx
                                              │
                                              ├──→ "Build Now" → CharacterSelector → ProductionPlanner
                                              └──→ "View Details" → Navigate to Analysis Section
```

### Multi-Character Action Flow

```
User clicks "Build Now" on Opportunity
    ↓
CharacterSelector appears (dropdown)
    ↓
User selects character (e.g., Artallus)
    ↓
Selection stored in localStorage: { production: 526379435 }
    ↓
Navigate to ProductionPlanner with query params:
  ?type_id=645&character_id=526379435
    ↓
ProductionPlanner pre-fills with item + character
```

### War Room Integration Flow

```
Killmail Fetcher (daily) → combat_ship_losses table
                                │
                                ↓
War Analyzer → Demand Analysis → manufacturing_opportunities
                                │
                                ├──→ GET /api/dashboard/war-alerts → Dashboard Sidebar
                                └──→ GET /api/dashboard/opportunities → Opportunities Feed (⚔️ War Demand)
```

---

## Migration Strategy

### Phase 1: Dashboard Foundation (Week 1-2)
1. Create dashboard layout components
2. Implement backend aggregation endpoints
3. Build OpportunitiesFeed with mock data
4. Build CharacterOverview with ESI data
5. Build WarRoomAlerts with existing war data

### Phase 2: Navigation & Routing (Week 2-3)
1. Refactor main navigation to 5 sections
2. Implement nested routes for sub-tabs
3. Move Bookmarks to Management
4. Update all internal links

### Phase 3: Character Selector & Actions (Week 3-4)
1. Build CharacterSelector component
2. Implement localStorage persistence
3. Wire up "Quick Action" buttons
4. Update ProductionPlanner to accept character parameter
5. Update ShoppingWizard to accept character parameter

### Phase 4: Research Features (Week 4-5)
1. Create research_service.py backend
2. Implement skills-for-item endpoint
3. Implement skill recommendations endpoint
4. Build Research UI components
5. Integrate with Production Planner

### Phase 5: Enhanced War Room Integration (Week 5-6)
1. Create Demand Dashboard (consolidate existing pages)
2. Implement dashboard alerts feed
3. Wire up "Push to Dashboard" in War Room
4. Add region watch functionality

### Phase 6: Multi-Character Enhancements (Week 6-7)
1. Implement portfolio_service.py
2. Build multi-char views in Management section
3. Add multi-char shopping lists
4. Add character comparison in Production Planner

### Phase 7: Polish & Optimization (Week 7-8)
1. UI/UX polish (animations, loading states)
2. Performance optimization (query deduplication)
3. Error handling & edge cases
4. User testing & feedback
5. Documentation update

---

## Success Metrics

### User Experience Metrics
- **Time to First Action** - From app open to "Build Now" click < 5 seconds
- **Clicks to Complete Task** - Reduced from avg 4-5 to 2-3 clicks
- **Dashboard Load Time** - All data visible < 2 seconds

### Feature Adoption Metrics
- **Dashboard Usage** - 80%+ of sessions start on Dashboard
- **Character Switching** - All 3 characters used within 24h period
- **War Room Integration** - 30%+ of opportunities come from War Demand

### Business Metrics (EVE Online)
- **Profit per Session** - Measurable increase from better opportunity discovery
- **Multi-Char Coordination** - 50%+ of shopping lists involve 2+ characters
- **Production Efficiency** - Skill recommendations followed → faster training

---

## Open Questions

### To Be Decided
1. **Opportunity Scoring Algorithm** - How to weight Industrie vs Handel vs War Demand?
2. **Character Auto-Selection** - Should system suggest "best character for this task"?
3. **Notification System** - Should we add push notifications for high-value alerts?
4. **Mobile Support** - Is responsive design needed or desktop-only?

### Future Enhancements (Not in Scope)
- Multi-user corporation support
- Fleet coordination features
- Market prediction AI/ML
- Automated trading bots (ESI write scopes)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| ESI rate limiting on dashboard load | High | Cache aggressively, stagger requests, use optimistic UI |
| Character data staleness | Medium | Implement websocket for real-time updates (future) |
| Complex state management with 3 chars | Medium | Use React Query deduplication, shared cache keys |
| Migration breaks existing users | High | Feature flags, gradual rollout, keep old routes working |

---

## Appendix

### Character IDs
- Artallus: 526379435
- Cytrex: 1117367444
- Cytricia: 110592475

### Trade Hubs (Region IDs)
- Jita: 10000002
- Amarr: 10000043
- Rens: 10000030
- Dodixie: 10000032
- Hek: 10000042

### Technology Stack
- **Backend:** FastAPI + Python 3.11+
- **Frontend:** React 19 + TypeScript 5.9 + Vite 7
- **Database:** PostgreSQL 16
- **State:** TanStack React Query 5
- **Icons:** lucide-react

---

## Document History

| Date | Author | Change |
|------|--------|--------|
| 2025-12-11 | Cytrex, Claude | Initial design based on brainstorming session |
