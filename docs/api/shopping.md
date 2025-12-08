# Shopping Lists API

Manage shopping lists for production materials and items.

## Endpoints

### Create Shopping List

```http
POST /api/shopping/lists
```

**Request Body:**
```json
{
  "name": "T1 Frigate Production",
  "character_id": 526379435,
  "notes": "Materials for 10 Tristan builds"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "T1 Frigate Production",
  "character_id": 526379435,
  "corporation_id": null,
  "status": "active",
  "notes": "Materials for 10 Tristan builds",
  "created_at": "2025-12-08T10:00:00Z",
  "updated_at": "2025-12-08T10:00:00Z",
  "item_count": 0,
  "purchased_count": 0
}
```

---

### Get Shopping Lists

```http
GET /api/shopping/lists?character_id=526379435&status=active
```

**Query Parameters:**
- `character_id` (optional) - Filter by character
- `corporation_id` (optional) - Filter by corporation
- `status` (optional) - Filter by status (active/completed/archived)

**Response:**
```json
[
  {
    "id": 1,
    "name": "T1 Frigate Production",
    "character_id": 526379435,
    "status": "active",
    "item_count": 15,
    "purchased_count": 8,
    "created_at": "2025-12-08T10:00:00Z"
  }
]
```

---

### Get Shopping List Details

```http
GET /api/shopping/lists/{list_id}
```

**Response:**
```json
{
  "id": 1,
  "name": "T1 Frigate Production",
  "items": [
    {
      "id": 1,
      "type_id": 34,
      "item_name": "Tritanium",
      "quantity": 50000,
      "is_purchased": false,
      "is_product": false
    }
  ]
}
```

---

### Add Item to List

```http
POST /api/shopping/lists/{list_id}/items
```

**Request Body:**
```json
{
  "type_id": 34,
  "item_name": "Tritanium",
  "quantity": 50000,
  "is_product": false
}
```

---

### Add Production Materials to List

```http
POST /api/shopping/lists/{list_id}/add-production/{type_id}?quantity=10&me=10
```

**Query Parameters:**
- `quantity` (required) - Number of runs
- `me` (optional) - Material efficiency (0-10, default: 10)

**Description:** Automatically adds all required materials for manufacturing the specified item.

---

### Update Shopping List

```http
PATCH /api/shopping/lists/{list_id}
```

**Request Body:**
```json
{
  "status": "completed",
  "notes": "All materials purchased"
}
```

---

### Delete Shopping List

```http
DELETE /api/shopping/lists/{list_id}
```

**Response:** `204 No Content`

---

## Shopping List Workflow

1. **Create list** - POST `/api/shopping/lists`
2. **Add production materials** - POST `/api/shopping/lists/{id}/add-production/{type_id}`
3. **Compare prices** - GET `/api/market/compare/{type_id}` for each item
4. **Mark as purchased** - PATCH `/api/shopping/lists/{id}/items/{item_id}`
5. **Complete list** - PATCH `/api/shopping/lists/{id}` with status "completed"

## Business Logic

### Material Hierarchy

Shopping lists support hierarchical materials:

```
Product (is_product=true)
├── Material 1 (parent_item_id=product_id)
├── Material 2
└── Sub-Product (is_product=true, parent_item_id=product_id)
    ├── Sub-Material 1 (parent_item_id=sub_product_id)
    └── Sub-Material 2
```

### Price Comparison

Use market API to find best prices:

```http
GET /api/market/compare/{type_id}?regions=10000002,10000043
```

Returns prices across multiple regions with route planning.
