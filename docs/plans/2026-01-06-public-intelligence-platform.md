# EVE Intelligence Platform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a public-facing web platform (eve.infinimind-creations.com) providing EVE Online combat intelligence reports with Google Ads monetization.

**Architecture:** Separate FastAPI app on port 8001 serving cached reports from Redis, React frontend with auto-refresh, Nginx reverse proxy with HTTPS, rate limiting and security headers.

**Tech Stack:** FastAPI, React, TypeScript, Vite, Redis, Nginx, Let's Encrypt, SlowAPI, Google AdSense

---

## Phase 1: Backend API Setup

### Task 1: Create Public API Project Structure

**Files:**
- Create: `public_api/__init__.py`
- Create: `public_api/main.py`
- Create: `public_api/routers/__init__.py`
- Create: `public_api/middleware/__init__.py`
- Create: `public_api/requirements.txt`

**Step 1: Create directory structure**

```bash
mkdir -p public_api/routers public_api/middleware
touch public_api/__init__.py public_api/routers/__init__.py public_api/middleware/__init__.py
```

**Step 2: Create requirements.txt**

File: `public_api/requirements.txt`

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
slowapi==0.1.9
redis==5.0.1
python-dotenv==1.0.0
```

**Step 3: Create minimal FastAPI app**

File: `public_api/main.py`

```python
"""
EVE Intelligence Public API
Serves cached combat intelligence reports to the public
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="EVE Intelligence API",
    description="Public combat intelligence reports for EVE Online",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS - Only allow our public domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://eve.infinimind-creations.com",
        "http://localhost:5173",  # Development
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": "EVE Intelligence API",
        "version": "1.0.0",
        "endpoints": [
            "/api/reports/battle-24h",
            "/api/reports/war-profiteering",
            "/api/reports/alliance-wars",
            "/api/reports/trade-routes",
            "/api/health"
        ]
    }

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "eve-intelligence-api"}
```

**Step 4: Test server starts**

Run:
```bash
cd /home/cytrex/eve_copilot
python3 -m venv venv-public-api
source venv-public-api/bin/activate
pip install -r public_api/requirements.txt
uvicorn public_api.main:app --host 0.0.0.0 --port 8001 --reload
```

Expected: Server starts on http://0.0.0.0:8001
Test: `curl http://localhost:8001/api/health`
Expected output: `{"status":"healthy","service":"eve-intelligence-api"}`

**Step 5: Stop server and commit**

```bash
# Ctrl+C to stop
git add public_api/
git commit -m "feat: initialize public API project structure

- FastAPI app on port 8001
- CORS for public domain
- Health endpoint
- Basic requirements"
```

---

### Task 2: Add Security Middleware

**Files:**
- Create: `public_api/middleware/security.py`
- Modify: `public_api/main.py`

**Step 1: Create security headers middleware**

File: `public_api/middleware/security.py`

```python
"""
Security middleware for public API
Adds security headers to all responses
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # HSTS - Force HTTPS for 1 year
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS Protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://pagead2.googlesyndication.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self';"
        )

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        return response
```

**Step 2: Add middleware to app**

File: `public_api/main.py` - Add after CORS middleware:

```python
from public_api.middleware.security import SecurityHeadersMiddleware

# ... after CORSMiddleware ...

# Security Headers
app.add_middleware(SecurityHeadersMiddleware)
```

**Step 3: Test security headers**

Run:
```bash
uvicorn public_api.main:app --host 0.0.0.0 --port 8001 --reload &
sleep 2
curl -I http://localhost:8001/api/health
```

Expected: Headers should include:
- `Strict-Transport-Security`
- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `Content-Security-Policy`

**Step 4: Stop server and commit**

```bash
pkill -f "uvicorn public_api"
git add public_api/middleware/security.py public_api/main.py
git commit -m "feat: add security headers middleware

