# Dashboard Redesign - Implementation Plan

**Date:** 2025-12-11
**Design Doc:** `2025-12-11-dashboard-redesign-design.md`
**Approach:** Test-Driven Development (TDD)
**Estimated Tasks:** 12

---

## Implementation Strategy

### Approach
1. **Incremental replacement** - Build new components alongside old ones
2. **TDD workflow** - Write tests first, then implement
3. **Component-by-component** - One component per task
4. **Visual testing** - Manual verification after each component

### File Structure
```
frontend/src/
├── components/
│   └── dashboard/
│       ├── OpportunitiesTable.tsx       (NEW - Task 1)
│       ├── OpportunitiesTable.css       (NEW - Task 1)
│       ├── CharacterCard.tsx            (NEW - Task 2)
│       ├── CharacterCard.css            (NEW - Task 2)
│       ├── CharacterOverview.tsx        (REDESIGN - Task 3)
│       ├── CharacterOverview.css        (REDESIGN - Task 3)
│       ├── WarRoomAlerts.tsx            (NEW - Task 4)
│       ├── WarRoomAlerts.css            (NEW - Task 4)
│       ├── ActiveProjects.tsx           (NEW - Task 5)
│       ├── ActiveProjects.css           (NEW - Task 5)
│       ├── OpportunityCard.tsx          (DELETE after Task 1)
│       ├── OpportunityCard.css          (DELETE after Task 1)
│       ├── OpportunitiesFeed.tsx        (DELETE after Task 1)
│       └── OpportunitiesFeed.css        (DELETE after Task 1)
├── pages/
│   ├── Dashboard.tsx                    (UPDATE - Task 6)
│   └── Dashboard.css                    (MAJOR REWRITE - Task 6)
└── hooks/
    └── dashboard/
        ├── useCharacterPortrait.ts      (NEW - Task 2)
        └── useCharacterOnline.ts        (NEW - Task 2)
```

---

## Phase 1: Core Components (Tasks 1-3)

### Task 1.1: Create OpportunitiesTable Component (TDD)

**Test File:** `frontend/src/components/dashboard/__tests__/OpportunitiesTable.test.tsx`

**Tests to write FIRST:**
```typescript
describe('OpportunitiesTable', () => {
  it('renders table with correct headers', () => {
    // Verify headers: Icon, Item Name, Profit, ROI, Category, Actions
  });

  it('renders opportunities data in rows', () => {
    // Mock 5 opportunities, verify all rendered
  });

  it('formats profit with green gradient for high values', () => {
    // Check profit >5B has bright green color
  });

  it('color-codes ROI based on thresholds', () => {
    // >40% bright green, 20-40% medium, <20% muted
  });

  it('shows category badges with correct styling', () => {
    // PROD, TRADE, WAR_DEMAND badges
  });

  it('handles row hover state', () => {
    // Hover should change background and show left border
  });

  it('makes columns sortable', () => {
    // Click header should sort, show arrow indicator
  });

  it('handles empty state gracefully', () => {
    // No opportunities: show "No opportunities found"
  });
});
```

**Implementation:**
1. Create `OpportunitiesTable.tsx` with table structure
2. Implement data rendering from props
3. Add sorting logic (useState for sort column/direction)
4. Apply CSS for styling (row height, hover, borders)
5. Add profit/ROI color coding logic

**Styling:** `OpportunitiesTable.css`
- Row height: 48px
- Hover background transition
- Left border on hover: `2px solid #58a6ff`
- Tabular numbers for alignment

**Props Interface:**
```typescript
interface OpportunitiesTableProps {
  opportunities: Opportunity[];
  onRowClick?: (opportunity: Opportunity) => void;
  loading?: boolean;
}
```

**Commit:** `feat(frontend): add OpportunitiesTable component with TDD`

---

### Task 1.2: Add Table Sorting Logic

**Test File:** Update `OpportunitiesTable.test.tsx`

**Additional Tests:**
```typescript
describe('OpportunitiesTable sorting', () => {
  it('sorts by profit descending by default', () => {
    // First row should be highest profit
  });

  it('toggles sort direction on header click', () => {
    // Click once: ascending, click again: descending
  });

  it('rotates arrow indicator when sorting', () => {
    // Arrow should rotate 180deg
  });

  it('sorts numbers correctly (not alphabetically)', () => {
    // 10B > 2B (not "10" < "2")
  });

  it('sorts by all columns', () => {
    // Test sorting by Name, Profit, ROI, Category
  });
});
```

