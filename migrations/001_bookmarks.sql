-- migrations/001_bookmarks.sql
-- Bookmark System for EVE Co-Pilot

-- Characters table (links to ESI character data)
CREATE TABLE IF NOT EXISTS characters (
    character_id INTEGER PRIMARY KEY,
    character_name VARCHAR(255) NOT NULL,
    corporation_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert known characters
INSERT INTO characters (character_id, character_name, corporation_id) VALUES
    (526379435, 'Artallus', 98785281),
    (1117367444, 'Cytrex', 98785281),
    (110592475, 'Cytricia', 98785281)
ON CONFLICT (character_id) DO NOTHING;

-- Corporations table
CREATE TABLE IF NOT EXISTS corporations (
    corporation_id INTEGER PRIMARY KEY,
    corporation_name VARCHAR(255) NOT NULL,
    ticker VARCHAR(10),
    ceo_id INTEGER,
    home_system_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert Minimal Industries (home system: Isikemi = 30001365)
INSERT INTO corporations (corporation_id, corporation_name, ticker, ceo_id, home_system_id) VALUES
    (98785281, 'Minimal Industries', 'MINDI', 1117367444, 30001365)
ON CONFLICT (corporation_id) DO NOTHING;

-- Bookmarks table
CREATE TABLE IF NOT EXISTS bookmarks (
    id SERIAL PRIMARY KEY,
    type_id INTEGER NOT NULL,
    item_name VARCHAR(255),
    character_id INTEGER REFERENCES characters(character_id),
    corporation_id INTEGER REFERENCES corporations(corporation_id),
    notes TEXT,
    tags VARCHAR(50)[],
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bookmarks_character ON bookmarks(character_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_corporation ON bookmarks(corporation_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_type ON bookmarks(type_id);

-- Bookmark lists (folders/categories)
CREATE TABLE IF NOT EXISTS bookmark_lists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    character_id INTEGER REFERENCES characters(character_id),
    corporation_id INTEGER REFERENCES corporations(corporation_id),
    is_shared BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bookmark list membership
CREATE TABLE IF NOT EXISTS bookmark_list_items (
    list_id INTEGER REFERENCES bookmark_lists(id) ON DELETE CASCADE,
    bookmark_id INTEGER REFERENCES bookmarks(id) ON DELETE CASCADE,
    position INTEGER DEFAULT 0,
    PRIMARY KEY (list_id, bookmark_id)
);
