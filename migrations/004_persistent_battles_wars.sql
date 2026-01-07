-- Migration 004: Persistent Battle & War System
-- Stores all killmails, battles, and alliance wars permanently in PostgreSQL

-- =============================================
-- 1. KILLMAILS - Permanent storage of all kills
-- =============================================

CREATE TABLE IF NOT EXISTS killmails (
    killmail_id BIGINT PRIMARY KEY,
    killmail_time TIMESTAMP NOT NULL,
    solar_system_id BIGINT NOT NULL,
    region_id BIGINT,

    -- Ship/Victim Info
    ship_type_id INTEGER,
    ship_value BIGINT DEFAULT 0,

    -- Victim Details
    victim_character_id BIGINT,
    victim_corporation_id BIGINT,
    victim_alliance_id BIGINT,

    -- Attack Details
    attacker_count INTEGER DEFAULT 1,
    final_blow_character_id BIGINT,
    final_blow_corporation_id BIGINT,
    final_blow_alliance_id BIGINT,

    -- Combat Type
    is_solo BOOLEAN DEFAULT FALSE,
    is_npc BOOLEAN DEFAULT FALSE,
    is_capital BOOLEAN DEFAULT FALSE,

    -- Metadata
    zkb_points INTEGER,
    zkb_npc BOOLEAN DEFAULT FALSE,
    zkb_awox BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE killmails IS 'Permanent storage of all killmails with core data';

-- Indexes for killmails
CREATE INDEX IF NOT EXISTS idx_killmail_time ON killmails(killmail_time DESC);
CREATE INDEX IF NOT EXISTS idx_solar_system ON killmails(solar_system_id, killmail_time DESC);
CREATE INDEX IF NOT EXISTS idx_region ON killmails(region_id, killmail_time DESC);
CREATE INDEX IF NOT EXISTS idx_victim_alliance ON killmails(victim_alliance_id, killmail_time DESC);
CREATE INDEX IF NOT EXISTS idx_ship_type ON killmails(ship_type_id);
CREATE INDEX IF NOT EXISTS idx_capital ON killmails(is_capital, killmail_time DESC) WHERE is_capital = TRUE;


-- =============================================
-- 2. KILLMAIL ITEMS - Destroyed/Dropped items
-- =============================================

CREATE TABLE IF NOT EXISTS killmail_items (
    id SERIAL PRIMARY KEY,
    killmail_id BIGINT NOT NULL REFERENCES killmails(killmail_id) ON DELETE CASCADE,
    item_type_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    was_destroyed BOOLEAN NOT NULL,
    flag INTEGER,
    singleton INTEGER
);

COMMENT ON TABLE killmail_items IS 'Items destroyed or dropped in each killmail';

-- Indexes for killmail_items
CREATE INDEX IF NOT EXISTS idx_km_items_killmail ON killmail_items(killmail_id);
CREATE INDEX IF NOT EXISTS idx_km_items_type ON killmail_items(item_type_id);
CREATE INDEX IF NOT EXISTS idx_km_items_destroyed ON killmail_items(was_destroyed, item_type_id);


-- =============================================
-- 3. KILLMAIL ATTACKERS - Who was involved
-- =============================================

CREATE TABLE IF NOT EXISTS killmail_attackers (
    id SERIAL PRIMARY KEY,
    killmail_id BIGINT NOT NULL REFERENCES killmails(killmail_id) ON DELETE CASCADE,
    character_id BIGINT,
    corporation_id BIGINT,
    alliance_id BIGINT,
    ship_type_id INTEGER,
    weapon_type_id INTEGER,
    damage_done INTEGER,
    is_final_blow BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE killmail_attackers IS 'All attackers involved in each killmail';

-- Indexes for killmail_attackers
CREATE INDEX IF NOT EXISTS idx_km_attackers_killmail ON killmail_attackers(killmail_id);
CREATE INDEX IF NOT EXISTS idx_km_attackers_alliance ON killmail_attackers(alliance_id);
CREATE INDEX IF NOT EXISTS idx_km_attackers_corporation ON killmail_attackers(corporation_id);


-- =============================================
-- 4. BATTLES - Combat hotspot tracking
-- =============================================

CREATE TABLE IF NOT EXISTS battles (
    battle_id SERIAL PRIMARY KEY,
    solar_system_id BIGINT NOT NULL,
    region_id BIGINT,

    -- Timeline
    started_at TIMESTAMP NOT NULL,
    last_kill_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    duration_minutes INTEGER,

    -- Statistics
    total_kills INTEGER DEFAULT 0,
    total_isk_destroyed BIGINT DEFAULT 0,
    capital_kills INTEGER DEFAULT 0,

    -- Status
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'ended')),

    -- Telegram Integration
    telegram_message_id BIGINT,
    telegram_last_update TIMESTAMP
);