**Implementation:**
1. Add `sortColumn` and `sortDirection` useState
2. Implement sort comparator functions
3. Add arrow indicator to headers
4. Add click handlers to headers
5. Apply CSS rotation animation to arrows

**Commit:** `feat(frontend): add sorting to OpportunitiesTable`

---

### Task 2.1: Create useCharacterPortrait Hook (TDD)

**Test File:** `frontend/src/hooks/dashboard/__tests__/useCharacterPortrait.test.tsx`

**Tests:**
```typescript
describe('useCharacterPortrait', () => {
  it('fetches portrait from ESI API', async () => {
    // Mock ESI response with portrait URLs
    // Verify returns px256x256 URL
  });

  it('returns loading state while fetching', () => {
    // Initially: { loading: true, url: null, error: null }
  });

  it('returns error on API failure', async () => {
    // Mock API error, verify error state
  });

  it('returns fallback URL on 404', () => {
    // Character has no portrait: use default avatar
  });

  it('caches portrait URL after first fetch', () => {
    // Second call should not hit API
  });
});
```

**Implementation:**
```typescript
interface UseCharacterPortraitResult {
  url: string | null;
  loading: boolean;
  error: Error | null;
}

function useCharacterPortrait(characterId: number): UseCharacterPortraitResult {
  // Use React Query to fetch from /api/character/{id}/portrait (via backend proxy)
  // Return px256x256 URL
  // Cache for 24 hours
  // Fallback to default avatar on error
}
```

**Backend Support Required:**
Create proxy endpoint in FastAPI:
```python
@router.get("/character/{character_id}/portrait")
async def get_character_portrait(character_id: int):
    # Fetch from ESI: /characters/{character_id}/portrait/
    # Return px256x256 URL
    # Cache for 24 hours
```

**Commit:** `feat(frontend): add useCharacterPortrait hook with TDD`

---

### Task 2.2: Create CharacterCard Component (TDD)

**Test File:** `frontend/src/components/dashboard/__tests__/CharacterCard.test.tsx`

**Tests:**
```typescript
describe('CharacterCard', () => {
  it('renders character portrait', () => {
    // Verify <img> with portrait URL
  });

  it('shows loading state for portrait', () => {
    // Skeleton or spinner while loading
  });

  it('shows fallback avatar on error', () => {
    // Portrait fails: show default avatar icon
  });

  it('displays character name', () => {
    // Name rendered correctly
  });

  it('shows ISK balance formatted', () => {
    // 2400000000 → "2.4B ISK"
  });

  it('displays location with truncation', () => {
    // Long system names truncated to 15 chars
  });

  it('shows online status dot', () => {
    // Green if online, gray if offline
  });

  it('applies hover glow effect', () => {
    // Hover increases box-shadow glow
  });
});
```

**Implementation:**
1. Create `CharacterCard.tsx` component
2. Use `useCharacterPortrait` hook
3. Format ISK with `formatISK` utility
4. Add status dot (green/gray)
5. Style with glow effect

**Props:**
```typescript
interface CharacterCardProps {
  characterId: number;
  name: string;
  balance: number;
  location: string;
  online: boolean;
}
```

**Styling:** `CharacterCard.css`
- Dimensions: 140px × 200px
- Portrait: 120px × 120px with glow
- Hover: Intensified glow + blue border

**Commit:** `feat(frontend): add CharacterCard with portraits`

---

### Task 3: Update CharacterOverview Component

**Test File:** `frontend/src/components/dashboard/__tests__/CharacterOverview.test.tsx`

**Tests:**
```typescript
describe('CharacterOverview', () => {
  it('renders 3 character cards', () => {
    // Artallus, Cytrex, Cytricia
  });

  it('displays section header "Your Pilots"', () => {
    // Not "Your Characters"
  });

  it('fetches data for all 3 characters', () => {
    // Calls portfolio API endpoint
  });

  it('shows loading state for all cards', () => {
    // While fetching
  });

  it('handles API errors gracefully', () => {
    // Error for one character doesn't break others
  });
});
```

**Implementation:**
1. Update `CharacterOverview.tsx` to use new `CharacterCard`
2. Fetch data from `/api/dashboard/characters/summary` (existing endpoint)
3. Map data to 3 `CharacterCard` components
4. Update CSS for horizontal layout

**Changes:**
- Replace old gradient cards with new portrait cards
- Use "Your Pilots" header
- Horizontal flex layout

**Commit:** `refactor(frontend): redesign CharacterOverview with portraits`

