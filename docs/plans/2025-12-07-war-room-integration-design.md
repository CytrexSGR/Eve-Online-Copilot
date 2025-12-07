# War Room Integration Design

## Overview

Connect War Room combat data with existing modules (Scanner, Production, Shopping) through a unified Item Detail page with clickable items throughout the application.

## Goals

1. Make all items in War Room clickable → navigate to `/item/{type_id}`
2. Create unified Item Detail page with collapsible panels
3. Add Combat Stats panel showing losses and market gaps
4. Enable seamless flow: War Room → Item Detail → Add to List → Shopping

## Architecture

### Frontend Changes

#### 1. War Room - Clickable Items

All item lists become clickable links:
- Ships Destroyed
- Top Ships Galaxy-Wide
- Market Gaps
- Items Destroyed

Click navigates to `/item/{type_id}` using React Router.

#### 2. Item Detail Page - Collapsible Panels

Restructure `ItemDetail.tsx` with four collapsible panels:

```
▼ Overview
   - Item icon (from images.evetech.net/types/{id}/icon)
   - Item name, group, category
   - "Add to List" button (prominent)

▼ Combat Stats
   - Total destroyed (7d)
   - Breakdown by region
   - Market comparison (destroyed vs. stock)
   - Gap indicator (red if negative, green if surplus)
   - Shows "No recent combat data" if no losses

▼ Production
   - Material requirements (with ME level selector)
   - Production cost per region
   - Profit margin vs. market price

▼ Market Prices
   - Regional price comparison table
   - Best buy / best sell region highlighted
   - Price trend (if available)
```

### Backend Changes

#### New API Endpoint

```
GET /api/war/item/{type_id}/stats?days=7
```

Response:
```json
{
  "type_id": 4310,
  "type_name": "Tornado",
  "days": 7,
  "total_destroyed": 22,
  "by_region": [
    {"region_id": 10000002, "region_name": "The Forge", "destroyed": 15},
    {"region_id": 10000043, "region_name": "Domain", "destroyed": 7}
  ],
  "market_comparison": [
    {"region": "the_forge", "destroyed": 15, "stock": 45, "gap": 30},
    {"region": "domain", "destroyed": 7, "stock": 12, "gap": 5}
  ],
  "has_data": true
}
```

Queries both `combat_ship_losses` and `combat_item_losses` tables.

### Image Handling

Item icons loaded directly from EVE Image Server (CDN):
- Icon: `https://images.evetech.net/types/{type_id}/icon?size=64`
- Render: `https://images.evetech.net/types/{type_id}/render?size=128`

No local caching needed - browser handles HTTP caching automatically.

## Data Flow

```
War Room Page
    │
    ├─ Click "Tornado (22)"
    │
    ▼
Item Detail Page (/item/4310)
    │
    ├─ Fetch: GET /api/war/item/4310/stats
    ├─ Fetch: GET /api/production/optimize/4310 (existing)
    ├─ Fetch: GET /api/market/compare/4310 (existing)
    │
    ▼
Display Panels
    │
    ├─ Click "Add to List"
    │
    ▼
Shopping List Flow (existing)
```

## UI Components

### CollapsiblePanel Component

```tsx
interface CollapsiblePanelProps {
  title: string;
  icon: LucideIcon;
  defaultOpen?: boolean;
  children: React.ReactNode;
}
```

### CombatStatsPanel Component

```tsx
interface CombatStatsPanelProps {
  typeId: number;
  days?: number;
}
```

Fetches data from `/api/war/item/{type_id}/stats` and displays:
- Total destroyed badge
- Regional breakdown table
- Market gap indicators

## Files to Modify

### Backend
- `routers/war.py` - Add `/item/{type_id}/stats` endpoint
- `war_analyzer.py` - Add `get_item_combat_stats()` method

### Frontend
- `pages/WarRoom.tsx` - Make items clickable (Link components)
- `pages/ItemDetail.tsx` - Restructure with collapsible panels
- `components/CollapsiblePanel.tsx` - New reusable component
- `components/CombatStatsPanel.tsx` - New component for combat data
- `api.ts` - Add `getItemCombatStats()` function

## Implementation Order

1. Backend: Add API endpoint for item combat stats
2. Frontend: Create CollapsiblePanel component
3. Frontend: Create CombatStatsPanel component
4. Frontend: Restructure ItemDetail with panels
5. Frontend: Make War Room items clickable
6. Testing: Verify full flow works

## Success Criteria

- [ ] Click any item in War Room → navigates to Item Detail
- [ ] Item Detail shows all four panels (collapsible)
- [ ] Combat Stats shows losses + market gaps (or "No data")
- [ ] "Add to List" works from Item Detail
- [ ] Item icons display correctly from EVE Image Server
