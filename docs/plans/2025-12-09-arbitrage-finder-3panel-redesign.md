# Arbitrage Finder 3-Panel Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign Arbitrage Finder with a clear 3-panel layout (Market Groups | Items Table | Arbitrage Details) similar to Shopping Planner, removing confusing dropdown UX and providing consistent, intuitive navigation.

**Architecture:** Left sidebar shows market group tree (450px), center panel displays items in selected group as a table with search filter, right panel shows arbitrage opportunities when an item is selected. No dropdowns - everything visible and clickable.

**Tech Stack:** React, TypeScript, @tanstack/react-query, Vite, existing API endpoints

---

## Context

**Current Problems:**
- Items appear/disappear in dropdown unpredictably
- Unclear when to search vs when items auto-load
- Inconsistent with Shopping Planner UX (which has clear 3-panel layout)
- User can't see overview of items in a group

**New UX Flow:**
1. User clicks market group → Items table populates with all items in that group
2. User can search/filter within items table
3. User clicks item row → Arbitrage details panel shows opportunities for that item
4. Clear visual hierarchy like Shopping Planner

**Reference Files:**
- Current: `frontend/src/pages/ArbitrageFinder.tsx`
- Pattern: `frontend/src/pages/ShoppingPlanner.tsx` (3-panel layout reference)

---

## Task 1: Create Items Table Component

**Files:**
- Create: `frontend/src/components/arbitrage/ItemsTable.tsx`

**Step 1: Create component file with TypeScript interface**

```typescript
// frontend/src/components/arbitrage/ItemsTable.tsx
import { useState, useMemo } from 'react';
import { Search, Package } from 'lucide-react';

interface Item {
  typeID: number;
  typeName: string;
  groupID: number;
  volume: number | null;
  basePrice: number | null;
}

interface ItemsTableProps {
  items: Item[];
  selectedItemId: number | null;
  onSelectItem: (item: Item) => void;
  groupName: string;
  isLoading?: boolean;
}

export function ItemsTable({
  items,
  selectedItemId,
  onSelectItem,
  groupName,
  isLoading = false
}: ItemsTableProps) {
  const [searchQuery, setSearchQuery] = useState('');

  // Filter items based on search query
  const filteredItems = useMemo(() => {
    if (!searchQuery) return items;
    const query = searchQuery.toLowerCase();
    return items.filter(item =>
      item.typeName.toLowerCase().includes(query)
    );
  }, [items, searchQuery]);

  if (isLoading) {
    return (
      <div className="card" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="loading">Loading items...</div>
      </div>
    );
  }

  return (
    <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '1rem', borderBottom: '1px solid var(--border)' }}>
        <h3 style={{ margin: 0, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Package size={20} />
          Items in {groupName}
        </h3>

        {/* Search Filter */}
        <div style={{ position: 'relative' }}>
          <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Filter items..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ paddingLeft: '2.5rem', width: '100%' }}
          />
        </div>
      </div>

      {/* Items Table */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {filteredItems.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            {searchQuery ? 'No items match your search' : 'No items in this group'}
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Item Name</th>
                <th>Volume</th>
                <th>Base Price</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map(item => (
                <tr
                  key={item.typeID}
                  onClick={() => onSelectItem(item)}
                  className={selectedItemId === item.typeID ? 'selected' : ''}
                  style={{ cursor: 'pointer' }}
                >
                  <td><strong>{item.typeName}</strong></td>
                  <td>{item.volume ? `${item.volume.toLocaleString()} m³` : 'N/A'}</td>
                  <td>{item.basePrice ? `${item.basePrice.toLocaleString()} ISK` : 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Footer with count */}
      <div style={{ padding: '0.75rem', borderTop: '1px solid var(--border)', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
        Showing {filteredItems.length} of {items.length} items
      </div>
    </div>
  );
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd frontend && npm run build`
Expected: No TypeScript errors

**Step 3: Commit**

