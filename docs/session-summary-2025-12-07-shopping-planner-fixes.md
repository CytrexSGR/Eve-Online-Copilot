# Session Summary: Shopping Planner Bug Fixes & Improvements
**Date:** 2025-12-07
**Duration:** ~2 hours
**Focus:** Shopping Planner recursive BUY/BUILD functionality

---

## Overview

Fixed critical bugs in the Shopping Planner's recursive BUY/BUILD toggle system and Regional Price Comparison feature. The system now correctly handles large material quantities and properly aggregates materials based on build decisions.

---

## Problems Solved

### 1. Titanium Chromide BUILD Button Not Responding

**Symptoms:**
- BUILD button appeared clickable but didn't respond
- No visual feedback or state change
- Happened specifically for high-quantity materials at deep nesting levels

**Root Causes:**

#### Bug A: Hardcoded Depth (Frontend)
- **Location:** `frontend/src/pages/ShoppingPlanner.tsx:753`
- **Issue:** Recursive depth was hardcoded to `depth={1}` instead of `depth={depth + 1}`
- **Impact:** All nested sub-products appeared at the same visual indentation level, causing layout overlap

#### Bug B: INTEGER Overflow (Backend)
- **Location:** `shopping_list_items` database table
- **Issue:** `quantity` and `runs` columns were defined as `INTEGER` (max 2.1 billion)
- **Example:**
  - Titanium Chromide: 26,730,000 units
  - Material (Titanium): `100 × 26,730,000 × 0.9 ME = 2,405,700,000` ← **OVERFLOW!**
- **Impact:** Database constraint violation (NumericValueOutOfRange), causing API 500 errors

**Fixes:**
- Changed recursive depth: `depth={1}` → `depth={depth + 1}`
- Changed database columns: `INTEGER` → `BIGINT` (max 9.2 quintillion)
- Created migration: `migrations/004_shopping_bigint_quantities.sql`

---

### 2. Regional Price Comparison Showing 0 Items

**Symptoms:**
- Regional comparison view loaded but showed empty table
- No materials listed despite having items in shopping list
- API returned `{ "items": [] }`

**Root Cause:**
- **Location:** `routers/shopping.py:290, 294`
- **Issue:** Code checked `sub.get('mode')` but data structure uses `sub.get('build_decision')`
- **Impact:** Recursive material aggregation never executed, resulting in empty comparison

**Fix:**
- Changed all occurrences of `sub.get('mode')` to `sub.get('build_decision')`
- Now correctly processes materials based on BUY/BUILD decisions:
  - `build_decision='buy'` → Add sub-product to shopping list
  - `build_decision='build'` → Add materials recursively

**Verification:**
```bash
# Before fix
curl http://localhost:8000/api/shopping/lists/18/regional-comparison
# Result: { "items": [] }

# After fix
curl http://localhost:8000/api/shopping/lists/18/regional-comparison
# Result: { "items": 36, ... }
```

---

### 3. UI Simplification: Collapsible Region Totals

**Change:** Made "Region Totals Summary" section collapsible and collapsed by default

**Motivation:**
- Primary focus should be on the Regional Price Comparison table
- Region totals (Jita, Amarr, Rens, etc.) are reference data, not primary workflow

**Implementation:**
- Added state: `const [showRegionTotals, setShowRegionTotals] = useState(false)`
- Wrapped section in clickable card header with chevron icon
- Added `e.stopPropagation()` to "Apply All" and "Apply Optimal" buttons

---

## Technical Details

### Database Schema Change

**File:** `migrations/004_shopping_bigint_quantities.sql`

```sql
ALTER TABLE shopping_list_items
  ALTER COLUMN quantity TYPE BIGINT,
  ALTER COLUMN runs TYPE BIGINT;
```

**Capacity Comparison:**
- **INTEGER:** 2,147,483,647 (2.1 billion)
- **BIGINT:** 9,223,372,036,854,775,807 (9.2 quintillion)

### Data Structure Understanding

The shopping list has a hierarchical structure:

```typescript
{
  products: [
    {
      id: 659,
      item_name: "Hawk",
      build_decision: null,  // Top-level products don't have build_decision
      materials: [          // Raw materials (is_product=false)
        { item_name: "Construction Blocks", quantity: 342 },
        { item_name: "Morphite", quantity: 405 }
      ],
      sub_products: [       // Buildable components (is_product=true)
        {
          id: 1212,
          item_name: "Titanium Diborite Armor Plate",
          build_decision: "build",
          materials: [],    // Empty if all materials are also buildable
          sub_products: [
            {
              id: 1223,
              item_name: "Titanium Carbide",
              build_decision: "build",
              materials: [],
              sub_products: [
                {
                  id: 1225,
                  item_name: "Titanium Chromide",
                  build_decision: "build",
                  materials: [  // Raw materials needed to build
                    { item_name: "Chromium", quantity: 2405700000 },
                    { item_name: "Titanium", quantity: 2405700000 }
                  ],
                  sub_products: [
                    {
                      item_name: "Oxygen Fuel Block",
                      build_decision: "build"
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

**Key Insights:**
- `materials` = Raw materials (`is_product=false`)
- `sub_products` = Buildable items (`is_product=true`)
- `build_decision` only exists on `sub_products`, not raw materials

### Regional Comparison Aggregation Logic

```python
def process_sub_products_recursive(sub_products):
    """Recursively process sub-products and their materials"""
    for sub in sub_products:
        # If sub-product build_decision is 'buy', add the sub-product itself to buy list
        if sub.get('build_decision') == 'buy':
            if not sub.get('is_purchased'):
                add_to_aggregated(sub)
        # If sub-product build_decision is 'build', process its materials
        elif sub.get('build_decision') == 'build':
            # Process direct materials
            for mat in sub.get('materials', []):
                if not sub.get('is_purchased'):
                    add_to_aggregated(mat)
            # Recursively process nested sub-products
            if sub.get('sub_products'):
                process_sub_products_recursive(sub.get('sub_products', []))
