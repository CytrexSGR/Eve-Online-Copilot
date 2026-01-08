# EVE Online Combat Intelligence Dashboard

**Public-facing frontend for EVE Online combat intelligence and battle tracking.**

Real-time battle visualization, kill tracking, and combat analytics powered by zkillboard live stream.

---

## Quick Start

```bash
cd /home/cytrex/eve_copilot/public-frontend

# Development (with hot reload)
npm run dev -- --host 0.0.0.0

# Access: http://localhost:5173 or http://192.168.178.108:5173

# Production build
npm run build
# Output in dist/
```

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| React 19 | UI Framework |
| TypeScript | Type safety |
| Vite 7 | Build tool, dev server |
| React Router 7 | Client-side routing |
| TanStack Query v5 | Server state management |
| Axios | HTTP client |

---

## Project Structure

```
public-frontend/
├── src/
│   ├── App.tsx              # Root component, routes
│   ├── main.tsx             # Entry point
│   ├── index.css            # Global styles
│   │
│   ├── pages/               # Page components (all lazy-loaded)
│   │   ├── Home.tsx                    # Main dashboard
│   │   ├── BattleReport.tsx            # 24h battle report with ectmap
│   │   ├── BattleMap2D.tsx             # Interactive battle map
│   │   ├── BattleDetail.tsx            # Individual battle details
│   │   ├── WarProfiteering.tsx         # Market opportunities
│   │   ├── AllianceWars.tsx            # Alliance conflicts
│   │   └── TradeRoutes.tsx             # Route safety analysis
│   │
│   ├── components/          # Reusable components
│   │   ├── Layout.tsx                  # Main layout with navigation
│   │   ├── RefreshIndicator.tsx        # Auto-refresh status
│   │   ├── BattleStatsCards.tsx        # Live battle statistics
│   │   ├── LiveBattles.tsx             # Active battles feed
│   │   └── TelegramMirror.tsx          # Telegram alerts mirror
│   │
│   ├── services/            # API clients
│   │   └── api.ts                      # API functions & types
│   │
│   ├── hooks/               # Custom React hooks
│   │   ├── useReports.ts               # Reports data fetching
│   │   └── useAutoRefresh.ts           # Auto-refresh functionality
│   │
│   └── types/               # TypeScript types
│       └── reports.ts                  # API response types
│
├── public/                  # Static assets
├── index.html               # HTML template
├── vite.config.ts           # Vite configuration
├── tsconfig.json            # TypeScript configuration
└── package.json             # Dependencies
```

---

## Features

### Live Battle Tracking
- **Real-time battles**: Updated every 5 seconds from zkillboard
- **Battle intensity levels**: extreme (100+ kills), high (50+), moderate (10+), low (<10)
- **Interactive map**: Click battles to view details
- **Battle lifecycle**: Auto-cleanup after 2 hours of inactivity

### ectmap Integration
- **Full EVE universe map**: All systems, regions, and jump routes
- **Live battle overlay**: Battles rendered directly on map
- **Interactive tooltips**: Hover for battle details
- **Click navigation**: Jump to battle detail page
- **5-second refresh**: Always current battle state

### Battle Analytics
- **Ship class breakdown**: Detailed composition per battle
- **Kill timeline**: Chronological kill feed
- **ISK destroyed**: Real-time value tracking
- **System danger scores**: Route safety analysis

### Data Consistency
- **Transactional integrity**: Battles only updated if kills successfully stored
- **Automatic cleanup**: Old battles removed every 30 minutes
- **Battle-specific metrics**: All data scoped to battle timeframe

---

## Pages

| Page | Route | Purpose |
|------|-------|---------|
| Home | `/` | Combat intelligence dashboard |
| Battle Report | `/battle-report` | 24h battle report with ectmap |
| Battle Map | `/battle-map` | Interactive 2D battle map |
| Battle Detail | `/battle/:id` | Individual battle analysis |
| War Profiteering | `/war-profiteering` | Market opportunities |
| Alliance Wars | `/alliance-wars` | Alliance conflicts |
| Trade Routes | `/trade-routes` | Route safety |