- HSTS for HTTPS enforcement
- XSS protection headers
- Content Security Policy
- Clickjacking protection"
```

---

### Task 3: Add Rate Limiting Middleware

**Files:**
- Create: `public_api/middleware/rate_limit.py`
- Modify: `public_api/main.py`

**Step 1: Create rate limiting middleware**

File: `public_api/middleware/rate_limit.py`

```python
"""
Rate limiting middleware
100 requests per minute per IP address
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# Initialize limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri="memory://",  # In-memory storage
)


# Custom rate limit error response
async def rate_limit_handler(request, exc):
    return {
        "error": "Rate limit exceeded",
        "detail": "Maximum 100 requests per minute allowed",
        "retry_after": exc.detail
    }
```

**Step 2: Integrate rate limiter into app**

File: `public_api/main.py` - Add imports and setup:

```python
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from public_api.middleware.rate_limit import limiter, rate_limit_handler

# ... after SecurityHeadersMiddleware ...

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)
```

**Step 3: Test rate limiting**

Run:
```bash
uvicorn public_api.main:app --host 0.0.0.0 --port 8001 --reload &
sleep 2

# Test 5 rapid requests (should all succeed)
for i in {1..5}; do curl http://localhost:8001/api/health; echo ""; done

# Test 110 requests (last 10 should be rate limited)
for i in {1..110}; do
    curl -s http://localhost:8001/api/health -w "Status: %{http_code}\n" -o /dev/null
done | grep -c "429"
```

Expected: Should see some 429 (Too Many Requests) responses

**Step 4: Stop server and commit**

```bash
pkill -f "uvicorn public_api"
git add public_api/middleware/rate_limit.py public_api/main.py
git commit -m "feat: add rate limiting middleware

- 100 requests per minute per IP
- SlowAPI integration
- Custom error response"
```

---

### Task 4: Create Reports Router

**Files:**
- Create: `public_api/routers/reports.py`
- Modify: `public_api/main.py`

**Step 1: Create reports router with Redis integration**

File: `public_api/routers/reports.py`

```python
"""
Reports API Router
Serves cached combat intelligence reports from Redis
"""

from fastapi import APIRouter, HTTPException
from typing import Dict
import redis
from services.zkillboard import zkill_live_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/battle-24h")
async def get_battle_report() -> Dict:
    """
    24-Hour Battle Report by Region

    Returns comprehensive combat statistics for the last 24 hours,
    organized by region with top systems, ships, and destroyed items.

    Cache: 10 minutes
    """
    try:
        report = zkill_live_service.get_24h_battle_report()
        return report
    except redis.RedisError as e:
        raise HTTPException(
            status_code=503,
            detail="Redis connection error. Reports temporarily unavailable."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate battle report"
        )


@router.get("/war-profiteering")
async def get_war_profiteering() -> Dict:
    """
    War Profiteering Daily Digest

    Identifies market opportunities based on destroyed items in combat.
    Shows items with highest market value destroyed in last 24 hours.

    Cache: 1 hour (refreshed daily at 06:00 UTC)
    """
    try:
        report = zkill_live_service.get_war_profiteering_report(limit=20)
        return report
    except redis.RedisError as e:
        raise HTTPException(
            status_code=503,
            detail="Redis connection error. Reports temporarily unavailable."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate war profiteering report"
        )


@router.get("/alliance-wars")
async def get_alliance_wars() -> Dict:
    """
    Alliance War Tracker

    Tracks active alliance conflicts with kill/death ratios and ISK efficiency.
    Shows top 5 most active alliance wars in last 24 hours.

    Cache: 30 minutes
    """
    try:
        report = await zkill_live_service.get_alliance_war_tracker(limit=5)
        return report
    except redis.RedisError as e:
        raise HTTPException(
            status_code=503,
            detail="Redis connection error. Reports temporarily unavailable."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate alliance wars report"
        )


@router.get("/trade-routes")
async def get_trade_routes() -> Dict:
    """
    Trade Route Danger Map

    Analyzes danger levels along major HighSec trade routes between hubs.
    Shows danger scores per system based on recent kills and gate camps.

    Cache: 1 hour (refreshed daily at 08:00 UTC)
    """
    try:
        report = zkill_live_service.get_trade_route_danger_map()
        return report
    except redis.RedisError as e:
        raise HTTPException(
            status_code=503,
            detail="Redis connection error. Reports temporarily unavailable."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate trade routes report"
        )
```

**Step 2: Register router in main app**

File: `public_api/main.py` - Add after middleware setup:

```python
from public_api.routers import reports

# Register routers
app.include_router(reports.router)
```

**Step 3: Test all report endpoints**

Run:
```bash
uvicorn public_api.main:app --host 0.0.0.0 --port 8001 --reload &
sleep 2

# Test each endpoint
curl http://localhost:8001/api/reports/battle-24h | python3 -m json.tool | head -20
curl http://localhost:8001/api/reports/war-profiteering | python3 -m json.tool | head -20
curl http://localhost:8001/api/reports/alliance-wars | python3 -m json.tool | head -20
curl http://localhost:8001/api/reports/trade-routes | python3 -m json.tool | head -20

# Test API docs
curl http://localhost:8001/api/docs
```

Expected: All endpoints return JSON data with proper structure

**Step 4: Stop server and commit**

```bash
pkill -f "uvicorn public_api"
git add public_api/routers/reports.py public_api/main.py
git commit -m "feat: add reports API endpoints

- Battle report (24h regional statistics)
- War profiteering (market opportunities)
- Alliance wars (conflict tracking)
- Trade routes (danger analysis)
- Error handling for Redis failures"
```

---

## Phase 2: Frontend Project Setup

### Task 5: Initialize React + Vite Project

**Files:**
- Create: `public-frontend/` directory with Vite project

**Step 1: Create Vite React TypeScript project**

```bash
cd /home/cytrex/eve_copilot
npm create vite@latest public-frontend -- --template react-ts
cd public-frontend
```

**Step 2: Install dependencies**

```bash
npm install
npm install axios react-router-dom
npm install -D @types/react-router-dom
```

**Step 3: Update vite.config.ts for production**

File: `public-frontend/vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
        }
      }
    }
  }
})
```

**Step 4: Test dev server starts**

Run:
```bash
npm run dev
```

Expected: Dev server starts on http://localhost:5173

**Step 5: Stop server and commit**

```bash
# Ctrl+C to stop
cd /home/cytrex/eve_copilot
git add public-frontend/
git commit -m "feat: initialize React frontend with Vite

- TypeScript template
- React Router for navigation
- Axios for API calls
- Dev proxy to backend on :8001"
```

---

### Task 6: Create API Client Service

**Files:**
- Create: `public-frontend/src/services/api.ts`
- Create: `public-frontend/src/types/reports.ts`

**Step 1: Create TypeScript types for reports**

File: `public-frontend/src/types/reports.ts`

```typescript
export interface BattleReport {
  period: string;
  global: {
    total_kills: number;
    total_isk_destroyed: number;
    most_active_region: string;
    most_expensive_region: string;
  };
  regions: Array<{
    region_id: number;
    region_name: string;
    kills: number;
    total_isk_destroyed: number;
    avg_kill_value: number;
    top_systems: Array<{
      system_id: number;
      system_name: string;
      kills: number;
    }>;
    top_ships: Array<{
      ship_type_id: number;
      ship_name: string;
      losses: number;
    }>;
    top_destroyed_items: Array<{
      item_type_id: number;
      item_name: string;
      quantity_destroyed: number;
    }>;
  }>;
}

export interface WarProfiteeringReport {
  items: Array<{
    item_type_id: number;
    item_name: string;
    group_id: number;
    quantity_destroyed: number;
    market_price: number;
    opportunity_value: number;
  }>;
  total_items: number;
  total_opportunity_value: number;
  period: string;
}

export interface AllianceWarsReport {
  wars: Array<{
    alliance_a_id: number;
    alliance_a_name: string;
    alliance_b_id: number;
    alliance_b_name: string;
    total_kills: number;
    kills_by_a: number;
    kills_by_b: number;
    isk_destroyed_by_a: number;
    isk_destroyed_by_b: number;
    kill_ratio_a: number;
    isk_efficiency_a: number;
    active_systems: number;
    winner: string;
  }>;
  total_wars: number;
  period: string;
}

export interface TradeRoutesReport {
  timestamp: string;
  routes: Array<{
    from_hub: string;
    to_hub: string;
    from_system_id: number;
    to_system_id: number;
    total_jumps: number;
    danger_level: string;
    avg_danger_score: number;
    total_danger_score: number;
    max_danger_system: {
      system_id: number;
      system_name: string;
      danger_score: number;
    } | null;
    systems: Array<{
      system_id: number;
      system_name: string;
      security: number;
      danger_score: number;
      kills_24h: number;
      isk_destroyed_24h: number;
      gate_camp_detected: boolean;
    }>;
  }>;
  total_routes: number;
  period: string;
  danger_scale: Record<string, string>;
}
```

**Step 2: Create API client with auto-refresh**

File: `public-frontend/src/services/api.ts`

```typescript
import axios from 'axios';
import type {
  BattleReport,
  WarProfiteeringReport,
  AllianceWarsReport,
  TradeRoutesReport
} from '../types/reports';

const API_BASE_URL = import.meta.env.PROD
  ? 'https://eve.infinimind-creations.com/api'
  : '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API methods
export const reportsApi = {
  getBattleReport: async (): Promise<BattleReport> => {
    const { data } = await api.get('/reports/battle-24h');
    return data;
  },

  getWarProfiteering: async (): Promise<WarProfiteeringReport> => {
    const { data } = await api.get('/reports/war-profiteering');
    return data;
  },

  getAllianceWars: async (): Promise<AllianceWarsReport> => {
    const { data } = await api.get('/reports/alliance-wars');
    return data;
  },

  getTradeRoutes: async (): Promise<TradeRoutesReport> => {
    const { data } = await api.get('/reports/trade-routes');
    return data;
  },

  getHealth: async () => {
    const { data } = await api.get('/health');
    return data;
  }
};

export default api;
```

**Step 3: Commit**

```bash
cd /home/cytrex/eve_copilot
git add public-frontend/src/services/api.ts public-frontend/src/types/reports.ts
git commit -m "feat: add API client and TypeScript types

- Axios client with base URL
- TypeScript interfaces for all reports
- Environment-aware URL (dev/prod)"
```

---

### Task 7: Create Core UI Components

**Files:**
- Create: `public-frontend/src/components/Layout.tsx`
- Create: `public-frontend/src/components/RefreshIndicator.tsx`
- Create: `public-frontend/src/App.css`

**Step 1: Create dark mode global styles**

File: `public-frontend/src/App.css`

```css
:root {
  /* Dark Mode EVE Online Theme */
  --bg-primary: #0d1117;
  --bg-secondary: #161b22;
  --bg-elevated: #21262d;
  --border-color: #30363d;

  --text-primary: #e6edf3;
  --text-secondary: #8b949e;
  --text-tertiary: #6e7681;

  --accent-blue: #58a6ff;
  --accent-purple: #bc8cff;
  --success: #3fb950;
  --warning: #d29922;
  --danger: #f85149;

  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  line-height: 1.6;
  font-weight: 400;

  color-scheme: dark;
  color: var(--text-primary);
  background-color: var(--bg-primary);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  min-height: 100vh;
  background: var(--bg-primary);
}

#root {
  min-height: 100vh;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1rem;
}

.card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.card-elevated {
  background: var(--bg-elevated);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

h1, h2, h3, h4, h5, h6 {
  color: var(--text-primary);
  font-weight: 700;
  line-height: 1.3;
  margin-bottom: 1rem;
}

a {
  color: var(--accent-blue);
  text-decoration: none;
  transition: color 0.2s;
}

a:hover {
  color: var(--accent-purple);
}

.text-secondary {
  color: var(--text-secondary);
}

.text-success {
  color: var(--success);
}

.text-warning {
  color: var(--warning);
}

.text-danger {
  color: var(--danger);
}

/* Loading skeleton */
.skeleton {
  background: linear-gradient(
    90deg,
    var(--bg-secondary) 25%,
    var(--bg-elevated) 50%,
    var(--bg-secondary) 75%
  );
  background-size: 200% 100%;
  animation: loading 1.5s ease-in-out infinite;
  border-radius: 4px;
}

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Responsive */
@media (max-width: 768px) {
  .card {
    padding: 1rem;
  }
}
```

**Step 2: Create Layout component**

File: `public-frontend/src/components/Layout.tsx`

```typescript
import React from 'react';
import { Link } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header style={{
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-color)',
        padding: '1rem 0'
      }}>
        <div className="container">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <Link to="/" style={{ textDecoration: 'none' }}>
                <h1 style={{
                  fontSize: '1.5rem',
                  color: 'var(--accent-blue)',
                  margin: 0
                }}>
                  ⚔️ EVE Intelligence
                </h1>
              </Link>
              <p style={{
                color: 'var(--text-secondary)',
                fontSize: '0.875rem',
                margin: 0
              }}>
                Real-time Combat Intelligence for New Eden
              </p>
            </div>

            <nav style={{ display: 'flex', gap: '1.5rem' }}>
              <Link to="/battle-report">Battle Report</Link>
              <Link to="/war-profiteering">Profiteering</Link>
              <Link to="/alliance-wars">Alliance Wars</Link>
              <Link to="/trade-routes">Trade Routes</Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ flex: 1, padding: '2rem 0' }}>
        <div className="container">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer style={{
        background: 'var(--bg-secondary)',
        borderTop: '1px solid var(--border-color)',
        padding: '2rem 0',
        marginTop: '3rem'
      }}>
        <div className="container">
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '2rem'
          }}>
            <div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                © 2026 EVE Intelligence | Data from zKillboard & ESI
              </p>
              <p style={{ color: 'var(--text-tertiary)', fontSize: '0.75rem', marginTop: '0.5rem' }}>
                EVE Online and the EVE logo are trademarks of CCP hf.
              </p>
            </div>
            <div>
              <a href="/privacy" style={{ marginRight: '1rem' }}>Privacy Policy</a>
              <a href="/cookies">Cookie Policy</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
```

**Step 3: Create RefreshIndicator component**

File: `public-frontend/src/components/RefreshIndicator.tsx`

```typescript
import { useEffect, useState } from 'react';

interface RefreshIndicatorProps {
  lastUpdated: Date;
  autoRefreshSeconds?: number;
}

export function RefreshIndicator({
  lastUpdated,
  autoRefreshSeconds = 60
}: RefreshIndicatorProps) {
  const [timeAgo, setTimeAgo] = useState('');

  useEffect(() => {
    const updateTimeAgo = () => {
      const seconds = Math.floor((Date.now() - lastUpdated.getTime()) / 1000);

      if (seconds < 60) {
        setTimeAgo(`${seconds}s ago`);
      } else if (seconds < 3600) {
        setTimeAgo(`${Math.floor(seconds / 60)}m ago`);
      } else {
        setTimeAgo(`${Math.floor(seconds / 3600)}h ago`);
      }
    };

    updateTimeAgo();
    const interval = setInterval(updateTimeAgo, 1000);
    return () => clearInterval(interval);
  }, [lastUpdated]);

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      fontSize: '0.875rem',
      color: 'var(--text-secondary)'
    }}>
      <span>🔄</span>
      <span>Updated {timeAgo}</span>
      <span style={{ color: 'var(--text-tertiary)' }}>
        • Auto-refresh {autoRefreshSeconds}s
      </span>
    </div>
  );
}
```

**Step 4: Commit**

```bash
git add public-frontend/src/components/ public-frontend/src/App.css
git commit -m "feat: add core UI components

- Layout with header/footer/nav
- Dark mode EVE theme styles
- RefreshIndicator component
- Responsive design utilities"
```

---

### Task 8: Create Home Dashboard Page

**Files:**
- Create: `public-frontend/src/pages/Home.tsx`
- Create: `public-frontend/src/hooks/useAutoRefresh.ts`

**Step 1: Create auto-refresh hook**

File: `public-frontend/src/hooks/useAutoRefresh.ts`

```typescript
import { useEffect, useRef } from 'react';

export function useAutoRefresh(
  callback: () => void | Promise<void>,
  intervalSeconds: number = 60
) {
  const savedCallback = useRef(callback);

  // Update ref when callback changes
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  // Set up interval
  useEffect(() => {
    if (intervalSeconds <= 0) return;

    const tick = () => {
      savedCallback.current();
    };

    const id = setInterval(tick, intervalSeconds * 1000);
    return () => clearInterval(id);
  }, [intervalSeconds]);
}
```

**Step 2: Create Home dashboard page**

File: `public-frontend/src/pages/Home.tsx`

```typescript
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { reportsApi } from '../services/api';
import { RefreshIndicator } from '../components/RefreshIndicator';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import type {
  BattleReport,
  WarProfiteeringReport,
  AllianceWarsReport,
  TradeRoutesReport
} from '../types/reports';

export function Home() {
  const [battleReport, setBattleReport] = useState<BattleReport | null>(null);
  const [profiteering, setProfiteering] = useState<WarProfiteeringReport | null>(null);
  const [allianceWars, setAllianceWars] = useState<AllianceWarsReport | null>(null);
  const [tradeRoutes, setTradeRoutes] = useState<TradeRoutesReport | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const fetchAllReports = async () => {
    try {
      setError(null);
      const [battle, profit, wars, routes] = await Promise.all([
        reportsApi.getBattleReport(),
        reportsApi.getWarProfiteering(),
        reportsApi.getAllianceWars(),
        reportsApi.getTradeRoutes(),
      ]);

      setBattleReport(battle);
      setProfiteering(profit);
      setAllianceWars(wars);
      setTradeRoutes(routes);
      setLastUpdated(new Date());
      setLoading(false);
    } catch (err) {
      setError('Failed to load reports. Please try again.');
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchAllReports();
  }, []);

  // Auto-refresh every 60 seconds
  useAutoRefresh(fetchAllReports, 60);

  if (loading) {
    return (
      <div>
        <div className="skeleton" style={{ height: '200px', marginBottom: '1rem' }} />
        <div className="skeleton" style={{ height: '200px', marginBottom: '1rem' }} />
        <div className="skeleton" style={{ height: '200px', marginBottom: '1rem' }} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{
        background: 'var(--danger)',
        color: 'white',
        textAlign: 'center',
        padding: '2rem'
      }}>
        <h2>❌ {error}</h2>
        <button
          onClick={fetchAllReports}
          style={{
            marginTop: '1rem',
            padding: '0.5rem 1rem',
            background: 'white',
            color: 'var(--danger)',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontWeight: 600
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '2rem'
      }}>
        <div>
          <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
            Combat Intelligence Dashboard
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            Real-time intelligence from across New Eden
          </p>
        </div>
        <RefreshIndicator lastUpdated={lastUpdated} autoRefreshSeconds={60} />
      </div>

      {/* Battle Report Summary */}
      <div className="card card-elevated">
        <h2>⚔️ 24-Hour Battle Report</h2>
        {battleReport && (
          <>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '1.5rem',
              margin: '1.5rem 0'
            }}>
              <div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                  Total Kills
                </p>
                <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
                  {battleReport.global.total_kills.toLocaleString()}
                </p>
              </div>
              <div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                  ISK Destroyed
                </p>
                <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--danger)' }}>
                  {(battleReport.global.total_isk_destroyed / 1_000_000_000).toFixed(1)}B
                </p>
              </div>
              <div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                  Hottest Region
                </p>
                <p style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--warning)' }}>
                  {battleReport.global.most_active_region}
                </p>
              </div>
            </div>
            <Link
              to="/battle-report"
              style={{
                color: 'var(--accent-blue)',
                fontWeight: 600
              }}
            >
              View Full Report →
            </Link>
          </>
        )}
      </div>

      {/* War Profiteering Summary */}
      <div className="card">
        <h2>💰 War Profiteering Opportunities</h2>
        {profiteering && profiteering.items.length > 0 && (
          <>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Top {profiteering.items.slice(0, 5).length} destroyed items by market value
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {profiteering.items.slice(0, 5).map((item, idx) => (
                <div
                  key={item.item_type_id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '0.75rem',
                    background: 'var(--bg-elevated)',
                    borderRadius: '4px'
                  }}
                >
                  <span style={{ fontWeight: 600 }}>
                    {idx + 1}. {item.item_name}
                  </span>
                  <span style={{ color: 'var(--success)' }}>
                    {(item.opportunity_value / 1_000_000_000).toFixed(2)}B ISK
                  </span>
                </div>
              ))}
            </div>
            <Link
              to="/war-profiteering"
              style={{
                color: 'var(--accent-blue)',
                fontWeight: 600,
                display: 'block',
                marginTop: '1rem'
              }}
            >
              View All Opportunities →
            </Link>
          </>
        )}
      </div>

      {/* Alliance Wars Summary */}
      <div className="card">
        <h2>🛡️ Alliance Wars</h2>
        {allianceWars && allianceWars.wars.length > 0 && (
          <>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Top {allianceWars.wars.slice(0, 3).length} active conflicts
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {allianceWars.wars.slice(0, 3).map((war) => (
                <div
                  key={`${war.alliance_a_id}-${war.alliance_b_id}`}
                  style={{
                    padding: '1rem',
                    background: 'var(--bg-elevated)',
                    borderRadius: '4px',
                    borderLeft: `4px solid ${
                      war.winner === 'a' ? 'var(--success)' :
                      war.winner === 'b' ? 'var(--danger)' :
                      'var(--warning)'
                    }`
                  }}
                >
                  <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
                    {war.alliance_a_name} vs {war.alliance_b_name}
                  </div>
                  <div style={{
                    display: 'flex',
                    gap: '1.5rem',
                    fontSize: '0.875rem',
                    color: 'var(--text-secondary)'
                  }}>
                    <span>Kills: {war.total_kills}</span>
                    <span>Ratio: {war.kill_ratio_a.toFixed(2)}</span>
                    <span>Efficiency: {(war.isk_efficiency_a * 100).toFixed(1)}%</span>
                  </div>
                </div>
              ))}
            </div>
            <Link
              to="/alliance-wars"
              style={{
                color: 'var(--accent-blue)',
                fontWeight: 600,
                display: 'block',
                marginTop: '1rem'
              }}
            >
              View All Wars →
            </Link>
          </>
        )}
      </div>

      {/* Trade Routes Summary */}
      <div className="card">
        <h2>🛣️ Trade Route Safety</h2>
        {tradeRoutes && tradeRoutes.routes.length > 0 && (
          <>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Route danger levels (last 24h)
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {tradeRoutes.routes.slice(0, 5).map((route) => (
                <div
                  key={`${route.from_hub}-${route.to_hub}`}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '0.75rem',
                    background: 'var(--bg-elevated)',
                    borderRadius: '4px'
                  }}
                >
                  <span>
                    {route.from_hub} → {route.to_hub}
                  </span>
                  <span style={{
                    fontWeight: 600,
                    color:
                      route.danger_level === 'SAFE' ? 'var(--success)' :
                      route.danger_level === 'LOW' ? 'var(--accent-blue)' :
                      route.danger_level === 'MODERATE' ? 'var(--warning)' :
                      'var(--danger)'
                  }}>
                    {route.danger_level}
                  </span>
                </div>
              ))}
            </div>
            <Link
              to="/trade-routes"
              style={{
                color: 'var(--accent-blue)',
                fontWeight: 600,
                display: 'block',
                marginTop: '1rem'
              }}
            >
              View Route Details →
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add public-frontend/src/pages/Home.tsx public-frontend/src/hooks/useAutoRefresh.ts
git commit -m "feat: add Home dashboard page

- Display all 4 reports summary
- Auto-refresh every 60 seconds
- Loading and error states
- Links to detail pages"
```

---

## Task 9: Update App Router and Test

**Files:**
- Modify: `public-frontend/src/App.tsx`
- Modify: `public-frontend/src/main.tsx`

**Step 1: Set up React Router**

File: `public-frontend/src/App.tsx`

```typescript
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Home } from './pages/Home';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/battle-report" element={<div>Battle Report Detail (Coming Soon)</div>} />
          <Route path="/war-profiteering" element={<div>War Profiteering Detail (Coming Soon)</div>} />
          <Route path="/alliance-wars" element={<div>Alliance Wars Detail (Coming Soon)</div>} />
          <Route path="/trade-routes" element={<div>Trade Routes Detail (Coming Soon)</div>} />
          <Route path="/privacy" element={<div>Privacy Policy (Coming Soon)</div>} />
          <Route path="/cookies" element={<div>Cookie Policy (Coming Soon)</div>} />
          <Route path="*" element={<div>404 - Not Found</div>} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
```

**Step 2: Update main.tsx**

File: `public-frontend/src/main.tsx`

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

**Step 3: Test frontend with backend running**

```bash
# Terminal 1: Start backend
cd /home/cytrex/eve_copilot
uvicorn public_api.main:app --host 0.0.0.0 --port 8001 --reload &

# Terminal 2: Start frontend
cd /home/cytrex/eve_copilot/public-frontend
npm run dev
```

Expected:
- Frontend at http://localhost:5173
- Should see dashboard with all 4 report summaries
- Data should auto-refresh every 60s

**Step 4: Stop servers and commit**

```bash
pkill -f "uvicorn public_api"
# Ctrl+C in frontend terminal

git add public-frontend/src/App.tsx public-frontend/src/main.tsx
git commit -m "feat: add routing and test dashboard

- React Router setup
- Home page with all reports
- Placeholder detail pages
- Navigation working"
```

---

## Phase 3: Deployment Configuration

### Task 10: Create Nginx Configuration

**Files:**
- Create: `/tmp/eve-intelligence.nginx.conf` (will be moved by user)

**Step 1: Create Nginx config file**

File: `/tmp/eve-intelligence.nginx.conf`

```nginx
# Rate limiting zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name eve.infinimind-creations.com;

    # SSL Certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/eve.infinimind-creations.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/eve.infinimind-creations.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Static Frontend
    location / {
        root /home/cytrex/eve_copilot/public-frontend/dist;
        try_files $uri $uri/ /index.html;

        # Caching for static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # No cache for index.html
        location = /index.html {
            expires -1;
            add_header Cache-Control "no-cache, no-store, must-revalidate";
        }

        # Compression
        gzip on;
        gzip_vary on;
        gzip_min_length 1000;
        gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    }

    # API Proxy
    location /api/ {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Rate Limiting
        limit_req zone=api_limit burst=20 nodelay;
        limit_req_status 429;

        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;

        # CORS headers (already in app, but backup)
        add_header Access-Control-Allow-Origin "https://eve.infinimind-creations.com" always;
    }

    # Health Check (no rate limit)
    location = /api/health {
        proxy_pass http://localhost:8001;
        access_log off;
    }

    # Access Logs
    access_log /var/log/nginx/eve-intelligence-access.log;
    error_log /var/log/nginx/eve-intelligence-error.log warn;
}

# HTTP → HTTPS Redirect
server {
    listen 80;
    server_name eve.infinimind-creations.com;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}
```

**Step 2: Create installation instructions**

File: `public_api/DEPLOYMENT.md`

```markdown
# EVE Intelligence Platform - Deployment Guide

## Prerequisites

- Ubuntu/Debian server with sudo access
- Domain: eve.infinimind-creations.com pointing to server IP
- Nginx installed
- Certbot installed

## Step 1: Install SSL Certificate

```bash
# Install certbot if not present
sudo apt update
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot certonly --nginx -d eve.infinimind-creations.com

# Certificate will be at:
# /etc/letsencrypt/live/eve.infinimind-creations.com/fullchain.pem
# /etc/letsencrypt/live/eve.infinimind-creations.com/privkey.pem
```

## Step 2: Install Nginx Configuration

```bash
# Copy config
sudo cp /tmp/eve-intelligence.nginx.conf /etc/nginx/sites-available/eve-intelligence

# Enable site
sudo ln -s /etc/nginx/sites-available/eve-intelligence /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## Step 3: Build Frontend

```bash
cd /home/cytrex/eve_copilot/public-frontend
npm run build

# Output will be in: /home/cytrex/eve_copilot/public-frontend/dist
```

## Step 4: Create Systemd Service

```bash
sudo nano /etc/systemd/system/eve-intelligence-api.service
```

Paste content from systemd service file (see below).

## Step 5: Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable eve-intelligence-api
sudo systemctl start eve-intelligence-api
sudo systemctl status eve-intelligence-api
```

## Step 6: Verify Deployment

```bash
# Check API
curl https://eve.infinimind-creations.com/api/health

# Check frontend
curl -I https://eve.infinimind-creations.com

# Check logs
sudo journalctl -u eve-intelligence-api -f
sudo tail -f /var/log/nginx/eve-intelligence-access.log
```

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u eve-intelligence-api -n 50
```

### 502 Bad Gateway
Check if API is running:
```bash
sudo systemctl status eve-intelligence-api
curl http://localhost:8001/api/health
```

### 404 Not Found
Check Nginx config and frontend build:
```bash
ls -la /home/cytrex/eve_copilot/public-frontend/dist
sudo nginx -t
```
```

**Step 3: Create systemd service file**

File: `/tmp/eve-intelligence-api.service`

```ini
[Unit]
Description=EVE Intelligence Public API
Documentation=https://github.com/CytrexSGR/Eve-Online-Copilot
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=cytrex
Group=cytrex
WorkingDirectory=/home/cytrex/eve_copilot
Environment="PATH=/home/cytrex/.local/bin:/usr/local/bin:/usr/bin:/bin"

ExecStart=/home/cytrex/.local/bin/uvicorn public_api.main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --workers 2 \
    --log-level info \
    --access-log

StandardOutput=journal
StandardError=journal
SyslogIdentifier=eve-intelligence-api

Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/var/log/eve-intelligence

[Install]
WantedBy=multi-user.target
```

**Step 4: Commit**

```bash
git add /tmp/eve-intelligence.nginx.conf /tmp/eve-intelligence-api.service public_api/DEPLOYMENT.md
git commit -m "feat: add deployment configuration

- Nginx config with SSL, rate limiting, gzip
- Systemd service file
- Deployment guide with instructions
- Ready for production deployment"
```

---

## Phase 4: Final Steps

### Task 11: Build and Test Production

**Step 1: Build frontend for production**

```bash
cd /home/cytrex/eve_copilot/public-frontend
npm run build

# Verify build
ls -lah dist/
```

Expected: `dist/` directory with index.html, assets/, etc.

**Step 2: Test backend production mode**

```bash
cd /home/cytrex/eve_copilot

# Install dependencies if needed
pip install -r public_api/requirements.txt

# Start in production mode
uvicorn public_api.main:app --host 0.0.0.0 --port 8001 --workers 2 &

# Test endpoints
curl http://localhost:8001/api/health
curl http://localhost:8001/api/reports/battle-24h | python3 -m json.tool | head -30

# Stop
pkill -f "uvicorn public_api"
```

**Step 3: Commit final build**

```bash
git add public-frontend/dist/
git commit -m "build: production build of frontend

- Optimized bundle with code splitting
- Minified JS and CSS
- Ready for nginx deployment"
```

**Step 4: Push to GitHub**

```bash
git push origin main
```

---

## Deployment Checklist

### Manual Steps (require sudo access)

**SSL Certificate:**
```bash
sudo certbot certonly --nginx -d eve.infinimind-creations.com
```

**Nginx Setup:**
```bash
sudo cp /tmp/eve-intelligence.nginx.conf /etc/nginx/sites-available/eve-intelligence
sudo ln -s /etc/nginx/sites-available/eve-intelligence /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**Systemd Service:**
```bash
sudo cp /tmp/eve-intelligence-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable eve-intelligence-api
sudo systemctl start eve-intelligence-api
sudo systemctl status eve-intelligence-api
```

**Verify:**
```bash
curl https://eve.infinimind-creations.com/api/health
curl -I https://eve.infinimind-creations.com
```

---

## Next Steps (Post-Launch)

1. **Google AdSense Setup:**
   - Register eve.infinimind-creations.com in AdSense
   - Add `ads.txt` file to `public-frontend/public/`
   - Create AdSlot component with real ad unit IDs
   - Integrate ads into pages

2. **Analytics:**
   - Add Google Analytics 4 tracking
   - Setup Google Search Console
   - Configure UptimeRobot monitoring

3. **GDPR Compliance:**
   - Add cookie consent banner
   - Create privacy policy page
   - Create cookie policy page

4. **Detail Pages:**
   - Implement BattleReport.tsx with charts
   - Implement WarProfiteering.tsx with tables
   - Implement AllianceWars.tsx with conflict details
   - Implement TradeRoutes.tsx with route visualization

5. **SEO:**
   - Add meta tags to index.html
   - Create sitemap.xml
   - Add structured data (Schema.org)

---

## Estimated Timeline

- **Backend API:** ✅ Complete (Tasks 1-4)
- **Frontend Core:** ✅ Complete (Tasks 5-9)
- **Deployment:** ⏳ Manual steps required (Task 10-11)
- **Google Ads:** 📅 Post-launch (1 hour)
- **Detail Pages:** 📅 Post-launch (3-4 hours)
- **SEO/Analytics:** 📅 Post-launch (2 hours)

**Total Implementation Time:** ~6-8 hours (excluding manual deployment)

---

**End of Implementation Plan**
