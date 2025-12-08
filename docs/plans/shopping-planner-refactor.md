# Shopping Planner Refactoring Plan

## Problem Analysis

### Current State
- **File Size**: 2,726 lines (4.6x larger than next largest file)
- **React Hooks**: 45+ hooks in single component
- **TypeScript Errors**: 9 compilation errors
- **Responsibilities**: 10+ distinct concerns in one file
- **API Calls**: Inline API calls throughout (not abstracted)

### Issues
1. **Maintainability**: Too large to understand and modify safely
2. **Testing**: Impossible to test individual concerns
3. **Performance**: Excessive re-renders due to shared state
4. **Reusability**: Components locked inside main file
5. **Type Safety**: Missing null checks, undefined references
6. **Code Duplication**: Similar logic to ShoppingWizard but reimplemented

### TypeScript Errors
```
Line 2360, 2380, 2592: Cannot find name 'setShowCompareModal'
Line 2401-2403, 2440, 2584-2585: 'comparison' is possibly 'undefined'
```

## Current Component Structure

```
ShoppingPlanner.tsx (2726 lines)
├── Types (17 interfaces, 90 lines)
├── Constants (REGION_NAMES, REGION_ORDER, etc.)
├── OrderDetailsPopup (127 lines)
├── ShoppingRouteDisplay (290 lines)
├── SubProductTree (145 lines)
└── ShoppingPlanner (2074 lines)
    ├── State Management (45+ hooks)
    ├── List Management View
    ├── Compare Prices View
    └── Transport View
```

## Existing Patterns to Follow

### 1. Component Organization
```
components/shopping/
├── ShoppingWizard.tsx (main orchestrator)
├── ProductDefinitionStep.tsx
├── SubComponentsStep.tsx
├── ShoppingListStep.tsx
├── RegionalComparisonStep.tsx
├── types.ts (shared types)
└── index.ts (exports)
```

### 2. API Layer
```typescript
// War Room pattern from api.ts
export async function getWarDemand(regionId: number, days = 7) {
  const response = await api.get(`/api/war/demand/${regionId}`, { params: { days } });
  return response.data;
}
```

### 3. Component Size
- WarRoom.tsx: 594 lines (good reference)
- ItemDetail.tsx: 455 lines
- MarketScanner.tsx: 587 lines

**Target**: <400 lines per component

## Refactoring Strategy

### Phase 1: Fix TypeScript Errors (Quick Win)
**Priority**: CRITICAL
**Time**: 15 minutes
**Risk**: LOW

1. Remove `setShowCompareModal` references (dead code)
2. Add null checks for `comparison` variable
3. Verify build passes

### Phase 2: Extract API Functions
**Priority**: HIGH
**Time**: 30 minutes
**Risk**: LOW

Create `frontend/src/api/shopping.ts`:
```typescript
// Shopping List CRUD
export async function getShoppingLists()
export async function getShoppingList(listId: number)
export async function createShoppingList(name: string)
export async function deleteShoppingList(listId: number)

// Item Management
export async function addShoppingItem(listId: number, item: ShoppingItemInput)
export async function updateShoppingItem(itemId: number, updates: Partial<ShoppingItem>)
export async function removeShoppingItem(itemId: number)
export async function markItemPurchased(itemId: number)

// Price Comparison
export async function getRegionalComparison(listId: number)
export async function updateItemRegion(itemId: number, region: string, price?: number)

// Materials & Production
export async function calculateMaterials(typeId: number, runs: number, me: number)
export async function addProductionMaterials(listId: number, materials: Material[])

// Transport
export async function getCargoSummary(listId: number)
export async function getTransportOptions(listId: number)
export async function getShoppingRoute(params: RouteParams)

// Orders
export async function getOrderSnapshot(typeId: number, region: string)
```

Update imports in ShoppingPlanner to use these functions.

### Phase 3: Extract Types
**Priority**: HIGH
**Time**: 15 minutes
**Risk**: LOW

Create `frontend/src/types/shopping.ts`:
- Move all interfaces from ShoppingPlanner.tsx
- Consolidate with types from `components/shopping/types.ts`
- Export from single source of truth

### Phase 4: Extract Hooks
**Priority**: MEDIUM
**Time**: 45 minutes
**Risk**: MEDIUM

Create `frontend/src/hooks/shopping/`:

```
useShoppingLists.ts       - List CRUD operations
useShoppingItems.ts       - Item management
useRegionalComparison.ts  - Price comparison logic
useMaterialCalculation.ts - Production materials
useTransportPlanning.ts   - Cargo & routing
```

Example:
```typescript
// hooks/shopping/useShoppingLists.ts
export function useShoppingLists() {
  const queryClient = useQueryClient();

  const lists = useQuery({
    queryKey: ['shopping-lists'],
    queryFn: getShoppingLists
  });

  const createList = useMutation({
    mutationFn: createShoppingList,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    }
  });

  const deleteList = useMutation({
    mutationFn: deleteShoppingList,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-lists'] });
    }
  });

  return { lists, createList, deleteList };
}
```

### Phase 5: Extract View Components
**Priority**: MEDIUM
**Time**: 60 minutes
**Risk**: MEDIUM

Create `frontend/src/components/shopping/planner/`:

```
ShoppingListsView.tsx     - List management & selection (300 lines)
ComparisonView.tsx        - Regional price comparison (400 lines)
TransportView.tsx         - Cargo & transport planning (200 lines)
OrderDetailsModal.tsx     - Order snapshots popup (150 lines)
RouteDisplay.tsx          - Route visualization (250 lines)
ProductTree.tsx           - Sub-product tree (150 lines)
```

