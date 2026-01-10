# EVE Copilot - Complete Refactoring Plan

## Overview

Split 7 critical files (>1000 lines each) into focused, maintainable modules.

## Target Files

| File | Lines | Split Into |
|------|-------|------------|
| `services/zkillboard/reports_service.py` | 2516 | 6 modules |
| `services/zkillboard/live_service.py` | 2358 | 5 modules |
| `routers/war.py` | 1626 | 4 routers |
| `src/shopping_service.py` | 1357 | 4 modules |
| `ectmap/app/components/SystemDetail.tsx` | 2085 | 6 components |
| `ectmap/app/components/StarMap.tsx` | 1242 | 4 components |
| `frontend/src/pages/ShoppingPlanner.tsx` | 1229 | 5 components |

---

## 1. reports_service.py (2516 lines) → 6 modules

**Current:** One massive class with all report types mixed together.

**New Structure:**
```
services/zkillboard/reports/
├── __init__.py              # Re-exports for backwards compatibility
├── base.py                  # Base class, shared utilities
├── pilot_intelligence.py    # 24h battle report
├── war_profiteering.py      # Market opportunities from combat
├── alliance_wars.py         # Alliance conflict tracking
├── trade_routes.py          # Route danger analysis
├── war_economy.py           # Fleet doctrines, regional demand
└── fleet_doctrines.py       # Doctrine detection logic
```

---

## 2. live_service.py (2358 lines) → 5 modules

**Current:** Battle tracking, killmail processing, Redis caching, API calls all mixed.

**New Structure:**
```
services/zkillboard/
├── __init__.py              # Main service facade
├── live/
│   ├── __init__.py
│   ├── battle_tracker.py    # Battle detection & lifecycle
│   ├── killmail_processor.py # Killmail parsing & enrichment
│   ├── redis_cache.py       # Redis operations
│   ├── telegram_alerts.py   # Telegram notifications
│   └── statistics.py        # Stats aggregation
```

---

## 3. routers/war.py (1626 lines) → 4 routers

**Current:** All war-related endpoints in one file.

**New Structure:**
```
routers/war/
├── __init__.py              # Router aggregation
├── battles.py               # /api/war/battles/* endpoints
├── systems.py               # /api/war/system/* endpoints
├── alliances.py             # /api/war/conflicts, /api/war/doctrines
└── map.py                   # /api/war/map/*, /api/war/heatmap
```

---

## 4. shopping_service.py (1357 lines) → 4 modules

**Current:** Shopping lists, materials, routing, regions all mixed.

**New Structure:**
```
src/shopping/
├── __init__.py              # Service facade
├── lists.py                 # List CRUD operations
├── materials.py             # Material calculations
├── routing.py               # Shopping route optimization
└── regions.py               # Regional price comparison
```

---

## 5. SystemDetail.tsx (2085 lines) → 6 components

**Current:** Massive component with all system info panels.

**New Structure:**
```
ectmap/app/components/system-detail/
├── index.tsx                # Main container
├── SystemHeader.tsx         # System name, security, region
├── KillActivity.tsx         # Recent kills panel
├── BattleInfo.tsx           # Active battle info
├── StationList.tsx          # Stations & services
├── JumpConnections.tsx      # Connected systems
└── hooks/
    └── useSystemData.ts     # Data fetching hook
```

---

## 6. StarMap.tsx (1242 lines) → 4 components

**Current:** Map rendering, controls, overlays all in one.

**New Structure:**
```
ectmap/app/components/star-map/
├── index.tsx                # Main canvas container
├── MapCanvas.tsx            # Canvas rendering logic
├── MapControls.tsx          # Zoom, pan, layer toggles
├── BattleOverlay.tsx        # Battle markers & animations
└── hooks/
    └── useMapState.ts       # Map state management
```

---

## 7. ShoppingPlanner.tsx (1229 lines) → 5 components

**Current:** List view, item details, wizard, comparison all mixed.

**New Structure:**
```
frontend/src/pages/shopping/
├── index.tsx                # Main page container
├── ShoppingListView.tsx     # List display
├── ItemEditor.tsx           # Item quantity/region editing
├── RegionComparison.tsx     # Price comparison table
├── ExportPanel.tsx          # Export to EVE format
└── hooks/
    └── useShoppingList.ts   # List state management
```

---

## Execution Order

1. **Backend first** (dependencies flow downstream):
   - `reports_service.py` → `war_economy.py` etc.
   - `live_service.py` → `battle_tracker.py` etc.
   - `routers/war.py` → split routers
   - `shopping_service.py` → split modules

2. **Frontend second**:
   - `SystemDetail.tsx` → components
   - `StarMap.tsx` → components
   - `ShoppingPlanner.tsx` → components

## Backwards Compatibility

All refactored modules will re-export from `__init__.py` to maintain existing imports:

```python
# services/zkillboard/reports/__init__.py
from .pilot_intelligence import PilotIntelligenceReport
from .war_profiteering import WarProfiteeringReport
# ... etc

# For backwards compat:
class ZKillboardReportsService:
    """Facade that delegates to individual report classes"""
    pass
```

## Testing

After each file refactor:
1. Run existing tests
2. Verify API responses unchanged
3. Check frontend still loads

---

## Status

