# Shopping Planner Redesign - Step-Based Workflow

**Date:** 2025-12-07
**Status:** Planning
**Author:** Claude Code + User Brainstorming

---

## Overview

Redesign the Shopping Planner from a single-page list view to a guided, step-based workflow. Each step focuses on one decision type, making the process clearer and more intuitive.

**Example Flow:** Hawk Manufacturing

---

## Step 1: Product Definition

**Purpose:** Define what to build and how many runs.

### UI Elements

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Product Definition                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Product:  [Hawk]                          [Search Icon]    │
│                                                             │
│  Runs:     [1    ]  ▲▼                                     │
│                                                             │
│  Output:   1x Hawk                                          │
│  ME Level: 10%                                              │
│                                                             │
│                                           [Next Step →]     │
└─────────────────────────────────────────────────────────────┘
```

### Data Required

- Product search/autocomplete (existing)
- Blueprint lookup for ME level and output per run
- Calculation: `total_output = runs * output_per_run`

### API Changes

None - existing `/api/shopping/lists/{id}/add-production/{type_id}` provides this data.

### Frontend Changes

- New `ProductDefinitionStep.tsx` component
- State: `{ product: Item, runs: number, meLevel: number }`
- On "Next Step": Store product info, proceed to Step 2

---

## Step 2: Sub-Components Decision

**Purpose:** Decide which sub-components to build vs. buy.

### UI Elements

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Sub-Components                    [← Back]         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Building: 1x Hawk                                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [Select All: BUY]  [Select All: BUILD]              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Sub-Components (9 items):                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ☐ Merlin (1x)                          [BUY|BUILD] │   │
│  │ ☐ Gravimetric Sensor Cluster (30x)     [BUY|BUILD] │   │
│  │ ☐ Graviton Reactor Unit (8x)           [BUY|BUILD] │   │
│  │ ☐ Magpulse Thruster (30x)              [BUY|BUILD] │   │
│  │ ☐ Quantum Microprocessor (135x)        [BUY|BUILD] │   │
│  │ ☐ R.A.M.- Starship Tech (6x)           [BUY|BUILD] │   │
│  │ ☐ Scalar Capacitor Unit (90x)          [BUY|BUILD] │   │
│  │ ☐ Sustained Shield Emitter (30x)       [BUY|BUILD] │   │
│  │ ☐ Titanium Diborite Armor Plate (750x) [BUY|BUILD] │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│                                           [Next Step →]     │
└─────────────────────────────────────────────────────────────┘
```

### Features

1. **Select All Buttons:** Quick toggle all items to BUY or BUILD
2. **Individual Toggle:** Each component has its own BUY/BUILD toggle button
3. **Visual State:** Clear indication whether item is marked BUY or BUILD
4. **Persistence:** Decisions stored for next step calculation

### Data Required

- List of sub_products from Step 1 (items with `has_blueprint: true`)
- Store decision state: `Map<type_id, 'buy' | 'build'>`

### State Structure

```typescript
interface SubComponentDecision {
  type_id: number;
  item_name: string;
  quantity: number;
  decision: 'buy' | 'build';
}
```

### API Changes

**New Endpoint:** `POST /api/shopping/calculate-materials`

```json
// Request
{
  "product_type_id": 11379,
  "runs": 1,
  "me_level": 10,
  "decisions": {
    "603": "buy",           // Merlin
    "11534": "build",       // Gravimetric Sensor Cluster
    "11550": "buy",
    // ... etc
  }
}

// Response
{
  "product": { "type_id": 11379, "name": "Hawk", "quantity": 1 },
  "sub_components": [
    { "type_id": 603, "name": "Merlin", "quantity": 1, "decision": "buy" },
    { "type_id": 11534, "name": "Gravimetric Sensor Cluster", "quantity": 30, "decision": "build" }
  ],
  "shopping_list": [
    // All items marked "buy" + raw materials from items marked "build"
    { "type_id": 603, "name": "Merlin", "quantity": 1, "category": "sub_component" },
    { "type_id": 3828, "name": "Construction Blocks", "quantity": 35, "category": "material" },
    // Materials from building Gravimetric Sensor Cluster...
  ]
}
```

### Frontend Changes

- New `SubComponentsStep.tsx` component
- Toggle button component for BUY/BUILD
- State management for decisions
- Batch update handlers for "Select All"

---

## Step 3: Shopping List

**Purpose:** Display complete shopping list with cost calculation.