Each view component:
- Receives data via props
- Uses extracted hooks
- Handles only its view logic
- <400 lines

### Phase 6: Refactor Main Component
**Priority**: MEDIUM
**Time**: 30 minutes
**Risk**: LOW

ShoppingPlanner.tsx (target: <300 lines):
```typescript
export default function ShoppingPlanner() {
  // View mode state
  const [viewMode, setViewMode] = useState<'list' | 'compare' | 'transport'>('list');
  const [selectedListId, setSelectedListId] = useState<number | null>(null);

  // Use extracted hooks
  const { lists, createList, deleteList } = useShoppingLists();
  const items = useShoppingItems(selectedListId);
  const comparison = useRegionalComparison(selectedListId, viewMode === 'compare');
  const transport = useTransportPlanning(selectedListId, viewMode === 'transport');

  return (
    <div className="page-container">
      <ShoppingPlannerHeader
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onCreateList={createList.mutate}
      />

      {viewMode === 'list' && (
        <ShoppingListsView
          lists={lists.data}
          selectedListId={selectedListId}
          onSelectList={setSelectedListId}
          onDeleteList={deleteList.mutate}
        />
      )}

      {viewMode === 'compare' && selectedListId && (
        <ComparisonView
          listId={selectedListId}
          comparison={comparison.data}
          isLoading={comparison.isLoading}
        />
      )}

      {viewMode === 'transport' && selectedListId && (
        <TransportView
          listId={selectedListId}
          options={transport.data}
          isLoading={transport.isLoading}
        />
      )}
    </div>
  );
}
```

## File Structure After Refactoring

```
frontend/src/
├── api/
│   └── shopping.ts (NEW - 200 lines)
├── types/
│   └── shopping.ts (NEW - 150 lines)
├── hooks/
│   └── shopping/
│       ├── useShoppingLists.ts (NEW - 80 lines)
│       ├── useShoppingItems.ts (NEW - 100 lines)
│       ├── useRegionalComparison.ts (NEW - 80 lines)
│       ├── useMaterialCalculation.ts (NEW - 60 lines)
│       └── useTransportPlanning.ts (NEW - 60 lines)
├── components/
│   └── shopping/
│       ├── planner/
│       │   ├── ShoppingListsView.tsx (NEW - 300 lines)
│       │   ├── ComparisonView.tsx (NEW - 400 lines)
│       │   ├── TransportView.tsx (NEW - 200 lines)
│       │   ├── OrderDetailsModal.tsx (NEW - 150 lines)
│       │   ├── RouteDisplay.tsx (NEW - 250 lines)
│       │   └── ProductTree.tsx (NEW - 150 lines)
│       ├── wizard/ (EXISTING)
│       │   ├── ShoppingWizard.tsx
│       │   ├── ProductDefinitionStep.tsx
│       │   ├── SubComponentsStep.tsx
│       │   ├── ShoppingListStep.tsx
│       │   └── RegionalComparisonStep.tsx
│       └── types.ts (MERGE into types/shopping.ts)
└── pages/
    └── ShoppingPlanner.tsx (REFACTORED - <300 lines)
```

## Implementation Order

### Sprint 1: Critical Fixes & Foundation (2 hours)
1. ✅ Phase 1: Fix TypeScript errors
2. ✅ Phase 2: Extract API functions
3. ✅ Phase 3: Extract and consolidate types

### Sprint 2: Logic Extraction (3 hours)
4. ⏳ Phase 4: Extract hooks
5. ⏳ Phase 5: Extract view components (ListView first)

### Sprint 3: Completion (2 hours)
6. ⏳ Phase 5 continued: Extract remaining views
7. ⏳ Phase 6: Refactor main component
8. ⏳ Testing & validation

## Testing Strategy

### After Each Phase
1. Run TypeScript compiler: `npm run build`
2. Check dev server: `npm run dev`
3. Manual testing of affected features
4. Verify no console errors

### Critical Test Paths
1. Create/delete shopping list
2. Add/remove items
3. Regional price comparison
4. Apply optimal/regional selections
5. Transport planning
6. Order snapshots
7. Material calculation with sub-products

## Rollback Strategy

Each phase is independent:
- Phase 1-3: Low risk, easy rollback via git
- Phase 4: Hooks can be reverted individually
- Phase 5-6: Can keep old file as backup temporarily

## Benefits

### Immediate
- ✅ TypeScript compilation passes
- ✅ Reduced file size (2726 → 8 files <400 lines each)
- ✅ Clear separation of concerns

### Long-term
- ✅ Easier maintenance and debugging
- ✅ Testable units
- ✅ Reusable hooks and components
- ✅ Better performance (selective re-renders)
- ✅ Onboarding new developers

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Breaking existing functionality | HIGH | MEDIUM | Thorough testing after each phase |
| Missed TypeScript errors | MEDIUM | LOW | Run `npm run build` frequently |
| State management bugs | HIGH | MEDIUM | Keep optimistic updates pattern |
| Performance regression | MEDIUM | LOW | Monitor React DevTools |

## Open Questions

1. **Integration with ShoppingWizard**: Should wizard create lists directly or remain separate?
2. **Shared components**: Can OrderDetailsModal be used by both Planner and Wizard?
3. **Type consolidation**: Single types file or split by domain (lists, items, routes)?

## Success Criteria

- [ ] All TypeScript errors resolved
- [ ] Build passes without warnings
- [ ] All features work as before
- [ ] No new console errors
- [ ] Main component <300 lines
- [ ] All sub-components <400 lines
- [ ] API functions centralized
- [ ] Hooks reusable across components
