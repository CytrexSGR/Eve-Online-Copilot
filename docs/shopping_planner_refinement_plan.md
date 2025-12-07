# Shopping Planner Refinement - Implementation Plan

## Design Decisions (from Brainstorming)

### Core Concept
- **Product = Blueprint** (1:1 Beziehung)
- Items mit Blueprint in `industryActivityProducts` sind automatisch Produkte
- Items ohne Blueprint sind reine Einkaufsartikel (Materials)

### Workflow
1. Market Scanner → User wählt Item
2. "Add to Shopping List" → System prüft ob Blueprint existiert
3. Falls Blueprint: Item wird als Product markiert, User kann Runs setzen
4. "Calculate Materials" Button → Materials werden berechnet und als Child-Items hinzugefügt
5. Bei Sub-Products (Materials die selbst Blueprints haben): Modal zur Auswahl Buy/Build

### Entscheidungen
| Frage | Entscheidung |
|-------|--------------|
| Material-Berechnung | **Manuell** - Button "Calculate Materials" |
| Bei Runs-Änderung | **Überschreiben** - Alte Materials löschen, neu berechnen |
| Material-Darstellung | **Gruppiert** - Materials unter ihrem Parent-Product |
| Sub-Products | **User entscheidet** - Buy or Build Auswahl |
| Sub-Product UI | **Modal** - Nach Calculate, zeigt Sub-Products mit Checkboxen |
| ME Level | **Per Product editierbar** - Default 10, User kann ändern |

---

## Database Schema Updates

### Neue Spalten in `shopping_list_items`
```sql
-- Bereits vorhanden: is_product, runs, me_level, parent_item_id

-- Neu hinzufügen:
ALTER TABLE shopping_list_items
ADD COLUMN IF NOT EXISTS build_decision VARCHAR(10) DEFAULT NULL;
-- Werte: NULL (nicht relevant), 'buy', 'build'

COMMENT ON COLUMN shopping_list_items.build_decision IS
'For sub-products: user decision to buy or build. NULL for top-level products and pure materials.';
```

---

## Implementation Tasks

### Task 1: Backend - Calculate Materials Endpoint
**File:** `routers/shopping.py`

```python
@router.post("/items/{item_id}/calculate-materials")
async def calculate_materials(item_id: int):
    """
    Calculate and add materials for a product item.
    Returns list of materials including sub-products for user decision.
    """
    result = shopping_service.calculate_materials(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found or not a product")
    return result
```

**Response Format:**
```json
{
    "product": {
        "id": 123,
        "type_id": 11393,
        "item_name": "Caracal Navy Issue",
        "runs": 1,
        "me_level": 10,
        "output_per_run": 1
    },
    "materials": [
        {
            "type_id": 34,
            "item_name": "Tritanium",
            "quantity": 1500000,
            "has_blueprint": false
        },
        {
            "type_id": 11399,
            "item_name": "Morphite",
            "quantity": 500,
            "has_blueprint": false
        }
    ],
    "sub_products": [
        {
            "type_id": 11478,
            "item_name": "Gravimetric Sensor Cluster",
            "quantity": 50,
            "has_blueprint": true,
            "default_decision": "buy"
        }
    ]
}
```

### Task 2: Backend - Shopping Service calculate_materials()
**File:** `shopping_service.py`

```python
def calculate_materials(self, item_id: int) -> dict:
    """
    Calculate materials for a product.

    1. Get product details (type_id, runs, me_level)
    2. Get blueprint materials from industryActivityMaterials
    3. Apply ME formula: ceil(base_quantity * runs * (1 - me_level/100))
    4. Check each material for blueprint (= sub-product)
    5. Return materials and sub-products separately
    """
    # Implementation details in code
```

**ME Formula:**
```python
def calculate_material_quantity(base_quantity: int, runs: int, me_level: int) -> int:
    """
    EVE Online ME formula for manufacturing.
    ME 0 = 100% materials, ME 10 = 90% materials
    """
    me_modifier = 1 - (me_level / 100)
    return math.ceil(base_quantity * runs * me_modifier)
```

### Task 3: Backend - Apply Materials Endpoint
**File:** `routers/shopping.py`