```bash
git add frontend/src/components/arbitrage/ItemsTable.tsx
git commit -m "feat: add ItemsTable component for arbitrage finder

- Create reusable items table with search filter
- Support row selection and onClick handler
- Show item name, volume, base price
- Display item count in footer
- Loading and empty states"
```

---

## Task 2: Refactor ArbitrageFinder to Use 3-Panel Layout

**Files:**
- Modify: `frontend/src/pages/ArbitrageFinder.tsx`

**Step 1: Import ItemsTable component**

At top of `ArbitrageFinder.tsx`, add:

```typescript
import { ItemsTable } from '../components/arbitrage/ItemsTable';
```

**Step 2: Update state management**

Replace the current state section (around line 165-173) with:

```typescript
export default function ArbitrageFinder() {
  // Selected item state (replaces searchQuery + selectedItem)
  const [selectedItem, setSelectedItem] = useState<{ typeID: number; typeName: string; groupID: number; volume: number | null; basePrice: number | null } | null>(null);
  const [minProfit, setMinProfit] = useState(5);
  const [shipType, setShipType] = useState('industrial');

  // Market Group Tree state
  const [selectedGroup, setSelectedGroup] = useState<{ id: number | null; name: string; path: string[]; isLeaf: boolean } | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({});
```

**Step 3: Update queries to load items for selected group**

Replace the `groupItems` and `searchResults` queries (around line 184-211) with single query:

```typescript
  // Load all items for selected group
  const { data: groupItems, isLoading: isLoadingItems } = useQuery({
    queryKey: ['groupItems', selectedGroup?.id],
    queryFn: async () => {
      const response = await api.get('/api/items/search', {
        params: {
          q: '',
          group_id: selectedGroup!.id,
        },
      });
      return response.data.results;
    },
    enabled: !!selectedGroup?.id,
  });
```

**Step 4: Update arbitrage query to use selectedItem**

Replace line 217-219 with:

```typescript
  // Get enhanced arbitrage opportunities
  const { data: arbitrageData, isLoading, error } = useQuery<EnhancedArbitrageResponse>({
    queryKey: ['enhancedArbitrage', selectedItem?.typeID, minProfit, shipType],
    queryFn: () => getEnhancedArbitrage(selectedItem!.typeID, minProfit, shipType),
    enabled: !!selectedItem,
  });
```

**Step 5: Update layout JSX to 3-panel design**

Replace the main return JSX (from around line 220 to end) with:

