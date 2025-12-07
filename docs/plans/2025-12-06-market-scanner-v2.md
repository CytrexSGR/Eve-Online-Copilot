# Market Scanner V2 - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the EVE Co-Pilot Market Scanner into a full production optimization suite with bookmarks, shopping planning, route optimization, and corporation integration.

**Architecture:** Modular service-based backend with dedicated services for routing, planning, and corp data. React frontend with new pages for Shopping Planner and Logistics. All data flows through PostgreSQL with ESI caching.

**Tech Stack:** Python/FastAPI backend, React 19/TypeScript frontend, PostgreSQL database, ESI API for live data.

---

## Phase Overview

| Phase | Feature | Tasks |
|-------|---------|-------|
| 1 | UI/UX Improvements | 3 |
| 2 | Bookmark System | 4 |
| 3 | Material Availability | 3 |
| 4 | Shopping Planning | 4 |
| 5 | Route & Logistics | 5 |
| 6 | Corporation Integration | 4 |
| 7 | Production Optimization | 3 |
| 8 | Market Analysis | 3 |

---

## Phase 1: UI/UX Improvements

### Task 1.1: ISK Number Formatting Utility

**Files:**
- Create: `frontend/src/utils/format.ts`
- Modify: `frontend/src/pages/MarketScanner.tsx:57-63`

**Step 1: Create formatting utility**

```typescript
// frontend/src/utils/format.ts

/**
 * Format ISK values with German locale (dots as thousand separators)
 * @param value - The ISK value to format
 * @param compact - Use compact notation (K, M, B)
 */
export function formatISK(value: number | null | undefined, compact = true): string {
  if (value === null || value === undefined) return '-';

  if (compact) {
    if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
    return value.toFixed(0);
  }

  // Full format with German locale (1.234.567,89)
  return value.toLocaleString('de-DE', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  });
}

/**
 * Format percentage values
 */
export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  if (value > 1000) return '>1000%';
  return `${value.toFixed(1)}%`;
}

/**
 * Format volume in m3
 */
export function formatVolume(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M m³`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K m³`;
  return `${value.toFixed(0)} m³`;
}

/**
 * Format quantity with thousand separators
 */
export function formatQuantity(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  return value.toLocaleString('de-DE');
}
```

**Step 2: Update MarketScanner to use new utility**

Replace the local `formatISK` function in `MarketScanner.tsx` with import:

```typescript
// At top of file, add:
import { formatISK, formatPercent, formatQuantity } from '../utils/format';

// Remove lines 57-63 (local formatISK function)
```

**Step 3: Verify**

Run: `cd /home/cytrex/eve_copilot/frontend && npm run build`

**Step 4: Commit**

```bash
git add frontend/src/utils/format.ts frontend/src/pages/MarketScanner.tsx
git commit -m "feat: add ISK formatting utility with German locale"
```

---

### Task 1.2: Item Detail as Tab (Not Modal)

**Files:**
- Create: `frontend/src/pages/ItemDetail.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/MarketScanner.tsx`

**Step 1: Create ItemDetail page**

```typescript
// frontend/src/pages/ItemDetail.tsx
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Package, TrendingUp, ChevronRight } from 'lucide-react';
import { api } from '../api';
import { formatISK, formatQuantity } from '../utils/format';

interface ProductionData {
  type_id: number;
  item_name: string;
  me_level: number;
  materials: {
    type_id: number;
    name: string;
    base_quantity: number;
    adjusted_quantity: number;
    prices_by_region: Record<string, number>;
  }[];
  production_cost_by_region: Record<string, number>;
  cheapest_production_region: string;
  cheapest_production_cost: number;
  product_prices: Record<string, { lowest_sell: number; highest_buy: number }>;
  best_sell_region: string;
  best_sell_price: number;
}

const REGION_NAMES: Record<string, string> = {
  the_forge: 'Jita',
  domain: 'Amarr',
  heimatar: 'Rens',
  sinq_laison: 'Dodixie',
  metropolis: 'Hek',
};

export default function ItemDetail() {
  const { typeId } = useParams<{ typeId: string }>();
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery<ProductionData>({
    queryKey: ['production', typeId],
    queryFn: async () => {
      const response = await api.get(`/api/production/optimize/${typeId}`, {
        params: { me: 10 }
      });
      return response.data;
    },
    enabled: !!typeId,
  });

  const bestProfit = data
    ? data.best_sell_price - data.cheapest_production_cost
    : 0;

  if (isLoading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        Loading production data...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="empty-state">
        <p>No blueprint data available for this item.</p>
        <button className="btn btn-primary" onClick={() => navigate('/')}>
          <ArrowLeft size={16} /> Back to Scanner
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Breadcrumb */}
      <div className="breadcrumb">
        <Link to="/">Market Scanner</Link>
        <ChevronRight size={14} />
        <span>{data.item_name}</span>
      </div>

      <div className="page-header">
        <div>
          <h1>{data.item_name}</h1>
          <p>Production analysis with ME {data.me_level}</p>
        </div>
        <button className="btn" onClick={() => navigate('/')}>
          <ArrowLeft size={16} /> Back
        </button>
      </div>

      {/* Summary Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Best Production Cost</div>
          <div className="stat-value isk">{formatISK(data.cheapest_production_cost)}</div>
          <div className="neutral">in {REGION_NAMES[data.cheapest_production_region]}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Best Sell Price</div>
          <div className="stat-value isk positive">{formatISK(data.best_sell_price)}</div>
          <div className="neutral">in {REGION_NAMES[data.best_sell_region]}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Max Profit</div>
          <div className={`stat-value ${bestProfit > 0 ? 'positive' : 'negative'}`}>
            {bestProfit > 0 ? '+' : ''}{formatISK(bestProfit)}
          </div>
          <div className="neutral">
            ROI: {data.cheapest_production_cost > 0
              ? ((bestProfit / data.cheapest_production_cost) * 100).toFixed(1)
              : 0}%
          </div>
        </div>
      </div>

      {/* Materials Table */}
      <div className="card">
        <h3 style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Package size={18} />
          Required Materials (ME {data.me_level})
        </h3>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Material</th>
                <th>Quantity</th>
                {Object.keys(REGION_NAMES).map((region) => (
                  <th key={region}>{REGION_NAMES[region]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.materials.map((mat) => {
                const prices = Object.entries(mat.prices_by_region).filter(([_, p]) => p);
                const cheapestRegion = prices.length > 0
                  ? prices.sort((a, b) => a[1] - b[1])[0][0]
                  : null;

                return (
                  <tr key={mat.type_id}>
                    <td>
                      <Link to={`/item/${mat.type_id}`} className="material-link">
                        {mat.name}
                      </Link>
                    </td>
                    <td>{formatQuantity(mat.adjusted_quantity)}</td>
                    {Object.keys(REGION_NAMES).map((region) => {
                      const price = mat.prices_by_region[region];
                      const total = price ? price * mat.adjusted_quantity : null;
                      const isCheapest = region === cheapestRegion;
                      return (
                        <td key={region} className={`isk ${isCheapest ? 'positive' : ''}`}>
                          {formatISK(total)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
              <tr style={{ fontWeight: 'bold', background: 'var(--bg-dark)' }}>
                <td colSpan={2}>Total Cost</td>
                {Object.keys(REGION_NAMES).map((region) => {
                  const cost = data.production_cost_by_region[region];
                  const isCheapest = region === data.cheapest_production_region;
                  return (
                    <td key={region} className={`isk ${isCheapest ? 'positive' : ''}`}>
                      {formatISK(cost)}
                    </td>
                  );
                })}
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Sell Prices Grid */}
      <div className="card">
        <h3 style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <TrendingUp size={18} />
          Sell Prices & Profit by Region
        </h3>
        <div className="region-grid">
          {Object.entries(data.product_prices)
            .sort((a, b) => (b[1]?.highest_buy || 0) - (a[1]?.highest_buy || 0))
            .map(([region, prices]) => {
              const isBest = region === data.best_sell_region;
              const productionCost = data.production_cost_by_region[region] || data.cheapest_production_cost;
              const profitBuyOrder = (prices?.highest_buy || 0) - productionCost;

              return (
                <div key={region} className={`region-card ${isBest ? 'best' : ''}`}>
                  <div className="region-name">
                    {REGION_NAMES[region] || region}
                    {isBest && <span className="badge badge-green">Best</span>}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
                    <div>
                      <div className="neutral" style={{ fontSize: 11 }}>Sell Order</div>
                      <div className="isk">{formatISK(prices?.lowest_sell)}</div>
                    </div>
                    <div>
                      <div className="neutral" style={{ fontSize: 11 }}>Buy Order</div>
                      <div className="isk positive">{formatISK(prices?.highest_buy)}</div>
                    </div>
                  </div>
                  <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border)' }}>
                    <div className="neutral" style={{ fontSize: 10 }}>Profit (Instant Sell)</div>
                    <div className={profitBuyOrder > 0 ? 'positive' : 'negative'}>
                      {formatISK(profitBuyOrder)}
                    </div>
                  </div>
                </div>
              );
            })}
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Add route in App.tsx**

```typescript
// Add import at top:
import ItemDetail from './pages/ItemDetail';