---

## Phase 2: Sidebar Components (Tasks 4-5)

### Task 4: Create WarRoomAlerts Component (TDD)

**Test File:** `frontend/src/components/dashboard/__tests__/WarRoomAlerts.test.tsx`

**Tests:**
```typescript
describe('WarRoomAlerts', () => {
  it('renders alert items with icons', () => {
    // 🔴 high priority, 🟡 medium
  });

  it('shows timestamps in relative format', () => {
    // "2h ago", "5h ago"
  });

  it('limits to 5 alerts with "View All" link', () => {
    // More than 5: show link
  });

  it('shows empty state when no alerts', () => {
    // "No active threats" with 🛡️
  });

  it('adds scrollbar when >5 alerts', () => {
    // Max-height with overflow-y
  });
});
```

**Implementation:**
1. Create `WarRoomAlerts.tsx` component
2. Fetch from `/api/war/alerts` (to be created in backend)
3. Render alert list with icons
4. Format timestamps with `date-fns` (relative)
5. Style with red left border

**API Endpoint (Backend Task):**
```python
@router.get("/war/alerts")
async def get_war_alerts(limit: int = 5):
    # Return recent high-priority war events
    # From combat_ship_losses or sovereignty_campaigns
```

**Commit:** `feat(frontend): add WarRoomAlerts component`

---

### Task 5: Create ActiveProjects Component (TDD)

**Test File:** `frontend/src/components/dashboard/__tests__/ActiveProjects.test.tsx`

**Tests:**
```typescript
describe('ActiveProjects', () => {
  it('renders project items with progress bars', () => {
    // Progress bar shows completion percentage
  });

  it('displays project status text', () => {
    // "3/10 items"
  });

  it('shows empty state when no projects', () => {
    // "No active projects" with ➕
  });

  it('calculates progress percentage correctly', () => {
    // 3/10 = 30% width
  });
});
```

**Implementation:**
1. Create `ActiveProjects.tsx` component
2. Fetch from `/api/dashboard/projects` (to be created)
3. Render project list with progress bars
4. Calculate percentage for bar width
5. Style with blue left border

**API Endpoint (Backend Task):**
```python
@router.get("/dashboard/projects")
async def get_active_projects():
    # Return shopping lists with completion status
    # Count items: checked vs total
```

**Commit:** `feat(frontend): add ActiveProjects component`

---

## Phase 3: Integration (Task 6)

### Task 6.1: Update Dashboard Page Layout

**Test File:** `frontend/src/pages/__tests__/Dashboard.test.tsx`

**Tests:**
```typescript
describe('Dashboard', () => {
  it('renders main content at 70% width', () => {
    // CSS grid/flex layout
  });

  it('renders sidebar at 30% width', () => {
    // Sidebar column
  });

  it('shows OpportunitiesTable in main area', () => {
    // New table component
  });

  it('shows CharacterOverview below table', () => {
    // 25% of main height
  });

  it('renders WarRoomAlerts in sidebar', () => {
    // Top sidebar section
  });

  it('renders ActiveProjects in sidebar', () => {
    // Bottom sidebar section
  });

  it('applies dark background color', () => {
    // #0a0e14
  });
});
```

**Implementation:**
1. Remove old components (`OpportunitiesFeed`, `OpportunityCard`)
2. Add new components (`OpportunitiesTable`, `WarRoomAlerts`, `ActiveProjects`)
3. Restructure layout with CSS Grid
4. Update proportions (70/30 split)
5. Apply new color palette

**Layout Structure:**
```tsx
<div className="dashboard">
  <div className="dashboard-main">
    <OpportunitiesTable opportunities={opportunities} />
    <CharacterOverview />
  </div>
  <aside className="dashboard-sidebar">
    <WarRoomAlerts />
    <ActiveProjects />
  </aside>
</div>
```

**Commit:** `refactor(frontend): integrate redesigned dashboard layout`

---

### Task 6.2: Major CSS Rewrite

**Changes:**
1. Update color variables to new palette
2. Rewrite grid layout (70/30 split)
3. Add custom scrollbar styling
4. Remove old card styles
5. Add subtle sci-fi hover effects

**CSS Variables:**
```css
:root {
  --bg-primary: #0a0e14;
  --bg-surface: #161b22;
  --bg-elevated: #21262d;
  --border: #21262d;

  --text-primary: #e6edf3;
  --text-secondary: #8b949e;
  --text-tertiary: #6e7681;

  --accent-blue: #58a6ff;
  --accent-green: #3fb950;
  --danger: #f85149;

  --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
```