**Note:** All pages are lazy-loaded using React.lazy() for code splitting.

---

## API Integration

### Base Configuration

```typescript
// src/services/api.ts
import axios from 'axios';

const API_BASE_URL = import.meta.env.PROD
  ? 'https://eve.infinimind-creations.com/api'
  : '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});
```

### Reports API

```typescript
import { reportsApi } from '../services/api';

// Get 24h battle report
const battleReport = await reportsApi.getBattleReport();

// Get war profiteering opportunities
const profiteering = await reportsApi.getWarProfiteering();

// Get alliance wars
const allianceWars = await reportsApi.getAllianceWars();

// Get trade route safety
const tradeRoutes = await reportsApi.getTradeRoutes();
```

### Battle API

```typescript
import { battleApi } from '../services/api';

// Get active battles
const battles = await battleApi.getActiveBattles(limit);

// Get recent Telegram alerts
const alerts = await battleApi.getRecentTelegramAlerts(limit);

// Get battle kills
const kills = await battleApi.getBattleKills(battleId, limit);

// Get battle ship classes
const shipClasses = await battleApi.getBattleShipClasses(battleId, 'category');

// Get system danger score
const danger = await battleApi.getSystemDanger(systemId);
```

---

## ectmap Integration

**ectmap** is a third-party EVE Online map running on port 3001, integrated via iframe.

### Architecture

```
┌─────────────────────────────────────────┐
│  public-frontend (Port 5173)            │
│  ┌───────────────────────────────────┐  │
│  │ BattleReport.tsx                  │  │
│  │   └── <iframe src="ectmap" />    │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  ectmap (Port 3001)                     │
│  ┌───────────────────────────────────┐  │
│  │ StarMap.tsx                        │  │
│  │  - Canvas-based EVE map            │  │
│  │  - Battle rendering layer          │  │
│  │  - Hover tooltips                  │  │
│  │  - Click handlers                  │  │
│  └───────────────────────────────────┘  │
│           │                              │
│           ▼                              │
│  ┌───────────────────────────────────┐  │
│  │ /api/battles                       │  │
│  │  - Fetches from backend:8000      │  │
│  │  - Returns battle data with coords │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Backend (Port 8000)                    │
│  GET /api/war/battles/active            │
└─────────────────────────────────────────┘
```

### Battle Rendering

Battles are rendered directly on ectmap's canvas:
- **Color coding**: Intensity-based (red=extreme, yellow=high, blue=moderate, green=low)
- **Size scaling**: Larger markers for bigger battles
- **Glow effects**: Animated glow for visual prominence
- **5s auto-refresh**: Live updates without page reload

### iframe Communication

When user clicks a battle on ectmap, it navigates the parent window:

```typescript
// In ectmap/app/components/StarMap.tsx
const battleUrl = `http://192.168.178.108:5173/battle/${battle.battle_id}`;
if (window.parent !== window) {
  window.parent.location.href = battleUrl;  // Navigate parent
} else {
  window.location.href = battleUrl;         // Navigate self
}
```

---

## Battle System

### Battle Detection
Battles are detected by `services/zkillboard/live_service.py`:
- **Threshold**: 5+ kills in same system within 5 minutes
- **Intensity levels**: Based on kill count
- **Telegram alerts**: Sent at milestones (10, 25, 50, 100, 250 kills)

### Battle Lifecycle
1. **Creation**: First kill exceeding threshold
2. **Active**: Continuous kill updates
3. **Ended**: 2 hours of inactivity OR manual cleanup
4. **Cleanup**: Automatic via cron job (every 30 minutes)

### Data Consistency Fix
**Critical improvement** (Jan 2026):
- Previously: Battles counted kills even if database storage failed
- **Result**: 99.5% phantom kills (113k claimed, only 4.7k real)
- **Fix**: Transactional integrity - battles only updated if kills successfully stored

```python
# services/zkillboard/live_service.py
db_stored = self.store_live_kill(kill, zkb_data, esi_killmail)

if not db_stored:
    print(f"[SKIP] Killmail not stored - skipping battle tracking")
    return