// Add route in Routes:
<Route path="/item/:typeId" element={<ItemDetail />} />
```

**Step 3: Update MarketScanner to navigate instead of modal**

Replace click handler in table row:

```typescript
// In MarketScanner.tsx, change onClick:
onClick={() => navigate(`/item/${item.product_id}`)}

// Add at top:
import { useNavigate } from 'react-router-dom';

// Inside component:
const navigate = useNavigate();

// Remove modal state and ItemDetailModal component usage
```

**Step 4: Add breadcrumb CSS**

```css
/* Add to App.css */
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  color: var(--text-secondary);
  font-size: 14px;
}

.breadcrumb a {
  color: var(--primary);
  text-decoration: none;
}

.breadcrumb a:hover {
  text-decoration: underline;
}

.material-link {
  color: var(--primary);
  text-decoration: none;
}

.material-link:hover {
  text-decoration: underline;
}
```

**Step 5: Commit**

```bash
git add frontend/src/pages/ItemDetail.tsx frontend/src/App.tsx frontend/src/pages/MarketScanner.tsx frontend/src/App.css
git commit -m "feat: convert item detail modal to dedicated page with drill-down"
```

---

### Task 1.3: Recursive Material Drill-Down

**Files:**
- Modify: `frontend/src/pages/ItemDetail.tsx`
- Modify: `backend/database.py`
- Modify: `backend/main.py`

**Step 1: Add API endpoint for material composition**

Add to `database.py`:

```python
def get_material_composition(type_id: int) -> list:
    """Get what materials an item is made of (if it's craftable)"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if this item can be manufactured
            cur.execute('''
                SELECT
                    iap."typeID" as blueprint_id,
                    iam."materialTypeID" as material_type_id,
                    it."typeName" as material_name,
                    iam."quantity"
                FROM "industryActivityProducts" iap
                JOIN "industryActivityMaterials" iam
                    ON iam."typeID" = iap."typeID" AND iam."activityID" = 1
                JOIN "invTypes" it ON iam."materialTypeID" = it."typeID"
                WHERE iap."productTypeID" = %s
                AND iap."activityID" = 1
                ORDER BY iam."quantity" DESC
            ''', (type_id,))
            return cur.fetchall()
```

Add to `main.py`:

```python
@app.get("/api/materials/{type_id}/composition")
async def api_material_composition(type_id: int):
    """Get manufacturing composition for an item (if craftable)"""
    from database import get_material_composition, get_item_info

    composition = get_material_composition(type_id)
    item = get_item_info(type_id)

    return {
        "type_id": type_id,
        "item_name": item["typeName"] if item else f"Type {type_id}",
        "is_craftable": len(composition) > 0,
        "materials": [
            {
                "type_id": m["material_type_id"],
                "name": m["material_name"],
                "quantity": m["quantity"]
            }
            for m in composition
        ]
    }
```

**Step 2: Add drill-down indicator in ItemDetail**

Materials that are craftable should show a ">" icon and link to their detail page.

**Step 3: Commit**

```bash
git add database.py main.py frontend/src/pages/ItemDetail.tsx
git commit -m "feat: add recursive material drill-down for complex items"
```

---

## Phase 2: Bookmark System

### Task 2.1: Create Bookmark Database Schema

**Files:**
- Create: `backend/migrations/001_bookmarks.sql`

**Step 1: Create migration file**

```sql
-- migrations/001_bookmarks.sql
-- Bookmark System for EVE Co-Pilot

-- Characters table (links to ESI character data)
CREATE TABLE IF NOT EXISTS characters (
    character_id INTEGER PRIMARY KEY,
    character_name VARCHAR(255) NOT NULL,
    corporation_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert known characters
INSERT INTO characters (character_id, character_name, corporation_id) VALUES
    (526379435, 'Artallus', 98785281),
    (1117367444, 'Cytrex', 98785281),
    (110592475, 'Cytricia', 98785281)
ON CONFLICT (character_id) DO NOTHING;

-- Corporations table
CREATE TABLE IF NOT EXISTS corporations (
    corporation_id INTEGER PRIMARY KEY,
    corporation_name VARCHAR(255) NOT NULL,
    ticker VARCHAR(10),
    ceo_id INTEGER,
    home_system_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert Minimal Industries
INSERT INTO corporations (corporation_id, corporation_name, ticker, ceo_id, home_system_id) VALUES
    (98785281, 'Minimal Industries', 'MINDI', 1117367444, 30001365)
ON CONFLICT (corporation_id) DO NOTHING;

-- Bookmarks table
CREATE TABLE IF NOT EXISTS bookmarks (
    id SERIAL PRIMARY KEY,
    type_id INTEGER NOT NULL,
    item_name VARCHAR(255),
    character_id INTEGER REFERENCES characters(character_id),
    corporation_id INTEGER REFERENCES corporations(corporation_id),
    notes TEXT,
    tags VARCHAR(50)[],
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_bookmarks_character ON bookmarks(character_id);
CREATE INDEX idx_bookmarks_corporation ON bookmarks(corporation_id);
CREATE INDEX idx_bookmarks_type ON bookmarks(type_id);

-- Bookmark lists (folders/categories)
CREATE TABLE IF NOT EXISTS bookmark_lists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    character_id INTEGER REFERENCES characters(character_id),
    corporation_id INTEGER REFERENCES corporations(corporation_id),
    is_shared BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bookmark list membership
CREATE TABLE IF NOT EXISTS bookmark_list_items (
    list_id INTEGER REFERENCES bookmark_lists(id) ON DELETE CASCADE,
    bookmark_id INTEGER REFERENCES bookmarks(id) ON DELETE CASCADE,
    position INTEGER DEFAULT 0,
    PRIMARY KEY (list_id, bookmark_id)
);
```

**Step 2: Run migration**

```bash
echo 'Aug2012#' | sudo -S docker exec -i eve_db psql -U eve -d eve_sde < /home/cytrex/eve_copilot/migrations/001_bookmarks.sql
```

**Step 3: Commit**

```bash
mkdir -p migrations
git add migrations/001_bookmarks.sql
git commit -m "feat: add bookmark system database schema"
```

---

### Task 2.2: Create Bookmark API Endpoints

**Files:**
- Create: `backend/bookmark_service.py`
- Modify: `backend/main.py`

**Step 1: Create bookmark service**

```python
# bookmark_service.py
"""Bookmark Service for EVE Co-Pilot"""

from database import get_db_connection
from psycopg2.extras import RealDictCursor
from typing import Optional, List
from datetime import datetime


class BookmarkService:

    def create_bookmark(
        self,
        type_id: int,
        item_name: str,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        priority: int = 0
    ) -> dict:
        """Create a new bookmark"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    INSERT INTO bookmarks
                        (type_id, item_name, character_id, corporation_id, notes, tags, priority)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                ''', (type_id, item_name, character_id, corporation_id, notes, tags or [], priority))
                conn.commit()
                return dict(cur.fetchone())

    def get_bookmarks(
        self,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None,
        list_id: Optional[int] = None
    ) -> List[dict]:
        """Get bookmarks filtered by character/corp/list"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if list_id:
                    cur.execute('''
                        SELECT b.*, bli.position
                        FROM bookmarks b
                        JOIN bookmark_list_items bli ON b.id = bli.bookmark_id
                        WHERE bli.list_id = %s
                        ORDER BY bli.position, b.created_at DESC
                    ''', (list_id,))
                else:
                    where_clauses = []
                    params = []

                    if character_id:
                        where_clauses.append("character_id = %s")
                        params.append(character_id)
                    if corporation_id:
                        where_clauses.append("corporation_id = %s")
                        params.append(corporation_id)

                    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                    cur.execute(f'''
                        SELECT * FROM bookmarks
                        WHERE {where_sql}
                        ORDER BY priority DESC, created_at DESC
                    ''', params)

                return [dict(row) for row in cur.fetchall()]

    def delete_bookmark(self, bookmark_id: int) -> bool:
        """Delete a bookmark"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM bookmarks WHERE id = %s', (bookmark_id,))
                conn.commit()
                return cur.rowcount > 0

    def update_bookmark(
        self,
        bookmark_id: int,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        priority: Optional[int] = None
    ) -> dict:
        """Update bookmark fields"""
        updates = []
        params = []

        if notes is not None:
            updates.append("notes = %s")
            params.append(notes)
        if tags is not None:
            updates.append("tags = %s")
            params.append(tags)
        if priority is not None:
            updates.append("priority = %s")
            params.append(priority)

        updates.append("updated_at = %s")
        params.append(datetime.now())
        params.append(bookmark_id)

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f'''
                    UPDATE bookmarks
                    SET {", ".join(updates)}
                    WHERE id = %s
                    RETURNING *
                ''', params)
                conn.commit()
                result = cur.fetchone()
                return dict(result) if result else None

    def is_bookmarked(self, type_id: int, character_id: Optional[int] = None, corporation_id: Optional[int] = None) -> bool:
        """Check if an item is bookmarked"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                where_clauses = ["type_id = %s"]
                params = [type_id]

                if character_id:
                    where_clauses.append("character_id = %s")
                    params.append(character_id)
                if corporation_id:
                    where_clauses.append("corporation_id = %s")
                    params.append(corporation_id)

                cur.execute(f'''
                    SELECT COUNT(*) FROM bookmarks
                    WHERE {" AND ".join(where_clauses)}
                ''', params)
                return cur.fetchone()[0] > 0

    # Bookmark Lists
    def create_list(
        self,
        name: str,
        description: Optional[str] = None,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None,
        is_shared: bool = False
    ) -> dict:
        """Create a bookmark list"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    INSERT INTO bookmark_lists (name, description, character_id, corporation_id, is_shared)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                ''', (name, description, character_id, corporation_id, is_shared))
                conn.commit()
                return dict(cur.fetchone())

    def get_lists(
        self,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None
    ) -> List[dict]:
        """Get bookmark lists"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                where_clauses = []
                params = []

                if character_id:
                    where_clauses.append("(character_id = %s OR is_shared = TRUE)")
                    params.append(character_id)
                if corporation_id:
                    where_clauses.append("corporation_id = %s")
                    params.append(corporation_id)

                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                cur.execute(f'''
                    SELECT bl.*,
                           (SELECT COUNT(*) FROM bookmark_list_items WHERE list_id = bl.id) as item_count
                    FROM bookmark_lists bl
                    WHERE {where_sql}
                    ORDER BY bl.name
                ''', params)
                return [dict(row) for row in cur.fetchall()]

    def add_to_list(self, list_id: int, bookmark_id: int, position: int = 0) -> bool:
        """Add bookmark to list"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO bookmark_list_items (list_id, bookmark_id, position)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                ''', (list_id, bookmark_id, position))
                conn.commit()
                return cur.rowcount > 0

    def remove_from_list(self, list_id: int, bookmark_id: int) -> bool:
        """Remove bookmark from list"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    DELETE FROM bookmark_list_items
                    WHERE list_id = %s AND bookmark_id = %s
                ''', (list_id, bookmark_id))
                conn.commit()
                return cur.rowcount > 0


bookmark_service = BookmarkService()
```

**Step 2: Add API endpoints to main.py**

```python
# Add to main.py after existing endpoints

from bookmark_service import bookmark_service
from pydantic import BaseModel
from typing import List, Optional


class BookmarkCreate(BaseModel):
    type_id: int
    item_name: str
    character_id: Optional[int] = None
    corporation_id: Optional[int] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: int = 0


class BookmarkUpdate(BaseModel):
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: Optional[int] = None


class BookmarkListCreate(BaseModel):
    name: str
    description: Optional[str] = None
    character_id: Optional[int] = None
    corporation_id: Optional[int] = None
    is_shared: bool = False


# ============================================================
# Bookmark Endpoints
# ============================================================

@app.post("/api/bookmarks")
async def create_bookmark(request: BookmarkCreate):
    """Create a new bookmark"""
    return bookmark_service.create_bookmark(
        type_id=request.type_id,
        item_name=request.item_name,
        character_id=request.character_id,
        corporation_id=request.corporation_id,
        notes=request.notes,
        tags=request.tags,
        priority=request.priority
    )


@app.get("/api/bookmarks")
async def get_bookmarks(
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None),
    list_id: Optional[int] = Query(None)
):
    """Get bookmarks with optional filters"""
    return bookmark_service.get_bookmarks(character_id, corporation_id, list_id)


@app.get("/api/bookmarks/check/{type_id}")
async def check_bookmark(
    type_id: int,
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None)
):
    """Check if item is bookmarked"""
    return {"is_bookmarked": bookmark_service.is_bookmarked(type_id, character_id, corporation_id)}


@app.patch("/api/bookmarks/{bookmark_id}")
async def update_bookmark(bookmark_id: int, request: BookmarkUpdate):
    """Update a bookmark"""
    result = bookmark_service.update_bookmark(
        bookmark_id=bookmark_id,
        notes=request.notes,
        tags=request.tags,
        priority=request.priority
    )
    if not result:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return result


@app.delete("/api/bookmarks/{bookmark_id}")
async def delete_bookmark(bookmark_id: int):
    """Delete a bookmark"""
    if not bookmark_service.delete_bookmark(bookmark_id):
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"status": "deleted"}


@app.post("/api/bookmarks/lists")
async def create_bookmark_list(request: BookmarkListCreate):
    """Create a bookmark list"""
    return bookmark_service.create_list(
        name=request.name,
        description=request.description,
        character_id=request.character_id,
        corporation_id=request.corporation_id,
        is_shared=request.is_shared
    )


@app.get("/api/bookmarks/lists")
async def get_bookmark_lists(
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None)
):
    """Get bookmark lists"""
    return bookmark_service.get_lists(character_id, corporation_id)


@app.post("/api/bookmarks/lists/{list_id}/items/{bookmark_id}")
async def add_to_list(list_id: int, bookmark_id: int, position: int = Query(0)):
    """Add bookmark to list"""
    if not bookmark_service.add_to_list(list_id, bookmark_id, position):
        raise HTTPException(status_code=400, detail="Could not add to list")
    return {"status": "added"}


@app.delete("/api/bookmarks/lists/{list_id}/items/{bookmark_id}")
async def remove_from_list(list_id: int, bookmark_id: int):
    """Remove bookmark from list"""
    if not bookmark_service.remove_from_list(list_id, bookmark_id):
        raise HTTPException(status_code=404, detail="Item not in list")
    return {"status": "removed"}
```

**Step 3: Commit**

```bash
git add bookmark_service.py main.py
git commit -m "feat: add bookmark API endpoints"
```

---

### Task 2.3: Bookmark UI Components

**Files:**
- Create: `frontend/src/components/BookmarkButton.tsx`
- Create: `frontend/src/components/BookmarkSidebar.tsx`
- Modify: `frontend/src/pages/MarketScanner.tsx`
- Modify: `frontend/src/api.ts`

**Step 1: Create BookmarkButton component**

```typescript
// frontend/src/components/BookmarkButton.tsx
import { useState } from 'react';
import { Star } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

interface BookmarkButtonProps {
  typeId: number;
  itemName: string;
  characterId?: number;
  corporationId?: number;
  size?: number;
}

export default function BookmarkButton({
  typeId,
  itemName,
  characterId,
  corporationId,
  size = 18
}: BookmarkButtonProps) {
  const queryClient = useQueryClient();

  const { data: checkData } = useQuery({
    queryKey: ['bookmark-check', typeId, characterId, corporationId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (characterId) params.append('character_id', String(characterId));
      if (corporationId) params.append('corporation_id', String(corporationId));
      const response = await api.get(`/api/bookmarks/check/${typeId}?${params}`);
      return response.data;
    },
  });

  const isBookmarked = checkData?.is_bookmarked ?? false;

  const createMutation = useMutation({
    mutationFn: async () => {
      return api.post('/api/bookmarks', {
        type_id: typeId,
        item_name: itemName,
        character_id: characterId,
        corporation_id: corporationId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookmark-check', typeId] });
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] });
    },
  });

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!isBookmarked) {
      createMutation.mutate();
    }
    // TODO: If already bookmarked, show options (delete, add to list, etc.)
  };

  return (
    <button
      className={`bookmark-btn ${isBookmarked ? 'active' : ''}`}
      onClick={handleClick}
      title={isBookmarked ? 'Bookmarked' : 'Add bookmark'}
    >
      <Star
        size={size}
        fill={isBookmarked ? 'var(--warning)' : 'none'}
        color={isBookmarked ? 'var(--warning)' : 'currentColor'}
      />
    </button>
  );
}
```

**Step 2: Add CSS for bookmark button**

```css
/* Add to App.css */
.bookmark-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.bookmark-btn:hover {
  background: var(--bg-hover);
  color: var(--warning);
}

.bookmark-btn.active {
  color: var(--warning);
}
```

**Step 3: Add bookmark button to MarketScanner table**

```typescript
// In MarketScanner.tsx, add to table row:
import BookmarkButton from '../components/BookmarkButton';

// In table body, add column before ChevronRight:
<td onClick={(e) => e.stopPropagation()}>
  <BookmarkButton
    typeId={item.product_id}
    itemName={item.product_name}
    corporationId={98785281}  // MINDI
  />
</td>
```

**Step 4: Commit**

```bash
git add frontend/src/components/BookmarkButton.tsx frontend/src/pages/MarketScanner.tsx frontend/src/App.css
git commit -m "feat: add bookmark button component"
```

---

### Task 2.4: Bookmarks Page

**Files:**
- Create: `frontend/src/pages/Bookmarks.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Create Bookmarks page**

```typescript
// frontend/src/pages/Bookmarks.tsx
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Star, Trash2, Tag, FolderPlus, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { formatISK } from '../utils/format';

interface Bookmark {
  id: number;
  type_id: number;
  item_name: string;
  notes: string | null;
  tags: string[];
  priority: number;
  created_at: string;
}

export default function Bookmarks() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<'all' | 'character' | 'corporation'>('corporation');

  const { data: bookmarks, isLoading } = useQuery<Bookmark[]>({
    queryKey: ['bookmarks', filter],
    queryFn: async () => {
      const params = filter === 'corporation'
        ? { corporation_id: 98785281 }
        : filter === 'character'
        ? { character_id: 1117367444 }
        : {};
      const response = await api.get('/api/bookmarks', { params });
      return response.data;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/api/bookmarks/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] });
    },
  });

  return (
    <div>
      <div className="page-header">
        <h1>Bookmarks</h1>
        <p>Your saved items for quick access</p>
      </div>

      <div className="card">
        <div className="card-header">
          <div className="filter-tabs">
            <button
              className={`tab ${filter === 'corporation' ? 'active' : ''}`}
              onClick={() => setFilter('corporation')}
            >
              Corporation
            </button>
            <button
              className={`tab ${filter === 'character' ? 'active' : ''}`}
              onClick={() => setFilter('character')}
            >
              Personal
            </button>
            <button
              className={`tab ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              All
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="loading">
            <div className="spinner"></div>
            Loading bookmarks...
          </div>
        ) : !bookmarks?.length ? (
          <div className="empty-state">
            <Star size={48} />
            <p>No bookmarks yet</p>
            <p className="neutral">Star items in the Market Scanner to add them here</p>
          </div>
        ) : (
          <div className="bookmark-grid">
            {bookmarks.map((bookmark) => (
              <div
                key={bookmark.id}
                className="bookmark-card"
                onClick={() => navigate(`/item/${bookmark.type_id}`)}
              >
                <div className="bookmark-header">
                  <Star size={16} fill="var(--warning)" color="var(--warning)" />
                  <span className="bookmark-name">{bookmark.item_name}</span>
                  <button
                    className="btn-icon"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteMutation.mutate(bookmark.id);
                    }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                {bookmark.notes && (
                  <p className="bookmark-notes">{bookmark.notes}</p>
                )}
                {bookmark.tags?.length > 0 && (
                  <div className="bookmark-tags">
                    {bookmark.tags.map((tag) => (
                      <span key={tag} className="tag">{tag}</span>
                    ))}
                  </div>
                )}
                <ChevronRight size={16} className="neutral" />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

**Step 2: Add route and nav**

```typescript
// In App.tsx, add:
import Bookmarks from './pages/Bookmarks';
import { Star } from 'lucide-react';

// Add nav link:
<li>
  <NavLink to="/bookmarks" className={({ isActive }) => isActive ? 'active' : ''}>
    <Star size={20} />
    <span>Bookmarks</span>
  </NavLink>
</li>

// Add route:
<Route path="/bookmarks" element={<Bookmarks />} />
```

**Step 3: Add CSS**

```css
/* Add to App.css */
.filter-tabs {
  display: flex;
  gap: 8px;
}

.tab {
  padding: 8px 16px;
  border: none;
  background: var(--bg-dark);
  color: var(--text-secondary);
  border-radius: 4px;
  cursor: pointer;
}

.tab.active {
  background: var(--primary);
  color: white;
}

.bookmark-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  padding: 16px;
}

.bookmark-card {
  background: var(--bg-dark);
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.bookmark-card:hover {
  background: var(--bg-hover);
}

.bookmark-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bookmark-name {
  flex: 1;
  font-weight: 600;
}

.bookmark-notes {
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.bookmark-tags {
  display: flex;
  gap: 4px;
  margin-top: 8px;
}

.tag {
  background: var(--bg-card);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
}

.btn-icon {
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  color: var(--text-secondary);
  border-radius: 4px;
}

.btn-icon:hover {
  background: var(--bg-hover);
  color: var(--danger);
}
```

**Step 4: Commit**

```bash
git add frontend/src/pages/Bookmarks.tsx frontend/src/App.tsx frontend/src/App.css
git commit -m "feat: add bookmarks page with grid view"
```

---

## Phase 3: Material Availability

### Task 3.1: Add Volume Data to Material Queries

**Files:**
- Modify: `backend/esi_client.py`
- Modify: `backend/main.py`

**Step 1: Add volume fetching to ESI client**

Add method to `esi_client.py`:

```python
def get_market_depth(self, region_id: int, type_id: int) -> dict:
    """Get market depth (volume available at price points)"""
    orders = self._make_request(f"/markets/{region_id}/orders/", {"type_id": type_id})

    if not orders:
        return {"sell_volume": 0, "buy_volume": 0, "sell_orders": [], "buy_orders": []}

    sell_orders = [o for o in orders if not o.get("is_buy_order", False)]
    buy_orders = [o for o in orders if o.get("is_buy_order", False)]

    # Sort by price
    sell_orders.sort(key=lambda x: x.get("price", 0))
    buy_orders.sort(key=lambda x: x.get("price", 0), reverse=True)

    return {
        "sell_volume": sum(o.get("volume_remain", 0) for o in sell_orders),
        "buy_volume": sum(o.get("volume_remain", 0) for o in buy_orders),
        "lowest_sell_price": sell_orders[0]["price"] if sell_orders else None,
        "lowest_sell_volume": sell_orders[0]["volume_remain"] if sell_orders else 0,
        "highest_buy_price": buy_orders[0]["price"] if buy_orders else None,
        "highest_buy_volume": buy_orders[0]["volume_remain"] if buy_orders else 0,
        "sell_orders": len(sell_orders),
        "buy_orders": len(buy_orders),
    }
```

**Step 2: Add endpoint for material volumes**

```python
# Add to main.py

@app.get("/api/materials/{type_id}/volumes")
async def api_material_volumes(type_id: int):
    """Get available volumes for a material across regions"""
    volumes = {}
    for region_name, region_id in REGIONS.items():
        depth = esi_client.get_market_depth(region_id, type_id)
        volumes[region_name] = {
            "sell_volume": depth["sell_volume"],
            "lowest_sell": depth["lowest_sell_price"],
            "sell_orders": depth["sell_orders"],
        }

    return {
        "type_id": type_id,
        "volumes_by_region": volumes
    }
```

**Step 3: Commit**

```bash
git add esi_client.py main.py
git commit -m "feat: add material volume/depth API endpoints"
```

---

### Task 3.2: Show Volume in Item Detail

**Files:**
- Modify: `frontend/src/pages/ItemDetail.tsx`

**Step 1: Add volume column to materials table**

Fetch volume data and show color-coded availability:
- Green: > 10x needed quantity
- Yellow: 1-10x needed
- Red: < needed quantity

```typescript
// Add query for volumes
const { data: volumeData } = useQuery({
  queryKey: ['material-volumes', data?.materials?.map(m => m.type_id)],
  queryFn: async () => {
    if (!data?.materials) return {};
    const volumes: Record<number, any> = {};
    for (const mat of data.materials) {
      const response = await api.get(`/api/materials/${mat.type_id}/volumes`);
      volumes[mat.type_id] = response.data.volumes_by_region;
    }
    return volumes;
  },
  enabled: !!data?.materials,
});

// Add volume indicator function
function VolumeIndicator({ available, needed }: { available: number; needed: number }) {
  const ratio = available / needed;
  let colorClass = 'negative';
  if (ratio >= 10) colorClass = 'positive';
  else if (ratio >= 1) colorClass = 'warning';

  return (
    <span className={colorClass} title={`${available.toLocaleString()} available`}>
      {ratio >= 10 ? '++' : ratio >= 1 ? '+' : '!'}
    </span>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/pages/ItemDetail.tsx
git commit -m "feat: show material volume availability with color coding"
```

---

### Task 3.3: Materials Overview Tab

**Files:**
- Create: `frontend/src/pages/MaterialsOverview.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Create Materials Overview page**

This page aggregates materials from all bookmarked items.

```typescript
// frontend/src/pages/MaterialsOverview.tsx
import { useQuery } from '@tanstack/react-query';
import { Package, Download } from 'lucide-react';
import { api } from '../api';
import { formatISK, formatQuantity } from '../utils/format';

// Component that:
// 1. Loads all bookmarks
// 2. For each bookmark, loads material requirements
// 3. Aggregates total quantities needed
// 4. Shows availability per region
// 5. Provides CSV export

export default function MaterialsOverview() {
  // Implementation details...
  return (
    <div>
      <div className="page-header">
        <h1>Materials Overview</h1>
        <p>Aggregated materials from your bookmarked items</p>
      </div>
      {/* Material aggregation table */}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/pages/MaterialsOverview.tsx frontend/src/App.tsx
git commit -m "feat: add materials overview page with aggregation"
```

---

## Phase 4: Shopping Planning

### Task 4.1: Shopping List Database Schema

**Files:**
- Create: `backend/migrations/002_shopping.sql`

**Step 1: Create migration**

```sql
-- migrations/002_shopping.sql
-- Shopping Lists for EVE Co-Pilot

CREATE TABLE IF NOT EXISTS shopping_lists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    character_id INTEGER REFERENCES characters(character_id),
    corporation_id INTEGER REFERENCES corporations(corporation_id),
    status VARCHAR(50) DEFAULT 'planning',  -- planning, shopping, complete
    total_cost DECIMAL(20, 2),
    total_volume DECIMAL(20, 2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS shopping_list_items (
    id SERIAL PRIMARY KEY,
    list_id INTEGER REFERENCES shopping_lists(id) ON DELETE CASCADE,
    type_id INTEGER NOT NULL,
    item_name VARCHAR(255),
    quantity INTEGER NOT NULL,
    target_region VARCHAR(50),
    target_price DECIMAL(20, 2),
    actual_price DECIMAL(20, 2),
    is_purchased BOOLEAN DEFAULT FALSE,
    purchased_at TIMESTAMP,
    notes TEXT
);

CREATE INDEX idx_shopping_list_items_list ON shopping_list_items(list_id);
```

**Step 2: Run migration**

```bash
echo 'Aug2012#' | sudo -S docker exec -i eve_db psql -U eve -d eve_sde < /home/cytrex/eve_copilot/migrations/002_shopping.sql
```

**Step 3: Commit**

```bash
git add migrations/002_shopping.sql
git commit -m "feat: add shopping list database schema"
```

---

### Task 4.2: Shopping Service Backend

**Files:**
- Create: `backend/shopping_service.py`
- Modify: `backend/main.py`

**Step 1: Create shopping service**

```python
# shopping_service.py
"""Shopping List Service for EVE Co-Pilot"""

from database import get_db_connection
from psycopg2.extras import RealDictCursor
from typing import Optional, List
from datetime import datetime


class ShoppingService:

    def create_list(
        self,
        name: str,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> dict:
        """Create a new shopping list"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    INSERT INTO shopping_lists (name, character_id, corporation_id, notes)
                    VALUES (%s, %s, %s, %s)
                    RETURNING *
                ''', (name, character_id, corporation_id, notes))
                conn.commit()
                return dict(cur.fetchone())

    def get_lists(
        self,
        character_id: Optional[int] = None,
        corporation_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[dict]:
        """Get shopping lists"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                where_clauses = []
                params = []

                if character_id:
                    where_clauses.append("character_id = %s")
                    params.append(character_id)
                if corporation_id:
                    where_clauses.append("corporation_id = %s")
                    params.append(corporation_id)
                if status:
                    where_clauses.append("status = %s")
                    params.append(status)

                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                cur.execute(f'''
                    SELECT sl.*,
                           (SELECT COUNT(*) FROM shopping_list_items WHERE list_id = sl.id) as item_count,
                           (SELECT COUNT(*) FROM shopping_list_items WHERE list_id = sl.id AND is_purchased) as purchased_count
                    FROM shopping_lists sl
                    WHERE {where_sql}
                    ORDER BY sl.created_at DESC
                ''', params)
                return [dict(row) for row in cur.fetchall()]

    def get_list_with_items(self, list_id: int) -> dict:
        """Get shopping list with all items"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('SELECT * FROM shopping_lists WHERE id = %s', (list_id,))
                shopping_list = cur.fetchone()

                if not shopping_list:
                    return None

                cur.execute('''
                    SELECT * FROM shopping_list_items
                    WHERE list_id = %s
                    ORDER BY target_region, item_name
                ''', (list_id,))
                items = cur.fetchall()

                result = dict(shopping_list)
                result['items'] = [dict(item) for item in items]
                return result

    def add_item(
        self,
        list_id: int,
        type_id: int,
        item_name: str,
        quantity: int,
        target_region: Optional[str] = None,
        target_price: Optional[float] = None
    ) -> dict:
        """Add item to shopping list"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    INSERT INTO shopping_list_items
                        (list_id, type_id, item_name, quantity, target_region, target_price)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                ''', (list_id, type_id, item_name, quantity, target_region, target_price))
                conn.commit()
                self._update_list_totals(list_id)
                return dict(cur.fetchone())

    def mark_purchased(
        self,
        item_id: int,
        actual_price: Optional[float] = None
    ) -> dict:
        """Mark item as purchased"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    UPDATE shopping_list_items
                    SET is_purchased = TRUE, purchased_at = %s, actual_price = %s
                    WHERE id = %s
                    RETURNING *
                ''', (datetime.now(), actual_price, item_id))
                conn.commit()
                result = cur.fetchone()
                if result:
                    self._update_list_totals(result['list_id'])
                return dict(result) if result else None

    def _update_list_totals(self, list_id: int):
        """Update list total cost and volume"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE shopping_lists
                    SET total_cost = (
                        SELECT COALESCE(SUM(COALESCE(actual_price, target_price) * quantity), 0)
                        FROM shopping_list_items WHERE list_id = %s
                    ),
                    updated_at = %s
                    WHERE id = %s
                ''', (list_id, datetime.now(), list_id))
                conn.commit()

    def optimize_by_region(self, list_id: int) -> dict:
        """Calculate optimal purchase regions for all items"""
        # This will use the ESI price data to suggest best regions
        items = self.get_list_with_items(list_id)
        if not items:
            return None

        # Group items by optimal region
        # Compare total cost: all-in-one-region vs. optimized multi-region
        # Return savings calculation
        return {
            "list_id": list_id,
            "single_region_best": "the_forge",
            "single_region_cost": 0,
            "optimized_regions": {},
            "optimized_cost": 0,
            "savings": 0
        }


shopping_service = ShoppingService()
```

**Step 2: Add API endpoints**

Add shopping endpoints to `main.py` similar to bookmark endpoints.

**Step 3: Commit**

```bash
git add shopping_service.py main.py
git commit -m "feat: add shopping list service and API"
```

---

### Task 4.3: Shopping Planner Page

**Files:**
- Create: `frontend/src/pages/ShoppingPlanner.tsx`
- Modify: `frontend/src/App.tsx`

Create the Shopping Planner UI with:
- List management
- Item checkboxes
- Region optimization
- Cost summaries
- Export to clipboard (EVE multibuy format)

---

### Task 4.4: Add to Shopping List Flow

Enable adding items from ItemDetail page to a shopping list with quantity selection.

---

## Phase 5: Route & Logistics

### Task 5.1: Route Service with A* Pathfinding

**Files:**
- Create: `backend/route_service.py`

**Step 1: Create route service with A* algorithm**

```python
# route_service.py
"""Route calculation service using SDE jump data"""

from database import get_db_connection
from psycopg2.extras import RealDictCursor
from typing import List, Optional, Tuple
from heapq import heappush, heappop
from functools import lru_cache


class RouteService:
    def __init__(self):
        self._graph = None
        self._systems = None

    def _load_graph(self):
        """Load jump graph from database"""
        if self._graph is not None:
            return

        self._graph = {}
        self._systems = {}

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Load systems with security
                cur.execute('''
                    SELECT "solarSystemID", "solarSystemName", "security", "regionID"
                    FROM "mapSolarSystems"
                ''')
                for row in cur.fetchall():
                    self._systems[row['solarSystemID']] = {
                        'name': row['solarSystemName'],
                        'security': float(row['security']),
                        'region_id': row['regionID']
                    }

                # Load jumps
                cur.execute('''
                    SELECT "fromSolarSystemID", "toSolarSystemID"
                    FROM "mapSolarSystemJumps"
                ''')
                for row in cur.fetchall():
                    from_id = row['fromSolarSystemID']
                    to_id = row['toSolarSystemID']

                    if from_id not in self._graph:
                        self._graph[from_id] = []
                    self._graph[from_id].append(to_id)

    def find_route(
        self,
        from_system_id: int,
        to_system_id: int,
        avoid_lowsec: bool = True,
        avoid_nullsec: bool = True
    ) -> Optional[List[dict]]:
        """Find route using A* algorithm"""
        self._load_graph()

        if from_system_id not in self._systems or to_system_id not in self._systems:
            return None

        # A* implementation
        open_set = [(0, from_system_id, [from_system_id])]
        visited = set()

        while open_set:
            _, current, path = heappop(open_set)

            if current == to_system_id:
                return self._build_route_info(path)

            if current in visited:
                continue
            visited.add(current)

            for neighbor in self._graph.get(current, []):
                if neighbor in visited:
                    continue

                # Check security filters
                sec = self._systems[neighbor]['security']
                if avoid_nullsec and sec < 0.0:
                    continue
                if avoid_lowsec and sec < 0.5:
                    continue

                new_path = path + [neighbor]
                # Heuristic: just use path length (uniform cost)
                heappush(open_set, (len(new_path), neighbor, new_path))

        return None  # No route found

    def _build_route_info(self, path: List[int]) -> List[dict]:
        """Build detailed route information"""
        return [
            {
                'system_id': sys_id,
                'system_name': self._systems[sys_id]['name'],
                'security': round(self._systems[sys_id]['security'], 2),
                'region_id': self._systems[sys_id]['region_id'],
                'jump_number': i
            }
            for i, sys_id in enumerate(path)
        ]

    def get_system_by_name(self, name: str) -> Optional[dict]:
        """Find system by name"""
        self._load_graph()
        for sys_id, info in self._systems.items():
            if info['name'].lower() == name.lower():
                return {'system_id': sys_id, **info}
        return None

    def calculate_travel_time(
        self,
        route: List[dict],
        align_time_seconds: int = 10,
        warp_time_per_system: int = 30
    ) -> dict:
        """Estimate travel time for a route"""
        jumps = len(route) - 1
        total_seconds = jumps * (align_time_seconds + warp_time_per_system)

        return {
            'jumps': jumps,
            'estimated_seconds': total_seconds,
            'estimated_minutes': round(total_seconds / 60, 1),
            'formatted': f"{jumps} jumps (~{round(total_seconds/60)} min)"
        }


route_service = RouteService()
```

**Step 2: Add API endpoints**

```python
# Add to main.py

@app.get("/api/route/{from_system}/{to_system}")
async def api_calculate_route(
    from_system: str,
    to_system: str,
    highsec_only: bool = Query(True, description="Only use HighSec systems")
):
    """Calculate route between two systems"""
    from route_service import route_service

    # Resolve system names to IDs
    from_sys = route_service.get_system_by_name(from_system)
    to_sys = route_service.get_system_by_name(to_system)

    if not from_sys:
        raise HTTPException(status_code=404, detail=f"System not found: {from_system}")
    if not to_sys:
        raise HTTPException(status_code=404, detail=f"System not found: {to_system}")

    route = route_service.find_route(
        from_sys['system_id'],
        to_sys['system_id'],
        avoid_lowsec=highsec_only,
        avoid_nullsec=True
    )

    if not route:
        raise HTTPException(status_code=404, detail="No route found with current filters")

    travel_time = route_service.calculate_travel_time(route)

    return {
        "from": from_sys,
        "to": to_sys,
        "route": route,
        "travel_time": travel_time,
        "highsec_only": highsec_only
    }


@app.get("/api/systems/search")
async def api_search_systems(q: str = Query(..., min_length=2)):
    """Search for solar systems by name"""
    from route_service import route_service
    route_service._load_graph()

    results = []
    q_lower = q.lower()
    for sys_id, info in route_service._systems.items():
        if q_lower in info['name'].lower():
            results.append({'system_id': sys_id, **info})
            if len(results) >= 10:
                break

    return {"query": q, "results": results}
```

**Step 3: Commit**

```bash
git add route_service.py main.py
git commit -m "feat: add A* pathfinding route service for HighSec routes"
```

---

### Task 5.2: Trade Hub Distances

**Files:**
- Modify: `backend/route_service.py`

Pre-calculate and cache distances between all trade hubs and Isikemi (home base).

```python
TRADE_HUB_SYSTEMS = {
    'jita': 30000142,
    'amarr': 30002187,
    'rens': 30002510,
    'dodixie': 30002659,
    'hek': 30002053,
    'isikemi': 30001365  # Home base
}

def get_hub_distances(self, from_system: str = 'isikemi') -> dict:
    """Get distances from a system to all trade hubs"""
    from_id = TRADE_HUB_SYSTEMS.get(from_system.lower())
    if not from_id:
        from_sys = self.get_system_by_name(from_system)
        from_id = from_sys['system_id'] if from_sys else None

    if not from_id:
        return {}

    distances = {}
    for hub_name, hub_id in TRADE_HUB_SYSTEMS.items():
        if hub_id == from_id:
            distances[hub_name] = {'jumps': 0, 'time': '0 min'}
            continue

        route = self.find_route(from_id, hub_id, avoid_lowsec=True)
        if route:
            travel = self.calculate_travel_time(route)
            distances[hub_name] = {
                'jumps': travel['jumps'],
                'time': travel['formatted']
            }

    return distances
```

---

### Task 5.3: Cargo Volume Calculator

**Files:**
- Create: `backend/cargo_service.py`

Calculate total cargo volume for shopping lists and recommend ship types.

```python
# cargo_service.py

SHIP_CARGO_CAPACITY = {
    'shuttle': 10,
    'frigate': 400,
    'destroyer': 500,
    'cruiser': 500,
    'industrial': 5000,
    'blockade_runner': 10000,
    'deep_space_transport': 60000,
    'freighter': 1000000
}

def recommend_ship(volume_m3: float) -> dict:
    """Recommend ship based on cargo volume"""
    for ship, capacity in SHIP_CARGO_CAPACITY.items():
        if volume_m3 <= capacity:
            return {
                'recommended': ship,
                'capacity': capacity,
                'fill_percent': round((volume_m3 / capacity) * 100, 1)
            }

    trips = ceil(volume_m3 / SHIP_CARGO_CAPACITY['freighter'])
    return {
        'recommended': 'freighter',
        'capacity': SHIP_CARGO_CAPACITY['freighter'],
        'trips_needed': trips
    }
```

---

### Task 5.4: Logistics Planner Page

**Files:**
- Create: `frontend/src/pages/LogisticsPlanner.tsx`

Create UI showing:
- Route from Isikemi to each trade hub
- Security status along route
- Cargo requirements
- Ship recommendations
- Optimized shopping route

---

### Task 5.5: Route Visualization

Add visual route display with security colors.

---

## Phase 6: Corporation Integration

### Task 6.1: Corp Assets Endpoint

**Files:**
- Modify: `backend/character.py`
- Modify: `backend/main.py`

Add corporation asset fetching with ESI scope `esi-assets.read_corporation_assets.v1`.

---

### Task 6.2: Corp Industry Jobs

Add fetching of active corporation industry jobs to see what's already being produced.

---

### Task 6.3: Material Check Against Corp Hangar

When viewing materials, check if they're already in the Isikemi Corp Hangar.

---

### Task 6.4: Corp Dashboard Page

**Files:**
- Create: `frontend/src/pages/CorpDashboard.tsx`

Show:
- Corp wallet balances
- Assets in Isikemi
- Active industry jobs
- Pending shopping lists

---

## Phase 7: Production Optimization

### Task 7.1: Home System Configuration

**Files:**
- Create: `backend/migrations/003_settings.sql`
- Create: `backend/settings_service.py`

Store user/corp settings like home system, preferred ME level, etc.

---

### Task 7.2: Engineering Complex Bonuses

Add support for structure bonuses (Raitaru, Azbel, Sotiyo) that reduce material costs.

---

### Task 7.3: System Cost Index

Fetch and display system cost index for production, factor into profit calculations.

---

## Phase 8: Market Analysis

### Task 8.1: Price History Tracking

**Files:**
- Create: `backend/migrations/004_price_history.sql`
- Modify: `backend/jobs/batch_calculator.py`

Store daily snapshots of prices for trend analysis.

---

### Task 8.2: Price Trend Display

Show 7-day/30-day price trends in ItemDetail page.

---

### Task 8.3: Volume Trend Analysis

Track and display trading volume trends to identify market activity.

---

## Summary

**Total Tasks:** 29 tasks across 8 phases

**Execution Order:**
1. Phase 1 (UI) - Foundation
2. Phase 2 (Bookmarks) - Core feature
3. Phase 5 (Routes) - Critical for shopping
4. Phase 3 (Materials) - Depends on routes
5. Phase 4 (Shopping) - Combines all above
6. Phase 6 (Corp) - Enhancement
7. Phase 7 (Production) - Enhancement
8. Phase 8 (Market) - Enhancement

**Dependencies:**
- Phase 3 requires Phase 1.1 (formatting)
- Phase 4 requires Phase 2 + 3 + 5
- Phase 6 requires existing auth system
- Phase 7 requires Phase 4
- Phase 8 requires Phase 4

---

**Plan complete and saved to `docs/plans/2025-12-06-market-scanner-v2.md`.**

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