```typescript
  return (
    <div>
      <h1>Arbitrage Finder</h1>
      <p className="subtitle">Find profitable trading opportunities across regions with route planning and cargo optimization</p>

      <div style={{ display: 'flex', gap: '1rem', height: 'calc(100vh - 200px)' }}>
        {/* Left Panel: Market Groups Tree */}
        <div className="card" style={{ width: 450, overflowY: 'auto', flexShrink: 0 }}>
          <h3 style={{ margin: 0, marginBottom: '1rem' }}>Market Groups</h3>
          {marketTree && (
            <div>
              {Object.entries(marketTree.tree).map(([name, node]) => (
                <TreeNode
                  key={name}
                  name={name}
                  node={node}
                  level={0}
                  expanded={expandedNodes}
                  selected={selectedGroup}
                  onToggle={(path) => {
                    setExpandedNodes(prev => ({
                      ...prev,
                      [path]: !prev[path]
                    }));
                  }}
                  onSelect={(id, name, path, isLeaf) => {
                    setSelectedGroup({ id, name, path, isLeaf });
                    setSelectedItem(null); // Clear selected item when changing group
                  }}
                  path={[]}
                />
              ))}
            </div>
          )}
        </div>

        {/* Center Panel: Items Table */}
        {selectedGroup ? (
          <ItemsTable
            items={groupItems || []}
            selectedItemId={selectedItem?.typeID || null}
            onSelectItem={setSelectedItem}
            groupName={selectedGroup.path.join(' > ')}
            isLoading={isLoadingItems}
          />
        ) : (
          <div className="card" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
              <Package size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
              <p>Select a market group to view items</p>
            </div>
          </div>
        )}

        {/* Right Panel: Arbitrage Details */}
        {selectedItem ? (
          <div className="card" style={{ flex: 1.5, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ padding: '1rem', borderBottom: '1px solid var(--border)' }}>
              <h3 style={{ margin: 0, marginBottom: '1rem' }}>
                Arbitrage Opportunities: {selectedItem.typeName}
              </h3>

              {/* Ship Type and Min Profit Controls */}
              <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <label>Ship Type:</label>
                  <select
                    value={shipType}
                    onChange={(e) => setShipType(e.target.value)}
                    style={{ width: '100%' }}
                  >
                    {SHIP_TYPES.map(ship => (
                      <option key={ship.value} value={ship.value}>
                        {ship.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label>Min Profit per Unit:</label>
                  <input
                    type="number"
                    value={minProfit}
                    onChange={(e) => setMinProfit(Number(e.target.value))}
                    min="0"
                    step="1"
                    style={{ width: '100%' }}
                  />
                </div>
              </div>

              {/* Item Info */}
              {arbitrageData && (
                <div style={{ display: 'flex', gap: '2rem', padding: '1rem', background: 'var(--background-alt)', borderRadius: '4px' }}>
                  <div>
                    <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Item Volume</div>
                    <div><strong>{formatVolume(arbitrageData.item_volume)}</strong></div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Ship Capacity</div>
                    <div><strong>{formatVolume(arbitrageData.ship_capacity)}</strong></div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Opportunities Found</div>
                    <div><strong>{arbitrageData.opportunities.length}</strong></div>
                  </div>
                </div>
              )}
            </div>

            {/* Opportunities Table */}
            <div style={{ flex: 1, overflow: 'auto' }}>
              {isLoading ? (
                <div style={{ padding: '2rem', textAlign: 'center' }}>
                  <div className="loading">Loading arbitrage opportunities...</div>
                </div>
              ) : error ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--negative)' }}>
                  Error loading opportunities: {(error as Error).message}
                </div>
              ) : arbitrageData && arbitrageData.opportunities.length > 0 ? (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Route</th>
                      <th>Safety</th>
                      <th>Jumps</th>
                      <th>Time</th>
                      <th>Units/Trip</th>
                      <th>Profit/Trip</th>
                      <th>Net Profit</th>
                      <th>ISK/m³</th>
                      <th>Profit/Hour</th>
                      <th>ROI</th>
                    </tr>
                  </thead>
                  <tbody>
                    {arbitrageData.opportunities.map((opp, idx) => {
                      const buyRegion = REGION_NAMES[opp.buy_region] || opp.buy_region;
                      const sellRegion = REGION_NAMES[opp.sell_region] || opp.sell_region;

                      return (
                        <tr key={idx}>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <span>{buyRegion}</span>
                              <ArrowRight size={14} />
                              <span>{sellRegion}</span>
                            </div>
                          </td>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              {getSafetyIcon(opp.route.safety)}
                              {getSafetyBadge(opp.route.safety)}
                            </div>
                          </td>
                          <td>{opp.route.jumps}</td>
                          <td>{opp.route.time_minutes} min</td>
                          <td>{opp.cargo.units_per_trip.toLocaleString()}</td>
                          <td className="positive">{formatISK(opp.cargo.gross_profit_per_trip)}</td>
                          <td><strong className="positive">{formatISK(opp.profitability.net_profit)}</strong></td>
                          <td>{formatISK(opp.cargo.isk_per_m3)}</td>
                          <td className="positive">{formatISK(opp.profitability.profit_per_hour)}</td>
                          <td className="positive">{opp.profitability.roi_percent.toFixed(1)}%</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <TrendingUp size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                  <p>No profitable arbitrage opportunities found</p>
                  <p style={{ fontSize: '0.875rem' }}>Try adjusting the minimum profit or ship type</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="card" style={{ flex: 1.5, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
              <TrendingUp size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
              <p>Select an item to view arbitrage opportunities</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

**Step 6: Verify TypeScript compiles**

Run: `cd frontend && npm run build`
Expected: No TypeScript errors

**Step 7: Test in browser**

1. Open `http://localhost:3000` (or your dev server URL)
2. Navigate to Arbitrage Finder
3. Click a market group → Items table should populate
4. Type in search box → Items should filter
5. Click an item row → Arbitrage details should show
6. Change ship type/min profit → Data should update