```

**Result:** Materials with same `type_id` are aggregated (e.g., Titanium Carbide from multiple sources)

---

## Files Modified

### Frontend
- `frontend/src/pages/ShoppingPlanner.tsx`
  - Line 753: Fixed recursive depth propagation
  - Line 774: Added `showRegionTotals` state
  - Lines 1953-2026: Made Region Totals Summary collapsible

### Backend
- `routers/shopping.py`
  - Lines 290, 294: Changed `mode` → `build_decision`

### Database
- `migrations/004_shopping_bigint_quantities.sql` (new file)

---

## Git Commits

1. **fix: resolve integer overflow in shopping list material calculations**
   - Commit: `68953ff`
   - Changed quantity/runs to BIGINT
   - Fixed depth propagation bug

2. **fix: regional comparison now uses build_decision instead of mode**
   - Commit: `6bd6e51`
   - Fixed material aggregation logic

3. **feat: make region totals summary collapsible in shopping planner**
   - Commit: `8bb16ac`
   - UI improvement for better focus

---

## Testing Performed

### Manual Testing

1. **INTEGER Overflow Test:**
   ```bash
   # Add Titanium Diborite Armor Plate (causes high quantities)
   curl -X POST http://localhost:8000/api/shopping/lists/18/add-production/11544 \
     -d '{"quantity": 10, "runs": 1, "me_level": 10}'

   # Try to set Titanium Chromide to BUILD
   curl -X PATCH http://localhost:8000/api/shopping/items/1225/build-decision \
     -d '{"decision": "build"}'

   # Before fix: 500 Internal Server Error (NumericValueOutOfRange)
   # After fix: 200 OK with materials created
   ```

2. **Regional Comparison Test:**
   ```bash
   # Check regional comparison
   curl http://localhost:8000/api/shopping/lists/18/regional-comparison

   # Before fix: { "items": [] }
   # After fix: { "items": 36, ... }
   ```

3. **Python Direct Test:**
   ```python
   from shopping_service import ShoppingService
   svc = ShoppingService()
   result = svc.update_build_decision(1225, 'build')
   # Verified materials created with quantities > 2.4 billion
   ```

---

## Known Limitations

None. All functionality working as expected.

---

## Next Steps / Future Improvements

### Potential Enhancements:
1. Add visual indicator when materials require > 1 billion units (extreme quantities)
2. Consider adding "bulk operations" for setting multiple items to BUILD/BUY at once
3. Add undo/redo functionality for build decisions
4. Cache regional comparison results for faster repeated access

### Performance Considerations:
- BIGINT uses 8 bytes instead of 4 bytes (INTEGER)
- Impact negligible for typical shopping lists (< 1000 items)
- For very large lists (> 10,000 items), consider pagination

---

## Lessons Learned

1. **Always check data types when dealing with calculations**
   - Material quantity multiplication can quickly exceed expected ranges
   - Use BIGINT for any quantity-related fields in manufacturing systems

2. **Field name consistency is critical**
   - Using `mode` vs `build_decision` caused silent failures
   - Consider TypeScript interfaces to catch these at compile time

3. **Test with real-world data**
   - Edge cases (like Titanium Chromide) often reveal hidden bugs
   - High-ME blueprints with large run counts stress-test the system

4. **UI simplification improves UX**
   - Collapsing secondary information helps users focus on primary tasks
   - Default state should optimize for most common workflow

---

## Developer Notes

### Running the Application

**Backend:**
```bash
cd /home/cytrex/eve_copilot
/home/cytrex/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd /home/cytrex/eve_copilot/frontend
npm run dev -- --host 0.0.0.0
```

**Access:**
- Frontend: http://77.24.99.81:5173
- Backend: http://77.24.99.81:8000
- API Docs: http://77.24.99.81:8000/docs

### Database Connection
```bash
echo 'Aug2012#' | sudo -S docker exec eve_db psql -U eve -d eve_sde
```

### Useful Queries

**Check item quantities:**
```sql
SELECT id, item_name, quantity, is_product, build_decision
FROM shopping_list_items
WHERE list_id = 18 AND quantity > 1000000000
ORDER BY quantity DESC;
```

**Check regional comparison items:**
```bash
curl http://localhost:8000/api/shopping/lists/18/regional-comparison | \
  python3 -c "import json,sys; data=json.load(sys.stdin); print(f'Items: {len(data[\"items\"])}')"
```

---

## Session End State

- ✅ All changes committed and pushed to GitHub
- ✅ Backend running on port 8000
- ✅ Frontend running on port 5173
- ✅ Database migration applied
- ✅ Documentation updated
- ✅ No pending changes in git

**Repository:** https://github.com/CytrexSGR/Eve-Online-Copilot
**Branch:** main
**Latest Commit:** 8bb16ac - feat: make region totals summary collapsible