### UI Elements

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Shopping List                     [← Back]         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Building: 1x Hawk                                          │
│                                                             │
│  ═══════════════════════════════════════════════════════   │
│  SUB-COMPONENTS TO BUY (marked as BUY in Step 2)           │
│  ═══════════════════════════════════════════════════════   │
│  │ Item                          │ Qty  │ Est. Cost      │ │
│  ├───────────────────────────────┼──────┼────────────────┤ │
│  │ Merlin                        │ 1    │ 450,000 ISK    │ │
│  │ Graviton Reactor Unit         │ 8    │ 2,400,000 ISK  │ │
│  │ R.A.M.- Starship Tech         │ 6    │ 180,000 ISK    │ │
│  ├───────────────────────────────┼──────┼────────────────┤ │
│  │ Subtotal                      │      │ 3,030,000 ISK  │ │
│  └───────────────────────────────┴──────┴────────────────┘ │
│                                                             │
│  ═══════════════════════════════════════════════════════   │
│  RAW MATERIALS                                              │
│  ═══════════════════════════════════════════════════════   │
│  │ Item                          │ Qty  │ Est. Cost      │ │
│  ├───────────────────────────────┼──────┼────────────────┤ │
│  │ Construction Blocks           │ 35   │ 350,000 ISK    │ │
│  │ Morphite                      │ 41   │ 820,000 ISK    │ │
│  │ Titanium Carbide              │ 500  │ 2,500,000 ISK  │ │
│  │ Crystalline Carbonide         │ 200  │ 400,000 ISK    │ │
│  │ ... (more materials)          │      │                │ │
│  ├───────────────────────────────┼──────┼────────────────┤ │
│  │ Subtotal                      │      │ 38,000,000 ISK │ │
│  └───────────────────────────────┴──────┴────────────────┘ │
│                                                             │
│  ═══════════════════════════════════════════════════════   │
│  TOTAL ESTIMATED COST:                    41,030,000 ISK   │
│  ═══════════════════════════════════════════════════════   │
│                                                             │
│                                    [Compare Regions →]      │
└─────────────────────────────────────────────────────────────┘
```

### Features

1. **Two Sections:**
   - Sub-Components to Buy (items marked BUY in Step 2)
   - Raw Materials (from product + from items marked BUILD)

2. **Cost Calculation:**
   - Fetch prices from Jita (default) or selected region
   - Show per-item and subtotal costs
   - Grand total at bottom

3. **Aggregation:**
   - If same material appears multiple times (from different build paths), aggregate quantities

### Data Required

- Shopping list from Step 2 calculation
- Market prices per item (existing market_service)

### API Changes

Extend response from Step 2 endpoint to include prices:

```json
{
  "shopping_list": [
    {
      "type_id": 603,
      "name": "Merlin",
      "quantity": 1,
      "category": "sub_component",
      "jita_sell": 450000,
      "total_cost": 450000
    }
  ],
  "totals": {
    "sub_components": 3030000,
    "raw_materials": 38000000,
    "grand_total": 41030000
  }
}
```

### Frontend Changes

- New `ShoppingListStep.tsx` component
- Grouped display with collapsible sections
- Cost formatting with ISK abbreviations
- Loading state while fetching prices

---

## Step 4: Regional Comparison

**Purpose:** Compare prices across regions and optimize shopping route.

### UI Elements

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Regional Comparison               [← Back]         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ REGIONAL PRICE COMPARISON                           │   │
│  ├──────────┬──────────┬──────────┬──────────┬────────┤   │
│  │ Item     │ Jita     │ Amarr    │ Dodixie  │ Best   │   │
│  ├──────────┼──────────┼──────────┼──────────┼────────┤   │
│  │ Merlin   │ 450K ✓   │ 480K     │ 520K     │ Jita   │   │
│  │ Morphite │ 20K      │ 18K ✓    │ 22K      │ Amarr  │   │
│  │ Trit     │ 5.2      │ 5.0 ✓    │ 5.5      │ Amarr  │   │
│  └──────────┴──────────┴──────────┴──────────┴────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ OPTIMAL SHOPPING ROUTE                              │   │
│  │                                                     │   │
│  │ 1. Jita (12 items)         Total: 25,000,000 ISK   │   │
│  │    → Merlin, Construction Blocks, ...              │   │
│  │                                                     │   │
│  │ 2. Amarr (5 items)         Total: 16,000,000 ISK   │   │
│  │    → Morphite, Tritanium, ...                      │   │
│  │    Route: Jita → Amarr (9 jumps)                   │   │
│  │                                                     │   │
│  │ ─────────────────────────────────────────────────  │   │
│  │ TOTAL: 41,000,000 ISK                              │   │
│  │ Savings vs Jita-only: 2,500,000 ISK (5.7%)         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [Export to Clipboard]  [Save Shopping List]  [Done ✓]      │
└─────────────────────────────────────────────────────────────┘
```

### Features

1. **Price Comparison Table:**
   - Show prices from all major hubs
   - Highlight best price per item
   - Calculate potential savings

2. **Optimal Route Calculation:**
   - Group items by best-price region
   - Calculate route between hubs
   - Show savings vs single-hub shopping

3. **Export Options:**
   - Copy to clipboard (for in-game shopping)
   - Save as shopping list (existing functionality)

### Data Required

- Shopping list from Step 3
- Regional prices from all hubs
- Route calculation (existing route_service)

### API Changes

**New Endpoint:** `POST /api/shopping/compare-regions`