```python
class ApplyMaterialsRequest(BaseModel):
    materials: List[dict]  # [{type_id, quantity}]
    sub_product_decisions: List[dict]  # [{type_id, decision: 'buy'|'build'}]

@router.post("/items/{item_id}/apply-materials")
async def apply_materials(item_id: int, request: ApplyMaterialsRequest):
    """
    Apply calculated materials to shopping list.
    - Deletes existing child materials
    - Adds new materials with parent_item_id
    - For sub-products marked 'build': recursively calculate their materials
    """
    result = shopping_service.apply_materials(
        item_id,
        request.materials,
        request.sub_product_decisions
    )
    return result
```

### Task 4: Backend - Shopping Service apply_materials()
**File:** `shopping_service.py`

```python
def apply_materials(self, parent_id: int, materials: list, sub_decisions: list) -> dict:
    """
    1. Delete existing materials for this parent (WHERE parent_item_id = parent_id)
    2. For each material:
       - If sub-product with decision='build':
         - Add as product (is_product=True, build_decision='build')
         - Recursively calculate its materials (with default ME=10)
       - If sub-product with decision='buy':
         - Add as material (is_product=False, build_decision='buy')
       - If regular material:
         - Add as material (is_product=False, build_decision=NULL)
    3. Return updated shopping list
    """
```

### Task 5: Backend - Get Products with Materials
**File:** `shopping_service.py`

Extend `get_list_with_items()` to return hierarchical structure:

```python
def get_list_with_items(self, list_id: int) -> dict:
    """
    Returns:
    {
        "id": 1,
        "name": "My List",
        "products": [
            {
                "id": 123,
                "type_id": 11393,
                "item_name": "Caracal Navy Issue",
                "runs": 1,
                "me_level": 10,
                "output_per_run": 1,
                "materials_calculated": true,
                "materials": [
                    {"id": 124, "type_id": 34, "item_name": "Tritanium", "quantity": 1500000},
                    ...
                ],
                "sub_products": [
                    {
                        "id": 125,
                        "type_id": 11478,
                        "item_name": "Sensor Cluster",
                        "build_decision": "build",
                        "runs": 50,
                        "me_level": 10,
                        "materials": [...]
                    }
                ]
            }
        ],
        "standalone_items": [
            // Items without parent and without blueprint
        ]
    }
    """
```

### Task 6: Frontend - Products Section Redesign
**File:** `frontend/src/pages/ShoppingPlanner.tsx`

```typescript
// New interfaces
interface Material {
    id: number;
    type_id: number;
    item_name: string;
    quantity: number;
    is_purchased: boolean;
}

interface SubProduct {
    id: number;
    type_id: number;
    item_name: string;
    build_decision: 'buy' | 'build';
    runs: number;
    me_level: number;
    materials: Material[];
}

interface Product {
    id: number;
    type_id: number;
    item_name: string;
    runs: number;
    me_level: number;
    output_per_run: number;
    materials_calculated: boolean;
    materials: Material[];
    sub_products: SubProduct[];
}

interface ShoppingListData {
    id: number;
    name: string;
    products: Product[];
    standalone_items: ShoppingItem[];
}
```

### Task 7: Frontend - Calculate Materials Button & Modal
**File:** `frontend/src/pages/ShoppingPlanner.tsx`

```typescript
// State for modal
const [showSubProductModal, setShowSubProductModal] = useState(false);
const [pendingMaterials, setPendingMaterials] = useState<CalculateMaterialsResponse | null>(null);
const [subProductDecisions, setSubProductDecisions] = useState<Record<number, 'buy' | 'build'>>({});

// Calculate Materials handler
const handleCalculateMaterials = async (itemId: number) => {
    const response = await fetch(`/api/shopping/items/${itemId}/calculate-materials`, {
        method: 'POST'
    });
    const data = await response.json();

    if (data.sub_products.length > 0) {
        // Show modal for sub-product decisions
        setPendingMaterials(data);
        // Default all to 'buy'
        const defaults: Record<number, 'buy' | 'build'> = {};
        data.sub_products.forEach(sp => defaults[sp.type_id] = 'buy');
        setSubProductDecisions(defaults);
        setShowSubProductModal(true);
    } else {
        // No sub-products, apply directly
        await applyMaterials(itemId, data.materials, []);
    }
};

// Modal component
const SubProductModal = () => (
    <div className="modal">
        <h3>Sub-Components Found</h3>
        <p>These materials can be built from blueprints. Choose for each:</p>
        {pendingMaterials?.sub_products.map(sp => (
            <div key={sp.type_id} className="sub-product-row">
                <span>{sp.item_name} x{sp.quantity}</span>
                <select
                    value={subProductDecisions[sp.type_id]}
                    onChange={e => setSubProductDecisions({
                        ...subProductDecisions,
                        [sp.type_id]: e.target.value as 'buy' | 'build'
                    })}
                >
                    <option value="buy">Buy</option>
                    <option value="build">Build</option>
                </select>
            </div>
        ))}
        <button onClick={handleApplyWithDecisions}>Apply</button>
    </div>
);
```

