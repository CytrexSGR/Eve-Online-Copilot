# Fix Public Frontend Display Issues - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix black screen issues on AllianceWars, TradeRoutes, and WarProfiteering pages, and add drill-down functionality to BattleReport

**Architecture:** Backend API responses don't match frontend TypeScript interfaces, causing rendering failures. Need to fix backend to return correct data structures matching frontend expectations.

**Tech Stack:** FastAPI (backend), React + TypeScript (frontend), Redis (caching)

---

## Root Cause Analysis

**Problem:** Three pages show only black screens:
- `/alliance-wars` - Black screen
- `/trade-routes` - Black screen
- `/war-profiteering` - Black screen
- `/battle-report` - Works but needs drill-down functionality

**Root Cause:** Backend API returns different structures than frontend expects

**API Mismatches Identified:**

1. **Alliance Wars** (`/api/reports/alliance-wars`)
   - Backend returns: `{ wars: [...], total_wars, period }`
   - Frontend expects: `{ period, global: {...}, conflicts: [...], strategic_hotspots }`
   - Missing: `global` summary, renamed `wars` → `conflicts`, different field names

2. **War Profiteering** (`/api/reports/war-profiteering`)
   - Backend returns: `{ items: [...], total_items, total_opportunity_value, period }`
   - Frontend expects: `{ period, global: {...}, items: [...], categories }`
   - Missing: `global` object with structured summary, `categories` breakdown

3. **Trade Routes** (`/api/reports/trade-routes`)
   - Backend returns: `{ timestamp, routes: [...], total_routes, period, danger_scale }`
   - Frontend expects: `{ period, global: {...}, routes: [...] }`
   - Missing: `global` summary object
   - Field name mismatches in `routes` array

---

## Task 1: Fix Alliance Wars Backend

**Files:**
- Modify: `public_api/routers/reports.py:30-50` (alliance-wars endpoint)
- Test: Manual curl test

**Step 1: Read current implementation**

```bash
# Read the current alliance wars endpoint
```

**Step 2: Update endpoint to return correct structure**

Add global summary calculation and rename fields:

