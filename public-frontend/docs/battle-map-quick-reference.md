# Battle Map - Quick Reference Card

## Component Location
```
/src/pages/BattleMap.tsx (902 lines)
Route: /battle-map
```

## Build & Run
```bash
# Development
cd /home/cytrex/eve_copilot/public-frontend
npm run dev -- --host 0.0.0.0

# Production Build
npm run build

# Type Check
npm run build  # TypeScript is checked during build
```

## Key Features at a Glance

| Feature | Details |
|---------|---------|
| **Filters** | 4 types: Hot Zones, Capital Kills, Danger Zones, High-Value |
| **Default Filter** | Hot Zones (enabled by default) |
| **Layout** | 3-panel: Filters (280px) + Map (flex) + Info (320px) |
| **Data Source** | `/api/reports/battle-24h` |
| **Map Library** | `eve-map-3d` v2.0.2 |
| **Type Safety** | 100% TypeScript |

## Color Codes

| Filter | Color | Hex | Priority |
|--------|-------|-----|----------|
| Capital Kills | Purple | `#bc8cff` | 1 (Highest) |
| Hot Zones (Top 3) | Red | `#ff4444` | 2 |
| Hot Zones (Others) | Orange | `#ff9944` | 2 |
| High-Value Kills | Cyan | `#00d9ff` | 3 |
| Danger Zones | Yellow | `#d29922` | 4 (Lowest) |

## State Variables (10)

```typescript
// Map Data
const [systems, setSystems] = useState<SolarSystem[]>([]);
const [stargates, setStargates] = useState<Stargate[]>([]);
const [regions, setRegions] = useState<Region[]>([]);
const [mapLoading, setMapLoading] = useState(true);
const [mapError, setMapError] = useState<string | null>(null);

// Battle Report
const [battleReport, setBattleReport] = useState<BattleReport | null>(null);
const [reportLoading, setReportLoading] = useState(true);
const [reportError, setReportError] = useState<string | null>(null);

// UI
const [filters, setFilters] = useState({...});
const [selectedSystem, setSelectedSystem] = useState<...>(null);
```

## Computed Values (useMemo)

```typescript
// O(1) lookup maps
const systemLookups = useMemo(() => ({
  hotZoneMap: Map<systemId, HotZone>,
  capitalKillsMap: Map<systemId, count>,
  dangerZoneMap: Map<systemId, DangerZone>,
  highValueKillsMap: Map<systemId, HighValueKill[]>
}), [battleReport, systems]);

// Visual configuration
const systemRenderConfigs = useMemo(() => [...], [filters, systemLookups]);

// Filter counts
const filterCounts = useMemo(() => ({...}), [battleReport, systemLookups]);
```

## Event Handlers

```typescript
// System click
onSystemClick: (system: SolarSystem) => {
  handleSystemClick(system._key);
}

// Filter toggle
toggleFilter(filterName: keyof typeof filters)

// Close info panel
onClick={() => setSelectedSystem(null)}
```

## Important Type Patterns

```typescript
// System ID
system._key  // Use _key, NOT id

// System Name
const name = typeof system.name === 'string'
  ? system.name
  : system.name['en'] || system.name['zh'] || 'Unknown';

// Security Status
system.securityStatus  // NOT system.security

// Region ID
system.regionID  // NOT system.region
```

## API Response Structure

```typescript
BattleReport {
  period: string;
  global: {
    total_kills: number;
    total_isk_destroyed: number;
    peak_hour_utc: number;
  };
  hot_zones: HotZone[];
  capital_kills: {
    titans: { count, kills[] },
    supercarriers: { count, kills[] },
    carriers: { count, kills[] },
    dreadnoughts: { count, kills[] },
    force_auxiliaries: { count, kills[] }
  };
  danger_zones: DangerZone[];
  high_value_kills: HighValueKill[];
}
```

## Common Tasks

### Add New Filter
1. Add to `filters` state object
2. Add to `filterCounts` calculation
3. Add checkbox to sidebar JSX
4. Add to `systemRenderConfigs` logic
5. Add to info panel display

### Change Filter Colors
1. Update color in `systemRenderConfigs` (line ~220-245)
2. Update color in filter checkbox UI (line ~365-560)
3. Update color in info panel cards (line ~690-855)

### Modify System Info Panel
1. Find `{selectedSystem && (` section (line ~635)
2. Add/modify cards in combat data sections
3. Update data structure in `selectedSystem` state

## Performance Tips

✅ Use Map for O(1) lookups (not Array.find)
✅ useMemo for expensive calculations
✅ Minimal dependencies in useEffect
✅ Lazy evaluation of names (only when needed)

## Common Issues & Solutions

### Issue: Systems not highlighting
**Solution:** Check `systemRenderConfigs` is being passed to `mapControl.setConfig()`

### Issue: Wrong system name format
**Solution:** Use name extraction pattern:
```typescript
typeof system.name === 'string' ? system.name : system.name['en']
```

### Issue: Info panel not showing
**Solution:** Check `selectedSystem` state is being set correctly in `handleSystemClick`

### Issue: Filter counts wrong
**Solution:** Verify system name-to-ID mapping in `systemLookups` memo

## Documentation Files

```
/docs/battle-map-implementation.md  - Full technical documentation
/docs/battle-map-layout.txt         - Visual layout diagram
/docs/battle-map-summary.md         - Executive summary
/docs/battle-map-quick-reference.md - This file
```

## Testing Commands

```bash
# Type check
npm run build

# Dev server
npm run dev

# Production build
npm run build

# Check for errors
npm run build 2>&1 | grep -i error
```

## Useful Grep Commands

```bash
# Find all state variables
grep "useState" src/pages/BattleMap.tsx

# Find all effects
grep "useEffect" src/pages/BattleMap.tsx

# Find color definitions
grep "#[a-f0-9]\{6\}" src/pages/BattleMap.tsx

# Count lines by section
grep -n "Left Sidebar\|Main Map\|Right Sidebar" src/pages/BattleMap.tsx
```

## Quick Metrics

| Metric | Value |
|--------|-------|
| Total Lines | 902 |
| React Hooks | 17 |
| State Variables | 10 |
| useMemo Hooks | 3 |
| useEffect Hooks | 4 |
| Event Handlers | 3 |
| Build Size | 1.45 MB (416 KB gzipped) |
| TypeScript | 100% |
| Build Time | ~6-7 seconds |

## Status Checklist

- [x] TypeScript compilation
- [x] Production build
- [x] Dev server startup
- [x] Type safety validation
- [x] Documentation complete
- [ ] Manual testing
- [ ] Performance benchmarking
- [ ] User acceptance testing

---

**Last Updated:** 2026-01-06
**Status:** ✅ Ready for Testing
**Next:** Manual QA with live API data