**Commit:** `style(frontend): rewrite Dashboard CSS for new design`

---

## Phase 4: Backend Support (Tasks 7-9)

### Task 7: Add Character Portrait Proxy Endpoint

**Test File:** `tests/routers/test_character_portraits.py`

**Tests:**
```python
def test_get_character_portrait_returns_urls():
    # Mock ESI response
    # Verify returns px256x256

def test_get_character_portrait_caches_result():
    # Second call should use cache, not ESI

def test_get_character_portrait_handles_404():
    # Character without portrait: return default URL
```

**Implementation:**
```python
# routers/character.py

@router.get("/character/{character_id}/portrait")
async def get_character_portrait(character_id: int):
    """Proxy ESI character portrait endpoint with caching."""
    cache_key = f"portrait_{character_id}"

    # Check cache (24h TTL)
    if cached := get_from_cache(cache_key):
        return cached

    # Fetch from ESI
    try:
        response = await esi_client.get(
            f"/characters/{character_id}/portrait/"
        )
        url = response["px256x256"]

        # Cache result
        set_cache(cache_key, {"url": url}, ttl=86400)

        return {"url": url}
    except ESIError:
        # Return default avatar
        return {"url": "/assets/default-avatar.png"}
```

**Commit:** `feat(backend): add character portrait proxy endpoint`

---

### Task 8: Add War Room Alerts Endpoint

**Test File:** `tests/routers/test_war_alerts.py`

**Tests:**
```python
def test_get_war_alerts_returns_recent_events():
    # Query combat_ship_losses for high-value kills
    # Verify returns formatted alerts

def test_get_war_alerts_limits_to_5():
    # Default limit=5

def test_get_war_alerts_includes_timestamps():
    # Timestamps in ISO format
```

**Implementation:**
```python
# routers/war.py

@router.get("/war/alerts")
async def get_war_alerts(limit: int = 5):
    """Get recent high-priority war events."""
    cursor.execute("""
        SELECT
            type_id,
            typeName,
            kill_time,
            estimated_value,
            region_id,
            regionName
        FROM combat_ship_losses csl
        JOIN invTypes t ON csl.type_id = t.typeID
        WHERE estimated_value > 1000000000  -- >1B ISK
        AND kill_time > NOW() - INTERVAL '24 hours'
        ORDER BY kill_time DESC
        LIMIT %s
    """, (limit,))

    alerts = []
    for row in cursor.fetchall():
        alerts.append({
            "priority": "high" if row[3] > 5000000000 else "medium",
            "message": f"High-value target in {row[5]}",
            "timestamp": row[2].isoformat(),
            "value": row[3]
        })

    return alerts
```

**Commit:** `feat(backend): add war room alerts endpoint`

---

### Task 9: Add Active Projects Endpoint

**Test File:** `tests/routers/test_active_projects.py`

**Tests:**
```python
def test_get_active_projects_returns_shopping_lists():
    # Query shopping_lists with completion status
    # Verify calculates progress

def test_get_active_projects_includes_item_counts():
    # total_items, checked_items
```

**Implementation:**
```python
# routers/dashboard.py

@router.get("/dashboard/projects")
async def get_active_projects():
    """Get active shopping lists as projects."""
    cursor.execute("""
        SELECT
            sl.id,
            sl.name,
            COUNT(sli.id) as total_items,
            COUNT(CASE WHEN sli.checked THEN 1 END) as checked_items
        FROM shopping_lists sl
        LEFT JOIN shopping_list_items sli ON sl.id = sli.list_id
        WHERE sl.archived = FALSE
        GROUP BY sl.id, sl.name
        ORDER BY sl.created_at DESC
    """)

    projects = []
    for row in cursor.fetchall():
        total = row[2]
        checked = row[3]
        progress = (checked / total * 100) if total > 0 else 0

        projects.append({
            "id": row[0],
            "name": row[1],
            "total_items": total,
            "checked_items": checked,
            "progress": progress
        })

    return projects
```

**Commit:** `feat(backend): add active projects endpoint`

---

## Phase 5: Polish & Testing (Tasks 10-12)

### Task 10: Add Responsive Breakpoints

**Test:** Manual testing on different screen sizes

**Implementation:**
1. Add media queries for tablet (768-1199px)
2. Add media queries for mobile (<768px)
3. Test table horizontal scrolling on mobile
4. Test sidebar positioning on tablet

