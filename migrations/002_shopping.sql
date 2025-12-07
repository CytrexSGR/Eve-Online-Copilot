-- migrations/002_shopping.sql
-- Shopping Lists for EVE Co-Pilot

CREATE TABLE IF NOT EXISTS shopping_lists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    character_id INTEGER REFERENCES characters(character_id),
    corporation_id INTEGER REFERENCES corporations(corporation_id),
    status VARCHAR(50) DEFAULT 'planning',  -- planning, shopping, complete
    total_cost DECIMAL(20, 2),
    total_volume DECIMAL(20, 2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS shopping_list_items (
    id SERIAL PRIMARY KEY,
    list_id INTEGER REFERENCES shopping_lists(id) ON DELETE CASCADE,
    type_id INTEGER NOT NULL,
    item_name VARCHAR(255),
    quantity INTEGER NOT NULL,
    target_region VARCHAR(50),
    target_price DECIMAL(20, 2),
    actual_price DECIMAL(20, 2),
    is_purchased BOOLEAN DEFAULT FALSE,
    purchased_at TIMESTAMP,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_shopping_list_items_list ON shopping_list_items(list_id);
CREATE INDEX IF NOT EXISTS idx_shopping_lists_corp ON shopping_lists(corporation_id);
CREATE INDEX IF NOT EXISTS idx_shopping_lists_char ON shopping_lists(character_id);
