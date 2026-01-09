-- Migration 009: Fix Battle Tracking
-- Adds kill-battle association and fixes duplicate counting
--
-- Problems Fixed:
-- 1. Battle kill counts inflated 18.5x due to duplicate counting
-- 2. No way to verify which kills belong to which battle
-- 3. Cannot recalculate accurate battle statistics

BEGIN;

-- ============================================================
-- STEP 1: Add battle_id FK to killmails table
-- ============================================================
-- This creates the relationship between kills and battles

ALTER TABLE killmails
ADD COLUMN IF NOT EXISTS battle_id INTEGER REFERENCES battles(battle_id) ON DELETE SET NULL;

COMMENT ON COLUMN killmails.battle_id IS 'Associated battle ID (NULL if kill not part of a battle)';

-- Partial index for efficient battle queries (only index non-null values)
CREATE INDEX IF NOT EXISTS idx_killmails_battle_id
ON killmails(battle_id)
WHERE battle_id IS NOT NULL;

-- ============================================================
-- STEP 2: Create computed stats view
-- ============================================================
-- This view ALWAYS shows accurate battle statistics
-- by computing them from actual killmail data

DROP VIEW IF EXISTS battle_stats_computed;
CREATE VIEW battle_stats_computed AS
SELECT
    battle_id,
    COUNT(*) as actual_kills,
    COALESCE(SUM(ship_value), 0) as actual_isk_destroyed,
    COUNT(*) FILTER (WHERE is_capital = TRUE) as actual_capital_kills,
    MIN(killmail_time) as first_kill_time,
    MAX(killmail_time) as last_kill_time
FROM killmails
WHERE battle_id IS NOT NULL
GROUP BY battle_id;

COMMENT ON VIEW battle_stats_computed IS 'Computed battle statistics from actual killmail data - always accurate';

-- ============================================================
-- STEP 3: Create function to refresh battle stats
-- ============================================================
-- Called after each kill to update battle totals

CREATE OR REPLACE FUNCTION refresh_battle_stats(p_battle_id INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE battles b SET
        total_kills = COALESCE(s.actual_kills, 0),
        total_isk_destroyed = COALESCE(s.actual_isk_destroyed, 0),
        capital_kills = COALESCE(s.actual_capital_kills, 0),
        last_kill_at = COALESCE(s.last_kill_time, b.last_kill_at)
    FROM battle_stats_computed s
    WHERE b.battle_id = s.battle_id
    AND b.battle_id = p_battle_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_battle_stats(INTEGER) IS 'Update battle stats from computed view';

-- ============================================================
-- STEP 4: Create function to refresh ALL battle stats
-- ============================================================
-- Used for bulk reconciliation

CREATE OR REPLACE FUNCTION refresh_all_battle_stats()
RETURNS TABLE(battle_id INTEGER, old_kills INTEGER, new_kills BIGINT, diff BIGINT) AS $$
BEGIN
    RETURN QUERY
    WITH updates AS (
        UPDATE battles b SET
            total_kills = COALESCE(s.actual_kills, 0),
            total_isk_destroyed = COALESCE(s.actual_isk_destroyed, 0),
            capital_kills = COALESCE(s.actual_capital_kills, 0)
        FROM battle_stats_computed s
        WHERE b.battle_id = s.battle_id
        RETURNING b.battle_id, b.total_kills as old_kills, s.actual_kills as new_kills
    )
    SELECT u.battle_id, u.old_kills::INTEGER, u.new_kills, (u.old_kills - u.new_kills) as diff
    FROM updates u
    WHERE u.old_kills != u.new_kills;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_all_battle_stats() IS 'Bulk refresh all battle stats, returns changed battles';

-- ============================================================
-- STEP 5: Add kill processing log for deduplication tracking
-- ============================================================
-- Tracks which kills have been processed to prevent duplicates

CREATE TABLE IF NOT EXISTS kill_processing_log (
    killmail_id BIGINT PRIMARY KEY,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'redisq',  -- redisq, backfill, manual
    battle_id INTEGER REFERENCES battles(battle_id) ON DELETE SET NULL
);

COMMENT ON TABLE kill_processing_log IS 'Tracks processed killmails for deduplication';

CREATE INDEX IF NOT EXISTS idx_kpl_processed_at
ON kill_processing_log(processed_at DESC);

CREATE INDEX IF NOT EXISTS idx_kpl_source
ON kill_processing_log(source);

-- ============================================================
-- STEP 6: Associate existing kills with battles (data fix)
-- ============================================================
-- Links existing killmails to battles based on time/location match

UPDATE killmails k SET battle_id = matched.battle_id
FROM (
    SELECT DISTINCT ON (km.killmail_id)
        km.killmail_id,
        b.battle_id
    FROM killmails km
    JOIN battles b ON b.solar_system_id = km.solar_system_id
    WHERE km.battle_id IS NULL
    AND km.killmail_time >= b.started_at
    AND km.killmail_time <= COALESCE(b.ended_at, b.last_kill_at + INTERVAL '30 minutes')
    ORDER BY km.killmail_id, b.started_at DESC
) matched
WHERE k.killmail_id = matched.killmail_id;

-- ============================================================
-- STEP 7: Recalculate ALL battle stats from actual kills
-- ============================================================
-- This fixes the inflated kill counts

UPDATE battles b SET
    total_kills = COALESCE(s.actual_kills, 0),
    total_isk_destroyed = COALESCE(s.actual_isk_destroyed, 0),
    capital_kills = COALESCE(s.actual_capital_kills, 0)
FROM battle_stats_computed s
WHERE b.battle_id = s.battle_id;

-- Set battles with no associated kills to 0
UPDATE battles SET
    total_kills = 0,
    total_isk_destroyed = 0,
    capital_kills = 0
WHERE battle_id NOT IN (SELECT DISTINCT battle_id FROM battle_stats_computed);

-- ============================================================
-- STEP 8: Add composite index for hotspot detection
-- ============================================================
-- Optimizes the query: SELECT COUNT(*) FROM killmails WHERE system_id = X AND time > Y

CREATE INDEX IF NOT EXISTS idx_killmails_system_time_desc
ON killmails(solar_system_id, killmail_time DESC);

-- ============================================================
-- STEP 9: Add unique constraint to prevent race conditions
-- ============================================================
-- Ensures only one active battle per system at a time

CREATE UNIQUE INDEX IF NOT EXISTS idx_battles_active_system_unique
ON battles(solar_system_id)
WHERE status = 'active';

COMMIT;

-- ============================================================
-- Verification Queries (run after migration)
-- ============================================================
--
-- Check battle stats match actual kills:
-- SELECT b.battle_id, b.total_kills, s.actual_kills,
--        ABS(b.total_kills - s.actual_kills) as diff
-- FROM battles b
-- LEFT JOIN battle_stats_computed s ON b.battle_id = s.battle_id
-- WHERE COALESCE(b.total_kills, 0) != COALESCE(s.actual_kills, 0)
-- ORDER BY diff DESC;
--
-- Check how many kills are associated with battles:
-- SELECT
--     COUNT(*) FILTER (WHERE battle_id IS NOT NULL) as kills_with_battle,
--     COUNT(*) FILTER (WHERE battle_id IS NULL) as kills_without_battle,
--     COUNT(*) as total_kills
-- FROM killmails;