Expected: All interactions work smoothly, no console errors

**Step 8: Commit**

```bash
git add frontend/src/pages/ArbitrageFinder.tsx
git commit -m "refactor: redesign ArbitrageFinder with 3-panel layout

- Remove confusing dropdown UX
- Add clear 3-panel layout: Groups | Items | Details
- Items table shows all items in selected group
- Click item to view arbitrage opportunities
- Consistent with Shopping Planner UX
- Simplified state management (no more searchQuery)
- Better visual hierarchy and information density"
```

---

## Task 3: Add CSS Styles for Selected Row State

**Files:**
- Modify: `frontend/src/App.css` (or appropriate stylesheet)

**Step 1: Add selected row style**

Add to CSS file:

```css
/* Selected table row styling */
.data-table tbody tr.selected {
  background-color: var(--primary-alpha-10);
  border-left: 3px solid var(--primary);
}

.data-table tbody tr.selected:hover {
  background-color: var(--primary-alpha-20);
}
```

**Step 2: Verify styles apply**

1. Open browser dev tools
2. Select an item row
3. Verify `.selected` class is applied
4. Verify blue left border and background color appear

Expected: Selected row has visual highlight

**Step 3: Commit**

```bash
git add frontend/src/App.css
git commit -m "style: add selected row highlighting for items table

- Add .selected class styling with primary color
- Show left border to indicate selection
- Subtle background color change
- Hover state for selected rows"
```

---

## Task 4: Add Empty State When No Group Selected

**Files:**
- Already implemented in Task 2, Step 5

**Verification:**

1. Open Arbitrage Finder
2. Verify center and right panels show empty states with icons and messages
3. Click a group → Center panel populates with items
4. Click an item → Right panel shows arbitrage data

Expected: Clear guidance for user at each step

---

## Task 5: Remove Old Dropdown/Search Code

**Files:**
- Modify: `frontend/src/pages/ArbitrageFinder.tsx`

**Step 1: Remove unused interfaces**

Delete `SearchResult` interface (if not used elsewhere):

```typescript
// DELETE THIS:
interface SearchResult {
  typeID: number;
  typeName: string;
}
```

**Step 2: Remove unused state**

Verify no references to:
- `searchQuery`
- `setSearchQuery`
- `showResults`
- `setShowResults`
- `displayResults`

**Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: No TypeScript errors, no unused variable warnings

**Step 4: Commit**

```bash
git add frontend/src/pages/ArbitrageFinder.tsx
git commit -m "refactor: remove old dropdown search code

- Remove SearchResult interface (unused)
- Remove searchQuery state (moved to ItemsTable)
- Clean up unused imports
- Simplify component logic"
```

---

## Task 6: Update README/Documentation

**Files:**
- Modify: `docs/session-summary-2025-12-09-arbitrage-enhancement.md` (or create new)

**Step 1: Document UX redesign**

Add section to session summary:

