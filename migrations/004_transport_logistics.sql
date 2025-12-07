-- Migration 004: Transport & Logistics
-- Extend shopping_list_items for product tracking and cargo calculation

-- Add new columns to shopping_list_items
ALTER TABLE shopping_list_items
    ADD COLUMN IF NOT EXISTS is_product BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS runs INT DEFAULT 1,
    ADD COLUMN IF NOT EXISTS me_level INT DEFAULT 10,
    ADD COLUMN IF NOT EXISTS te_level INT DEFAULT 20,
    ADD COLUMN IF NOT EXISTS volume_per_unit NUMERIC(20,4),
    ADD COLUMN IF NOT EXISTS total_volume NUMERIC(20,2);

-- Add comments
COMMENT ON COLUMN shopping_list_items.is_product IS 'TRUE = Endprodukt (hat Blueprint), FALSE = Material';
COMMENT ON COLUMN shopping_list_items.runs IS 'Anzahl Production Runs (nur für Produkte)';
COMMENT ON COLUMN shopping_list_items.me_level IS 'Material Efficiency des Blueprints (0-10)';
COMMENT ON COLUMN shopping_list_items.te_level IS 'Time Efficiency des Blueprints (0-20)';
COMMENT ON COLUMN shopping_list_items.volume_per_unit IS 'Volumen pro Einheit in m³';
COMMENT ON COLUMN shopping_list_items.total_volume IS 'Gesamtvolumen in m³ (quantity * volume_per_unit)';

-- Create character_capabilities table
CREATE TABLE IF NOT EXISTS character_capabilities (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    character_name VARCHAR(255),
    type_id INT NOT NULL,
    ship_name VARCHAR(255),
    ship_group VARCHAR(100),
    cargo_capacity FLOAT,
    location_id BIGINT,
    location_name VARCHAR(255),
    can_fly BOOLEAN DEFAULT FALSE,
    missing_skills JSONB,
    last_synced TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_char_ship_location UNIQUE (character_id, type_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_char_capabilities_char ON character_capabilities(character_id);
CREATE INDEX IF NOT EXISTS idx_char_capabilities_location ON character_capabilities(location_id);
CREATE INDEX IF NOT EXISTS idx_char_capabilities_can_fly ON character_capabilities(can_fly);

-- Update existing items with volume from SDE
UPDATE shopping_list_items sli
SET volume_per_unit = t."volume",
    total_volume = sli.quantity * t."volume"
FROM "invTypes" t
WHERE sli.type_id = t."typeID"
  AND sli.volume_per_unit IS NULL;