# ONLY reached if db_stored == True
battle_id = self.create_or_update_battle(kill)
```

---

## Styling & Dark Mode

**IMPORTANT: All UI components MUST use dark mode by default.**

### Color Palette

```css
/* CSS Variables (index.css) */
--bg-primary: #0d1117;         /* Deep space dark */
--bg-elevated: #161b22;        /* Cards, panels */
--bg-surface: #21262d;         /* Hover states */
--border-color: #30363d;       /* Subtle borders */
--text-primary: #e6edf3;       /* High contrast */
--text-secondary: #8b949e;     /* Muted text */
--accent-blue: #58a6ff;        /* Links, actions */
--success: #3fb950;            /* Profit, positive */
--warning: #d29922;            /* Moderate alerts */
--danger: #f85149;             /* Errors, critical */
```

### Common Patterns

```css
.card {
  background: var(--bg-elevated);
  border-radius: 8px;
  padding: 1.5rem;
  border: 1px solid var(--border-color);
}

.card-elevated {
  background: var(--bg-surface);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}
```

---

## Performance

### Code Splitting
All pages lazy-loaded with React.lazy() + Suspense boundaries.

### Auto-Refresh
- **Home page**: 60 seconds
- **Battle map**: 5 seconds (ectmap internal)
- **Battle details**: Manual refresh only

### React Query Configuration
```typescript
// src/hooks/useReports.ts
staleTime: 60000,        // 1 minute
gcTime: 300000,          // 5 minutes
refetchOnWindowFocus: false,
refetchOnReconnect: true,
```

---

## Development

### Adding a New Page

1. **Create page component**:
```typescript
// src/pages/NewPage.tsx
export function NewPage() {
  return <div>Content</div>;
}
```

2. **Add route in App.tsx**:
```typescript
const NewPage = lazy(() => import('./pages/NewPage').then(m => ({ default: m.NewPage })));

<Route path="/new-page" element={<NewPage />} />
```

3. **Add navigation link in Layout.tsx**:
```typescript
<Link to="/new-page">New Page</Link>
```

### Adding a Battle API Function

1. **Add to `src/services/api.ts`**:
```typescript
export const battleApi = {
  getNewData: async (param: number) => {
    const { data } = await api.get(`/war/new-endpoint/${param}`);
    return data;
  }
};
```

2. **Use in component**:
```typescript
const { data } = useQuery({
  queryKey: ['newData', param],
  queryFn: () => battleApi.getNewData(param)
});
```

---

## Troubleshooting

### Frontend won't start
```bash
lsof -i :5173
cd public-frontend && npm install
npm run dev -- --host 0.0.0.0
```

### ectmap iframe not loading
1. Check ectmap is running on port 3001
2. Update iframe src URL if hostname changed
3. Check browser console for CORS errors

### Battle data not updating
1. Check backend zkillboard live stream is running
2. Check battle cleanup job hasn't removed old battles
3. Verify ectmap `/api/battles` endpoint returns data

### API calls fail
1. Check backend is running on port 8000
2. Check Vite proxy configuration in `vite.config.ts`
3. Check browser DevTools Network tab for errors

---

## Dependencies

```json
{
  "dependencies": {
    "@tanstack/react-query": "^5.90.16",
    "axios": "^1.13.2",
    "react": "^19.2.0",
    "react-dom": "^19.2.0",
    "react-router-dom": "^7.11.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^5.1.1",
    "typescript": "~5.9.3",
    "vite": "^7.2.4"
  }
}
```

**Removed dependencies** (Jan 2026):
- `eve-map-3d`, `@react-three/drei`, `@react-three/fiber`, `three`
- Old 3D map components replaced with ectmap iframe integration

---

## Related Services

| Service | Port | Purpose |
|---------|------|---------|
| public-frontend | 5173 | Combat intelligence dashboard |
| ectmap | 3001 | EVE Online universe map |
| Backend API | 8000 | Battle data, reports, zkillboard stream |
| PostgreSQL | 5432 | Battle data storage |

---

**Last Updated:** 2026-01-08