```markdown
## Phase 2: UX Redesign - 3-Panel Layout ✅ COMPLETE

**Problem:** Confusing dropdown UX, items appeared/disappeared unpredictably

**Solution:** Redesigned with clear 3-panel layout consistent with Shopping Planner:
- Left: Market Groups tree (450px)
- Center: Items table with search filter
- Right: Arbitrage opportunities for selected item

**Changes:**
- Created `ItemsTable.tsx` component
- Refactored `ArbitrageFinder.tsx` to use 3-panel layout
- Removed dropdown search UX
- Added selected row highlighting
- Clear empty states with guidance

**User Flow:**
1. Click market group → Items table populates
2. Search/filter items if needed
3. Click item row → Arbitrage details show
4. Adjust ship type/min profit → Results update

**Benefits:**
✅ Clear visual hierarchy
✅ Consistent with Shopping Planner
✅ No hidden dropdowns
✅ Better information density
✅ Easier to browse items in a group
```

**Step 2: Commit**

```bash
git add docs/session-summary-2025-12-09-arbitrage-enhancement.md
git commit -m "docs: document arbitrage finder UX redesign

- Add Phase 2 section for 3-panel layout
- Document problem, solution, and benefits
- Include user flow description
- Note consistency with Shopping Planner"
```

---

## Task 7: Build and Deploy Frontend

**Files:**
- N/A (build artifacts)

**Step 1: Run production build**

```bash
cd frontend
npm run build
```

Expected: Build succeeds with no errors, outputs to `dist/` directory

**Step 2: Verify bundle size**

Check build output for bundle size. Should be similar to before (no major size increase).

Expected: Bundle size reasonable (~500KB gzipped or less)

**Step 3: Test production build locally**

```bash
npm run preview
```

Open browser to preview URL, test all functionality:
- Market group selection
- Items table population
- Search filter
- Item selection
- Arbitrage data display

Expected: All features work in production build

**Step 4: Commit build config if changed**

If any build configuration was modified:

```bash
git add vite.config.ts package.json
git commit -m "build: ensure production build includes new components"
```

---

## Final Verification Checklist

Run through this checklist before considering the task complete:

**Functionality:**
- [ ] Market group tree displays and expands/collapses
- [ ] Clicking group populates items table
- [ ] Items table shows name, volume, base price
- [ ] Search filter works within items table
- [ ] Item count shows correctly in footer
- [ ] Clicking item row loads arbitrage data
- [ ] Selected row highlights visually
- [ ] Arbitrage table shows all columns correctly
- [ ] Ship type selector updates data
- [ ] Min profit filter updates data
- [ ] Empty states show when no group/item selected

**Code Quality:**
- [ ] No TypeScript errors
- [ ] No console errors in browser
- [ ] No unused imports or variables
- [ ] Components follow React best practices
- [ ] Consistent with existing codebase style

**Performance:**
- [ ] No unnecessary re-renders
- [ ] Tables handle 50+ items smoothly
- [ ] Queries use proper enabled flags
- [ ] Loading states show during data fetch

**Documentation:**
- [ ] Session summary updated
- [ ] Code comments where needed
- [ ] Commit messages are clear

---

## Success Metrics

**Before:**
- ❌ Confusing dropdown UX
- ❌ Items appear/disappear unpredictably
- ❌ Inconsistent with rest of app
- ❌ Can't browse items in a group

**After:**
- ✅ Clear 3-panel layout
- ✅ Always shows all items in group
- ✅ Consistent with Shopping Planner
- ✅ Easy to browse and filter items
- ✅ Obvious selection and interaction model

---

## Rollback Plan

If issues arise after deployment:

1. Revert to previous commit:
   ```bash
   git revert HEAD~7..HEAD
   git push origin main
   ```

2. Rebuild frontend:
   ```bash
   cd frontend && npm run build
   ```

3. Redeploy

---

## Future Enhancements (Not in This Plan)

- Add column sorting to items table
- Add "Add to Shopping List" button in arbitrage details
- Show production feasibility indicators in items table
- Multi-item comparison mode
- Save favorite routes/items
- Export arbitrage opportunities to CSV

---

**Plan created:** 2025-12-09
**Estimated time:** 60-90 minutes
**Complexity:** Medium
**Risk:** Low (mostly UI changes, existing API endpoints work)