- [x] reports_service.py ✅ COMPLETE (8 modules: base, kill_analysis, pilot_intelligence, war_profiteering, trade_routes, war_economy, alliance_wars, __init__)
- [x] live_service.py ✅ COMPLETE (7 modules: models, ship_classifier, killmail_processor, battle_tracker, telegram_alerts, redis_cache, statistics)
- [x] routers/war.py ✅ COMPLETE (7 modules: dependencies, battles, systems, analysis, live, fw_sov, map)
- [x] shopping_service.py ✅ COMPLETE (6 modules: lists, items, volumes, bulk, materials, wizard)
- [x] SystemDetail.tsx ✅ COMPLETE (14 components: types, StarDetail, StargateDetail, StationDetail, CelestialStats, PlanetDetail, MoonDetail, AsteroidBeltDetail, SystemHeader, ObjectCounts, HoverTooltip, ListPanel, index)
- [ ] ~~StarMap.tsx~~ - NOT DELETED (actively used by ectmap as main component)
- [x] ShoppingPlanner.tsx ✅ COMPLETE (7 components + 1 hook: ListsSidebar, ListHeader, ProductsSection, AddProductModal, ShoppingListTable, SubProductModal, index + useShoppingMutations)

### reports_service.py Progress ✅ COMPLETE

| Module | Status | Lines |
|--------|--------|-------|
| `base.py` | ✅ Complete | ~250 |
| `kill_analysis.py` | ✅ Complete | ~300 |
| `pilot_intelligence.py` | ✅ Complete | ~180 |
| `war_profiteering.py` | ✅ Complete | ~120 |
| `__init__.py` | ✅ Complete | ~60 |
| `alliance_wars.py` | ✅ Complete | ~400 |
| `trade_routes.py` | ✅ Complete | ~200 |
| `war_economy.py` | ✅ Complete | ~400 |

**Total: 8 modules created, ~1910 lines extracted from 2516 line monolith**

Note: Original `reports_service.py` is kept for backwards compatibility.
Mixins are ready to be composed into a new service class when needed.

### live_service.py Progress ✅ COMPLETE

| Module | Status | Lines |
|--------|--------|-------|
| `models.py` | ✅ Complete | ~50 |
| `ship_classifier.py` | ✅ Complete | ~210 |
| `killmail_processor.py` | ✅ Complete | ~320 |
| `battle_tracker.py` | ✅ Complete | ~280 |
| `telegram_alerts.py` | ✅ Complete | ~250 |
| `redis_cache.py` | ✅ Complete | ~210 |
| `statistics.py` | ✅ Complete | ~430 |
| `__init__.py` | ✅ Complete | ~80 |

**Total: 8 modules created, ~1830 lines extracted from 2358 line monolith**

Note: Original `live_service.py` is kept for backwards compatibility.
Mixins are ready to be composed into a new service class when needed.

### shopping_service.py Progress ✅ COMPLETE

| Module | Status | Lines |
|--------|--------|-------|
| `lists.py` | ✅ Complete | ~190 |
| `items.py` | ✅ Complete | ~190 |
| `volumes.py` | ✅ Complete | ~230 |
| `bulk.py` | ✅ Complete | ~110 |
| `materials.py` | ✅ Complete | ~270 |
| `wizard.py` | ✅ Complete | ~220 |
| `__init__.py` | ✅ Complete | ~65 |

**Total: 7 modules created, ~1275 lines extracted from 1357 line monolith**

Note: Original `shopping_service.py` is kept for backwards compatibility.
Mixins composed into ShoppingService class via `src/shopping/__init__.py`.

### SystemDetail.tsx Progress ✅ COMPLETE

| Component | Status | Lines |
|-----------|--------|-------|
| `types.ts` | ✅ Complete | ~15 |
| `details/StarDetail.tsx` | ✅ Complete | ~95 |
| `details/StargateDetail.tsx` | ✅ Complete | ~75 |
| `details/StationDetail.tsx` | ✅ Complete | ~105 |
| `details/CelestialStats.tsx` | ✅ Complete | ~65 |
| `details/PlanetDetail.tsx` | ✅ Complete | ~195 |
| `details/MoonDetail.tsx` | ✅ Complete | ~75 |
| `details/AsteroidBeltDetail.tsx` | ✅ Complete | ~65 |
| `details/index.ts` | ✅ Complete | ~10 |
| `SystemHeader.tsx` | ✅ Complete | ~55 |
| `ObjectCounts.tsx` | ✅ Complete | ~65 |
| `HoverTooltip.tsx` | ✅ Complete | ~25 |
| `ListPanel.tsx` | ✅ Complete | ~50 |
| `index.tsx` | ✅ Complete | ~880 |

**Total: 14 components created, 2085 line monolith split into modular structure**

Note: Original `SystemDetail.tsx` now re-exports from `./system-detail/` for backwards compatibility.

### ShoppingPlanner.tsx Progress ✅ COMPLETE

| Component | Status | Lines |
|-----------|--------|-------|
| `planner/ListsSidebar.tsx` | ✅ Complete | ~100 |
| `planner/ListHeader.tsx` | ✅ Complete | ~115 |
| `planner/ProductsSection.tsx` | ✅ Complete | ~300 |
| `planner/AddProductModal.tsx` | ✅ Complete | ~170 |
| `planner/ShoppingListTable.tsx` | ✅ Complete | ~115 |
| `planner/SubProductModal.tsx` | ✅ Complete | ~130 |
| `planner/index.ts` | ✅ Complete | ~20 |
| `hooks/useShoppingMutations.ts` | ✅ Complete | ~175 |

**Total: 7 new components + 1 hook, reduced ShoppingPlanner.tsx from 1229 lines to ~345 lines**

Note: ShoppingPlanner.tsx now uses extracted components and hooks for cleaner architecture.