COMMENT ON TABLE battles IS 'Combat hotspots and battle tracking';

-- Indexes for battles
CREATE INDEX IF NOT EXISTS idx_battles_system ON battles(solar_system_id);
CREATE INDEX IF NOT EXISTS idx_battles_status ON battles(status);
CREATE INDEX IF NOT EXISTS idx_battles_started ON battles(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_battles_active ON battles(solar_system_id, status) WHERE status = 'active';


-- =============================================
-- 5. BATTLE PARTICIPANTS - Who fought in battle
-- =============================================

CREATE TABLE IF NOT EXISTS battle_participants (
    id SERIAL PRIMARY KEY,
    battle_id INTEGER NOT NULL REFERENCES battles(battle_id) ON DELETE CASCADE,
    alliance_id BIGINT,
    corporation_id BIGINT,

    kills INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    isk_destroyed BIGINT DEFAULT 0,
    isk_lost BIGINT DEFAULT 0,

    UNIQUE(battle_id, alliance_id, corporation_id)
);

COMMENT ON TABLE battle_participants IS 'Alliance/Corp participation in battles';

-- Indexes for battle_participants
CREATE INDEX IF NOT EXISTS idx_bp_battle ON battle_participants(battle_id);
CREATE INDEX IF NOT EXISTS idx_bp_alliance ON battle_participants(alliance_id);


-- =============================================
-- 6. ALLIANCE WARS - Long-term conflicts
-- =============================================

CREATE TABLE IF NOT EXISTS alliance_wars (
    war_id SERIAL PRIMARY KEY,
    alliance_a_id BIGINT NOT NULL,
    alliance_b_id BIGINT NOT NULL,

    -- Timeline
    first_kill_at TIMESTAMP NOT NULL,
    last_kill_at TIMESTAMP NOT NULL,
    duration_days INTEGER,

    -- Status
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'ended', 'dormant')),

    -- Statistics (lifetime totals)
    total_kills INTEGER DEFAULT 0,
    total_isk_destroyed BIGINT DEFAULT 0,

    UNIQUE(alliance_a_id, alliance_b_id)
);

COMMENT ON TABLE alliance_wars IS 'Long-term alliance conflict tracking';

-- Indexes for alliance_wars
CREATE INDEX IF NOT EXISTS idx_wars_alliances ON alliance_wars(alliance_a_id, alliance_b_id);
CREATE INDEX IF NOT EXISTS idx_wars_status ON alliance_wars(status);
CREATE INDEX IF NOT EXISTS idx_wars_last_kill ON alliance_wars(last_kill_at DESC);


-- =============================================
-- 7. WAR DAILY STATS - Daily aggregation
-- =============================================

CREATE TABLE IF NOT EXISTS war_daily_stats (
    id SERIAL PRIMARY KEY,
    war_id INTEGER NOT NULL REFERENCES alliance_wars(war_id) ON DELETE CASCADE,
    date DATE NOT NULL,

    -- Alliance A Stats
    kills_by_a INTEGER DEFAULT 0,
    isk_destroyed_by_a BIGINT DEFAULT 0,

    -- Alliance B Stats
    kills_by_b INTEGER DEFAULT 0,
    isk_destroyed_by_b INTEGER DEFAULT 0,

    -- Systems active
    active_systems INTEGER DEFAULT 0,

    UNIQUE(war_id, date)
);

COMMENT ON TABLE war_daily_stats IS 'Daily statistics for alliance wars (for trend analysis)';

-- Indexes for war_daily_stats
CREATE INDEX IF NOT EXISTS idx_wds_war_date ON war_daily_stats(war_id, date DESC);


-- =============================================
-- 8. HELPER FUNCTIONS
-- =============================================

-- Function to update war duration
CREATE OR REPLACE FUNCTION update_war_duration()
RETURNS TRIGGER AS $$
BEGIN
    NEW.duration_days = EXTRACT(DAY FROM (NEW.last_kill_at - NEW.first_kill_at));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_war_duration ON alliance_wars;
CREATE TRIGGER trg_update_war_duration
    BEFORE UPDATE OF last_kill_at ON alliance_wars
    FOR EACH ROW
    EXECUTE FUNCTION update_war_duration();


-- Function to update battle duration
CREATE OR REPLACE FUNCTION update_battle_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.ended_at IS NOT NULL THEN
        NEW.duration_minutes = EXTRACT(EPOCH FROM (NEW.ended_at - NEW.started_at)) / 60;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_battle_duration ON battles;
CREATE TRIGGER trg_update_battle_duration
    BEFORE UPDATE OF ended_at ON battles
    FOR EACH ROW
    EXECUTE FUNCTION update_battle_duration();


-- =============================================
-- SUCCESS
-- =============================================

SELECT 'Migration 004: Persistent Battle & War System completed successfully!' AS status;
