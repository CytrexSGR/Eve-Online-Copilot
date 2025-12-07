-- Migration 005: Shopping Planner Refinement
-- Add build_decision and parent_item_id columns for hierarchical materials

-- Add parent_item_id column for material hierarchy
ALTER TABLE shopping_list_items
ADD COLUMN IF NOT EXISTS parent_item_id INTEGER REFERENCES shopping_list_items(id) ON DELETE CASCADE;

-- Add build_decision column
ALTER TABLE shopping_list_items
ADD COLUMN IF NOT EXISTS build_decision VARCHAR(10) DEFAULT NULL;

COMMENT ON COLUMN shopping_list_items.build_decision IS
'For sub-products: user decision to buy or build. Values: NULL, buy, build';

COMMENT ON COLUMN shopping_list_items.parent_item_id IS
'Reference to parent product item. Materials belong to their parent product.';

-- Add index for parent lookups (materials under products)
CREATE INDEX IF NOT EXISTS idx_shopping_items_parent
ON shopping_list_items(parent_item_id) WHERE parent_item_id IS NOT NULL;

-- Add index for products in list
CREATE INDEX IF NOT EXISTS idx_shopping_items_products
ON shopping_list_items(list_id, is_product) WHERE is_product = TRUE;

-- Add index for finding materials by parent
CREATE INDEX IF NOT EXISTS idx_shopping_items_list_parent
ON shopping_list_items(list_id, parent_item_id);
