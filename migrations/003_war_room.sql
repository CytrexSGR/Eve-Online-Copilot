-- migrations/003_war_room.sql
-- War Room feature: combat analysis and conflict tracking

-- System-to-region mapping cache (for fast lookups)
CREATE TABLE IF NOT EXISTS system_region_map (
    solar_system_id INTEGER PRIMARY KEY,
    solar_system_name VARCHAR(100),
    region_id INTEGER NOT NULL,
    region_name VARCHAR(100),
    constellation_id INTEGER,
    security_status FLOAT
);

CREATE INDEX IF NOT EXISTS idx_srm_region ON system_region_map(region_id);

-- Daily ship losses aggregated by system
CREATE TABLE IF NOT EXISTS combat_ship_losses (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    region_id INTEGER NOT NULL,
    solar_system_id INTEGER NOT NULL,
    ship_type_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    total_value_destroyed NUMERIC(20,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, solar_system_id, ship_type_id)
);

CREATE INDEX IF NOT EXISTS idx_csl_date_region ON combat_ship_losses(date, region_id);
CREATE INDEX IF NOT EXISTS idx_csl_ship ON combat_ship_losses(ship_type_id);
CREATE INDEX IF NOT EXISTS idx_csl_system ON combat_ship_losses(solar_system_id);

-- Daily item/module losses aggregated by system
CREATE TABLE IF NOT EXISTS combat_item_losses (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    region_id INTEGER NOT NULL,
    solar_system_id INTEGER NOT NULL,
    item_type_id INTEGER NOT NULL,
    quantity_destroyed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, solar_system_id, item_type_id)
);

CREATE INDEX IF NOT EXISTS idx_cil_date_region ON combat_item_losses(date, region_id);
CREATE INDEX IF NOT EXISTS idx_cil_item ON combat_item_losses(item_type_id);

-- Alliance conflict tracking (who fights whom)
CREATE TABLE IF NOT EXISTS alliance_conflicts (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    alliance_a INTEGER NOT NULL,
    alliance_b INTEGER NOT NULL,
    kill_count INTEGER NOT NULL DEFAULT 0,
    region_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, alliance_a, alliance_b)
);

CREATE INDEX IF NOT EXISTS idx_ac_date ON alliance_conflicts(date);
CREATE INDEX IF NOT EXISTS idx_ac_alliances ON alliance_conflicts(alliance_a, alliance_b);

-- Sovereignty campaign snapshots
CREATE TABLE IF NOT EXISTS sovereignty_campaigns (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER UNIQUE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    solar_system_id INTEGER NOT NULL,
    constellation_id INTEGER,
    defender_id INTEGER,
    defender_name VARCHAR(100),
    attacker_score FLOAT,
    defender_score FLOAT,
    start_time TIMESTAMP NOT NULL,
    structure_id BIGINT,
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sc_start ON sovereignty_campaigns(start_time);
CREATE INDEX IF NOT EXISTS idx_sc_system ON sovereignty_campaigns(solar_system_id);

-- Faction Warfare system status
CREATE TABLE IF NOT EXISTS fw_system_status (
    id SERIAL PRIMARY KEY,
    solar_system_id INTEGER NOT NULL,
    owner_faction_id INTEGER NOT NULL,
    occupier_faction_id INTEGER NOT NULL,
    contested VARCHAR(20) NOT NULL,
    victory_points INTEGER NOT NULL,
    victory_points_threshold INTEGER NOT NULL,
    snapshot_time TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fws_system ON fw_system_status(solar_system_id);
CREATE INDEX IF NOT EXISTS idx_fws_time ON fw_system_status(snapshot_time DESC);