**CSS:**
```css
/* Tablet */
@media (max-width: 1199px) {
  .dashboard {
    flex-direction: column;
  }

  .dashboard-sidebar {
    width: 100%;
  }
}

/* Mobile */
@media (max-width: 767px) {
  .opportunities-table-container {
    overflow-x: auto;
  }

  .character-cards {
    flex-direction: column;
  }
}
```

**Commit:** `feat(frontend): add responsive breakpoints to dashboard`

---

### Task 11: Add Loading & Error States

**Tests:**
```typescript
describe('Dashboard loading states', () => {
  it('shows skeleton loaders while fetching', () => {
    // Table: skeleton rows
    // Characters: skeleton cards
  });

  it('shows error message on API failure', () => {
    // Error boundary or error component
  });

  it('retries failed requests', () => {
    // React Query retry logic
  });
});
```

**Implementation:**
1. Add skeleton components for table rows
2. Add skeleton components for character cards
3. Add error boundaries
4. Configure React Query retry logic

**Commit:** `feat(frontend): add loading and error states`

---

### Task 12: Final Visual Polish

**Manual Testing Checklist:**
- [ ] All hover effects smooth (200ms transition)
- [ ] Table sorting works correctly
- [ ] Character portraits load and fallback works
- [ ] Scrollbar styled correctly
- [ ] Colors match design spec
- [ ] Typography matches (sizes, weights, spacing)
- [ ] Responsive layout works on all breakpoints
- [ ] Accessibility: keyboard navigation works
- [ ] Accessibility: screen reader labels correct
- [ ] Performance: table renders in <100ms

**Fine-tuning:**
- Adjust spacing if needed
- Tweak colors for better contrast
- Optimize animations
- Fix any visual bugs

**Commit:** `polish(frontend): final visual adjustments to dashboard`

---

## Testing Strategy

### Unit Tests
- All components have test files
- Test rendering, data handling, user interactions
- Mock API calls with MSW (Mock Service Worker)

### Integration Tests
- Test full dashboard data flow
- Test component interactions
- Test responsive behavior

### Visual Testing
- Manual review after each task
- Screenshot comparison (optional: Percy/Chromatic)
- Cross-browser testing (Chrome, Firefox, Safari)

### Accessibility Testing
- Automated: axe-core or jest-axe
- Manual: Keyboard navigation
- Screen reader: VoiceOver/NVDA

---

## Deployment Plan

### Step 1: Feature Branch
```bash
git checkout -b feature/dashboard-redesign
```

### Step 2: Incremental Commits
- Commit after each task completes
- Push to feature branch regularly
- Keep commits atomic and well-described

### Step 3: Code Review
- Create pull request when all tasks complete
- Self-review: Check all files changed
- Test on staging environment

### Step 4: Merge to Main
```bash
git checkout main
git merge feature/dashboard-redesign
git push origin main
```

### Step 5: Production Deploy
- Frontend: `npm run build` and serve dist/
- Backend: Already deployed (new endpoints)

---

## Rollback Plan

If major issues found after deployment:

### Option 1: Quick Fix
- Fix critical bugs in hotfix branch
- Deploy immediately

### Option 2: Revert
```bash
git revert HEAD
git push origin main
```
- Reverts to old dashboard design
- Gives time to fix issues properly

### Option 3: Feature Flag
- Add feature flag `ENABLE_NEW_DASHBOARD`
- Toggle in config to switch between old/new
- (Requires additional implementation)

---

## Success Criteria

Dashboard redesign is complete when:
1. ✅ All 12 tasks completed with passing tests
2. ✅ Manual testing checklist 100% complete
3. ✅ No console errors or warnings
4. ✅ Performance: Table renders <100ms
5. ✅ Accessibility: Passes automated checks
6. ✅ User feedback: "Looks professional"
7. ✅ Code review approved
8. ✅ Deployed to production

---

## Timeline Estimate

**Assuming TDD approach with subagent-driven-development:**

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Core Components | 1-3 | 2-3 hours |
| Phase 2: Sidebar Components | 4-5 | 1 hour |
| Phase 3: Integration | 6 | 1 hour |
| Phase 4: Backend Support | 7-9 | 1 hour |
| Phase 5: Polish & Testing | 10-12 | 1 hour |
| **Total** | **12 tasks** | **6-7 hours** |

**Note:** With parallel execution (multiple subagents), can reduce to 3-4 hours.

---

**Ready to start implementation?**
Begin with Task 1.1: Create OpportunitiesTable Component (TDD)