```json
// Request
{
  "items": [
    { "type_id": 603, "quantity": 1 },
    { "type_id": 11399, "quantity": 41 }
  ]
}

// Response
{
  "comparison": [
    {
      "type_id": 603,
      "name": "Merlin",
      "quantity": 1,
      "prices": {
        "jita": { "price": 450000, "total": 450000 },
        "amarr": { "price": 480000, "total": 480000 },
        "dodixie": { "price": 520000, "total": 520000 }
      },
      "best_region": "jita"
    }
  ],
  "optimal_route": {
    "stops": [
      {
        "region": "jita",
        "items": [...],
        "subtotal": 25000000
      },
      {
        "region": "amarr",
        "items": [...],
        "subtotal": 16000000,
        "route_from_previous": { "jumps": 9 }
      }
    ],
    "total": 41000000,
    "jita_only_total": 43500000,
    "savings": 2500000,
    "savings_percent": 5.7
  }
}
```

### Frontend Changes

- New `RegionalComparisonStep.tsx` component
- Price comparison table with highlighting
- Route visualization
- Export functionality

---

## Implementation Plan

### Phase 1: Backend API (3 Tasks)

1. **Task 1.1:** Create `/api/shopping/calculate-materials` endpoint
   - Accept product, runs, ME level, and build decisions
   - Return flattened shopping list with categories
   - Aggregate duplicate materials

2. **Task 1.2:** Add price calculation to shopping list response
   - Integrate with existing market_service
   - Calculate totals per category

3. **Task 1.3:** Create `/api/shopping/compare-regions` endpoint
   - Fetch prices from all hubs
   - Calculate optimal route
   - Return savings analysis

### Phase 2: Frontend Wizard (4 Tasks)

4. **Task 2.1:** Create `ShoppingWizard.tsx` container component
   - Manage wizard state (current step, data)
   - Handle step navigation
   - Pass data between steps

5. **Task 2.2:** Implement `ProductDefinitionStep.tsx`
   - Product search (reuse existing)
   - Runs input
   - Display output calculation

6. **Task 2.3:** Implement `SubComponentsStep.tsx`
   - List sub-components
   - BUY/BUILD toggle buttons
   - Select All functionality

7. **Task 2.4:** Implement `ShoppingListStep.tsx`
   - Grouped display (sub-components / materials)
   - Cost calculation display
   - Loading states

### Phase 3: Regional Comparison (2 Tasks)

8. **Task 3.1:** Implement `RegionalComparisonStep.tsx`
   - Price comparison table
   - Best price highlighting
   - Optimal route display

9. **Task 3.2:** Add export functionality
   - Copy to clipboard
   - Save to existing shopping list system

### Phase 4: Integration & Polish (2 Tasks)

10. **Task 4.1:** Replace existing ShoppingPlanner with new wizard
    - Update routes
    - Migration path for existing lists

11. **Task 4.2:** Testing and polish
    - Test all edge cases
    - Loading states
    - Error handling

---

## State Management

### Wizard State Structure

```typescript
interface ShoppingWizardState {
  currentStep: 1 | 2 | 3 | 4;

  // Step 1 data
  product: {
    type_id: number;
    name: string;
    runs: number;
    me_level: number;
    output_per_run: number;
  } | null;

  // Step 2 data
  subComponents: SubComponentDecision[];

  // Step 3 data
  shoppingList: ShoppingItem[];
  totals: {
    sub_components: number;
    raw_materials: number;
    grand_total: number;
  };

  // Step 4 data
  regionalComparison: RegionalComparisonData | null;
}
```

---

## File Structure

```
frontend/src/
├── pages/
│   └── ShoppingPlanner.tsx          # Updated to use wizard
│
├── components/
│   └── shopping/
│       ├── ShoppingWizard.tsx       # Main wizard container
│       ├── ProductDefinitionStep.tsx
│       ├── SubComponentsStep.tsx
│       ├── ShoppingListStep.tsx
│       ├── RegionalComparisonStep.tsx
│       ├── BuildBuyToggle.tsx       # Reusable toggle component
│       └── PriceComparisonTable.tsx
```

---

## Migration Strategy

1. Keep existing shopping list functionality intact
2. New wizard creates shopping lists via existing API
3. Wizard is the new default entry point
4. Old list view remains accessible for viewing saved lists

---

## Success Criteria

- [ ] User can define product and runs
- [ ] User can toggle BUY/BUILD for each sub-component
- [ ] Select All BUY/BUILD works correctly
- [ ] Shopping list shows correct aggregated materials
- [ ] Cost calculation is accurate
- [ ] Regional comparison shows all hub prices
- [ ] Optimal route is calculated correctly
- [ ] Export to clipboard works
- [ ] Save to shopping list works

---

## Notes

- Reactions (activityID 11) are already supported in backend
- Existing material calculation logic can be reused
- Market prices are cached, so Step 3/4 should be fast
- Route calculation uses existing A* implementation