```python
@router.get("/alliance-wars")
async def get_alliance_wars() -> Dict:
    try:
        # Get original wars data
        wars_data = zkill_live_service.get_alliance_wars()

        # Calculate global summary
        total_conflicts = len(wars_data.get("wars", []))
        all_alliances = set()
        total_kills = 0
        total_isk = 0

        for war in wars_data.get("wars", []):
            all_alliances.add(war["alliance_a_id"])
            all_alliances.add(war["alliance_b_id"])
            total_kills += war["total_kills"]
            total_isk += war["isk_destroyed_by_a"] + war["isk_destroyed_by_b"]

        # Transform wars to conflicts with correct field names
        conflicts = []
        for war in wars_data.get("wars", []):
            conflicts.append({
                "alliance_1_id": war["alliance_a_id"],
                "alliance_1_name": war["alliance_a_name"],
                "alliance_2_id": war["alliance_b_id"],
                "alliance_2_name": war["alliance_b_name"],
                "alliance_1_kills": war["kills_by_a"],
                "alliance_1_losses": war["kills_by_b"],
                "alliance_1_isk_destroyed": war["isk_destroyed_by_a"],
                "alliance_1_isk_lost": war["isk_destroyed_by_b"],
                "alliance_1_efficiency": war["isk_efficiency_a"],
                "alliance_2_kills": war["kills_by_b"],
                "alliance_2_losses": war["kills_by_a"],
                "alliance_2_isk_destroyed": war["isk_destroyed_by_b"],
                "alliance_2_isk_lost": war["isk_destroyed_by_a"],
                "alliance_2_efficiency": 100 - war["isk_efficiency_a"] if war["isk_efficiency_a"] <= 100 else 0,
                "duration_days": 1,  # TODO: Calculate from killmail timestamps
                "primary_regions": ["Unknown"],  # TODO: Get from system data
                "active_systems": [],  # TODO: Get top systems from killmails
                "winner": war["alliance_a_name"] if war["winner"] == "a" else war["alliance_b_name"] if war["winner"] == "b" else None
            })

        return {
            "period": wars_data.get("period", "24h"),
            "global": {
                "active_conflicts": total_conflicts,
                "total_alliances_involved": len(all_alliances),
                "total_kills": total_kills,
                "total_isk_destroyed": total_isk
            },
            "conflicts": conflicts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 3: Test with curl**

```bash
curl -s http://localhost:8001/api/reports/alliance-wars | python3 -m json.tool | head -50
```

Expected: JSON with `period`, `global`, and `conflicts` keys

**Step 4: Commit changes**

```bash
git add public_api/routers/reports.py
git commit -m "fix: alliance wars API to match frontend structure"
```

---

## Task 2: Fix War Profiteering Backend

**Files:**
- Modify: `public_api/routers/reports.py:55-75` (war-profiteering endpoint)
- Test: Manual curl test

**Step 1: Read current implementation**

```bash
# Read the current war profiteering endpoint
```

**Step 2: Update endpoint to return correct structure**

```python
@router.get("/war-profiteering")
async def get_war_profiteering() -> Dict:
    try:
        # Get original profiteering data
        profit_data = zkill_live_service.get_war_profiteering()

        # Convert Decimal to float for JSON serialization
        items = []
        total_items_destroyed = 0
        max_value_item = None
        max_value = 0

        for item in profit_data.get("items", []):
            market_price = float(item["market_price"])
            opportunity_value = float(item["opportunity_value"])
            qty = item["quantity_destroyed"]

            total_items_destroyed += qty

            if opportunity_value > max_value:
                max_value = opportunity_value
                max_value_item = item["item_name"]

            items.append({
                "item_type_id": item["item_type_id"],
                "item_name": item["item_name"],
                "quantity_destroyed": qty,
                "market_price": market_price,
                "opportunity_value": opportunity_value
            })

        return {
            "period": profit_data.get("period", "24h"),
            "global": {
                "total_opportunity_value": float(profit_data.get("total_opportunity_value", 0)),
                "total_items_destroyed": total_items_destroyed,
                "unique_item_types": len(items),
                "most_valuable_item": max_value_item or "N/A"
            },
            "items": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 3: Test with curl**

```bash
curl -s http://localhost:8001/api/reports/war-profiteering | python3 -m json.tool | head -50
```

Expected: JSON with `period`, `global`, and `items` keys

**Step 4: Commit changes**

```bash
git add public_api/routers/reports.py
git commit -m "fix: war profiteering API to match frontend structure"
```

---

## Task 3: Fix Trade Routes Backend

**Files:**
- Modify: `public_api/routers/reports.py:80-100` (trade-routes endpoint)
- Test: Manual curl test

**Step 1: Read current implementation**

```bash
# Read the current trade routes endpoint
```

**Step 2: Update endpoint to return correct structure**

```python
@router.get("/trade-routes")
async def get_trade_routes() -> Dict:
    try:
        # Get original routes data
        routes_data = zkill_live_service.get_trade_route_safety()

        # Calculate global summary
        total_routes = len(routes_data.get("routes", []))
        dangerous_count = 0
        total_danger = 0
        gate_camps = 0

        # Transform routes
        transformed_routes = []
        for route in routes_data.get("routes", []):
            avg_danger = route.get("avg_danger_score", 0)
            total_danger += avg_danger

            if avg_danger >= 5:
                dangerous_count += 1

            # Transform systems
            transformed_systems = []
            total_kills = 0
            total_isk = 0

            for system in route.get("systems", []):
                kills = system.get("kills_24h", 0)
                isk = system.get("isk_destroyed_24h", 0)
                is_camp = system.get("gate_camp_detected", False)

                total_kills += kills
                total_isk += isk
                if is_camp:
                    gate_camps += 1

                transformed_systems.append({
                    "system_id": system["system_id"],
                    "system_name": system["system_name"],
                    "security_status": system.get("security", 0),
                    "danger_score": system.get("danger_score", 0),
                    "kills_24h": kills,
                    "isk_destroyed_24h": isk,
                    "is_gate_camp": is_camp
                })

            transformed_routes.append({
                "origin_system": route["from_hub"],
                "destination_system": route["to_hub"],
                "jumps": route.get("total_jumps", 0),
                "danger_score": avg_danger,
                "total_kills": total_kills,
                "total_isk_destroyed": total_isk,
                "systems": transformed_systems
            })

        avg_danger_score = total_danger / total_routes if total_routes > 0 else 0

        return {
            "period": routes_data.get("period", "24h"),
            "global": {
                "total_routes": total_routes,
                "dangerous_routes": dangerous_count,
                "avg_danger_score": avg_danger_score,
                "gate_camps_detected": gate_camps
            },
            "routes": transformed_routes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 3: Test with curl**

```bash
curl -s http://localhost:8001/api/reports/trade-routes | python3 -m json.tool | head -80
```

Expected: JSON with `period`, `global`, and `routes` with correct field names

**Step 4: Commit changes**

```bash
git add public_api/routers/reports.py
git commit -m "fix: trade routes API to match frontend structure"
```

---

## Task 4: Add Drill-Down to Battle Report

**Files:**
- Modify: `public-frontend/src/pages/BattleReport.tsx:78-169` (regional cards)
- Create: `public-frontend/src/components/RegionDetailModal.tsx` (new modal component)

**Step 1: Create RegionDetailModal component**

Create modal that shows when clicking a region card:

```typescript
// public-frontend/src/components/RegionDetailModal.tsx
import { useState } from 'react';

interface RegionDetailModalProps {
  region: {
    region_id: number;
    region_name: string;
    kills: number;
    total_isk_destroyed: number;
    top_systems: Array<{ system_id: number; system_name: string; kills: number }>;
    top_ships: Array<{ ship_type_id: number; ship_name: string; losses: number }>;
    top_destroyed_items: Array<{ item_type_id: number; item_name: string; quantity_destroyed: number }>;
  };
  onClose: () => void;
}

export function RegionDetailModal({ region, onClose }: RegionDetailModalProps) {
  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          maxWidth: '900px',
          maxHeight: '80vh',
          overflow: 'auto',
          margin: '2rem'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2>{region.region_name} - Detailed Analysis</h2>
          <button
            onClick={onClose}
            style={{
              background: 'var(--danger)',
              border: 'none',
              color: 'white',
              padding: '0.5rem 1rem',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '1rem'
            }}
          >
            ✕ Close
          </button>
        </div>

        {/* Full detailed view - ALL systems, ALL ships, ALL items */}
        {/* ... rest of modal content */}
      </div>
    </div>
  );
}
```

**Step 2: Add modal state to BattleReport**

```typescript
const [selectedRegion, setSelectedRegion] = useState<typeof report.regions[0] | null>(null);
```

**Step 3: Make region cards clickable**

Add onClick to each region card to open modal

**Step 4: Test modal functionality**

Open http://192.168.178.108:5173/battle-report and click region cards

**Step 5: Commit changes**

```bash
git add public-frontend/src/pages/BattleReport.tsx public-frontend/src/components/RegionDetailModal.tsx
git commit -m "feat: add drill-down modal to battle report regions"
```

---

## Task 5: Verify All Pages Work

**Files:**
- Test: All 4 report pages in browser

**Step 1: Open each page in browser**

```bash
# Navigate to each URL and verify:
# - http://192.168.178.108:5173/battle-report (should show data + clickable regions)
# - http://192.168.178.108:5173/war-profiteering (should show profiteering table)
# - http://192.168.178.108:5173/alliance-wars (should show conflicts)
# - http://192.168.178.108:5173/trade-routes (should show routes with danger scores)
```

**Step 2: Check browser console for errors**

Open DevTools (F12) and check Console tab - should be no errors

**Step 3: Verify auto-refresh works**

Wait 60 seconds and check RefreshIndicator updates

**Step 4: Document test results**

Create test report if needed

---

## Task 6: Production Build

**Files:**
- Build: `public-frontend/dist/`

**Step 1: Build frontend for production**

```bash
cd /home/cytrex/eve_copilot/public-frontend
npm run build
```

Expected: Optimized bundle in `dist/` directory

**Step 2: Verify build output**

```bash
ls -lh dist/
```

Expected: index.html, assets/ directory with JS/CSS bundles

**Step 3: Test production build locally**

```bash
cd dist
python3 -m http.server 8080
```

Visit http://192.168.178.108:8080 and verify all pages work

**Step 4: Commit and push all changes**

```bash
git add -A
git commit -m "fix: complete public frontend with working data display and drill-down"
git push origin main
```

---

## Completion Criteria

- ✅ Alliance Wars page displays conflicts with full stats
- ✅ War Profiteering page shows items table
- ✅ Trade Routes page shows routes with danger analysis
- ✅ Battle Report has clickable regions with detail modal
- ✅ No console errors on any page
- ✅ Auto-refresh works on all pages
- ✅ Production build successful
- ✅ All changes committed and pushed to GitHub

---

## Notes

**API Structure Standardization:**
All public API endpoints now follow the pattern:
```json
{
  "period": "24h",
  "global": { /* summary metrics */ },
  "data_key": [ /* detailed data */ ]
}
```

**Future Enhancements:**
- Add strategic_hotspots to alliance wars (requires system mapping)
- Add categories breakdown to war profiteering (requires item categorization)
- Calculate actual duration_days for conflicts (requires killmail timestamp analysis)
- Add primary_regions to conflicts (requires system-to-region mapping)