### Task 8: Frontend - Hierarchical Product Display
**File:** `frontend/src/pages/ShoppingPlanner.tsx`

```typescript
// Product card with expandable materials
const ProductCard = ({ product }: { product: Product }) => {
    const [expanded, setExpanded] = useState(false);

    return (
        <div className="product-card">
            <div className="product-header">
                <span className="product-name">{product.item_name}</span>
                <div className="product-controls">
                    <input
                        type="number"
                        value={product.runs}
                        onChange={e => handleUpdateRuns(product.id, parseInt(e.target.value))}
                        min={1}
                    />
                    <span>runs × {product.output_per_run} = {product.runs * product.output_per_run}</span>
                    <input
                        type="number"
                        value={product.me_level}
                        onChange={e => handleUpdateME(product.id, parseInt(e.target.value))}
                        min={0}
                        max={10}
                    />
                    <span>ME</span>
                </div>
                <button onClick={() => handleCalculateMaterials(product.id)}>
                    {product.materials_calculated ? 'Recalculate' : 'Calculate Materials'}
                </button>
            </div>

            {product.materials_calculated && (
                <div className="materials-section">
                    <button onClick={() => setExpanded(!expanded)}>
                        {expanded ? '▼' : '▶'} Materials ({product.materials.length})
                    </button>
                    {expanded && (
                        <ul className="materials-list">
                            {product.materials.map(mat => (
                                <li key={mat.id} className={mat.is_purchased ? 'purchased' : ''}>
                                    {mat.item_name}: {mat.quantity.toLocaleString()}
                                </li>
                            ))}
                        </ul>
                    )}

                    {product.sub_products.length > 0 && (
                        <div className="sub-products">
                            <h4>Sub-Components (Build)</h4>
                            {product.sub_products
                                .filter(sp => sp.build_decision === 'build')
                                .map(sp => (
                                    <ProductCard key={sp.id} product={sp} />
                                ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};
```

### Task 9: Database Migration
**File:** `migrations/005_shopping_refinement.sql`

```sql
-- Add build_decision column
ALTER TABLE shopping_list_items
ADD COLUMN IF NOT EXISTS build_decision VARCHAR(10) DEFAULT NULL;

-- Add index for parent lookups
CREATE INDEX IF NOT EXISTS idx_shopping_items_parent
ON shopping_list_items(parent_item_id) WHERE parent_item_id IS NOT NULL;

-- Add index for products
CREATE INDEX IF NOT EXISTS idx_shopping_items_products
ON shopping_list_items(list_id, is_product) WHERE is_product = TRUE;
```

### Task 10: Integration Test
1. Add product to shopping list (e.g., Caracal Navy Issue)
2. Verify it's marked as is_product=True
3. Set runs=2, ME=10
4. Click "Calculate Materials"
5. Verify materials appear with correct quantities
6. If sub-products exist, verify modal appears
7. Select "Build" for one sub-product
8. Verify recursive material calculation
9. Change runs to 5, recalculate
10. Verify old materials replaced with new quantities

---

## Task Order & Dependencies

```
Task 9 (Migration)
    ↓
Task 2 (calculate_materials service)
    ↓
Task 1 (calculate-materials endpoint)
    ↓
Task 4 (apply_materials service)
    ↓
Task 3 (apply-materials endpoint)
    ↓
Task 5 (hierarchical get_list_with_items)
    ↓
Task 6 (Frontend interfaces)
    ↓
Task 7 (Calculate button & modal)
    ↓
Task 8 (Hierarchical display)
    ↓
Task 10 (Integration test)
```

---

## Future Enhancements (Phase 2)
- Show available blueprints from ESI as ME reference
- Blueprint inventory integration
- Copy vs Original tracking
- Automatic ME suggestion based on best available blueprint
