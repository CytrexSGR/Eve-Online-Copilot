-- Migration 007: Add ship_class column to killmails
-- Stores pre-computed ship classification for performance

-- =============================================
-- 1. Add ship_class column
-- =============================================

ALTER TABLE killmails
ADD COLUMN IF NOT EXISTS ship_class VARCHAR(20);

COMMENT ON COLUMN killmails.ship_class IS 'Pre-computed ship classification: capital, battleship, battlecruiser, cruiser, destroyer, frigate, logistics, stealth_bomber, hauler, industrial, mining, capsule, other';

-- =============================================
-- 2. Create index for ship_class queries
-- =============================================

CREATE INDEX IF NOT EXISTS idx_ship_class ON killmails(ship_class, killmail_time DESC);
CREATE INDEX IF NOT EXISTS idx_system_ship_class ON killmails(solar_system_id, ship_class, killmail_time DESC);
CREATE INDEX IF NOT EXISTS idx_region_ship_class ON killmails(region_id, ship_class, killmail_time DESC);

-- =============================================
-- 3. Backfill ship_class for existing killmails
-- =============================================

UPDATE killmails k
SET ship_class = CASE
    -- Capsules
    WHEN t."groupID" = 29 THEN 'capsule'
    -- Capitals (Titans, Supercarriers, Carriers, Dreads, FAX)
    WHEN t."groupID" IN (30, 659, 547, 485, 1538) THEN 'capital'
    -- Battleships (BS, Black Ops, Marauders)
    WHEN t."groupID" IN (27, 898, 900) THEN 'battleship'
    -- Battlecruisers (BC, Command Ships)
    WHEN t."groupID" IN (419, 540) THEN 'battlecruiser'
    -- Cruisers (Cruisers, HACs, Recons, etc)
    WHEN t."groupID" IN (26, 358, 894, 906, 963) THEN 'cruiser'
    -- Destroyers (Destroyers, Interdictors, Tactical Destroyers)
    WHEN t."groupID" IN (420, 541, 1305) THEN 'destroyer'
    -- Frigates (Frigates, AFs, Interceptors, etc)
    WHEN t."groupID" IN (25, 324, 831, 893) THEN 'frigate'
    -- Logistics
    WHEN t."groupID" = 832 THEN 'logistics'
    -- Stealth Bombers
    WHEN t."groupID" = 834 THEN 'stealth_bomber'
    -- Freighters
    WHEN t."groupID" IN (513, 902) THEN 'hauler'
    -- Industrials and Mining Barges
    WHEN t."groupID" IN (28, 463) THEN 'industrial'
    -- Exhumers
    WHEN t."groupID" = 543 THEN 'mining'
    ELSE 'other'
END
FROM "invTypes" t
WHERE k.ship_type_id = t."typeID"
  AND k.ship_class IS NULL;

-- =============================================
-- 4. Verify migration
-- =============================================

DO $$
DECLARE
    total_killmails INTEGER;
    classified_killmails INTEGER;
    null_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_killmails FROM killmails;
    SELECT COUNT(*) INTO classified_killmails FROM killmails WHERE ship_class IS NOT NULL;
    SELECT COUNT(*) INTO null_count FROM killmails WHERE ship_class IS NULL;

    RAISE NOTICE 'Migration 007 Statistics:';
    RAISE NOTICE '  Total killmails: %', total_killmails;
    RAISE NOTICE '  Classified: %', classified_killmails;
    RAISE NOTICE '  Still NULL: %', null_count;

    IF null_count > 0 THEN
        RAISE WARNING 'Some killmails still have NULL ship_class. This may indicate missing ship_type_id or unknown ship types.';
    END IF;
END $$;

-- =============================================
-- SUCCESS
-- =============================================

SELECT 'Migration 007: Ship class column added and backfilled successfully!' AS status;
