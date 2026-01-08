-- Migration 008: Add ship_category and ship_role columns
-- Implements official EVE Online ship classification system

-- =============================================
-- 1. Add new columns
-- =============================================

ALTER TABLE killmails
ADD COLUMN IF NOT EXISTS ship_category VARCHAR(30),
ADD COLUMN IF NOT EXISTS ship_role VARCHAR(30);

COMMENT ON COLUMN killmails.ship_category IS 'Ship category: frigate, destroyer, cruiser, battlecruiser, battleship, dreadnought, carrier, force_auxiliary, supercarrier, titan, industrial, freighter, mining_barge, exhumer, industrial_command, capital_industrial, corvette, shuttle, capsule';
COMMENT ON COLUMN killmails.ship_role IS 'Ship role: standard, assault, interceptor, covert_ops, stealth_bomber, electronic_attack, logistics, expedition, interdictor, command, tactical, heavy_assault, recon, heavy_interdictor, strategic, attack, marauder, black_ops, elite, blockade_runner, deep_space_transport, jump, lancer, prototype, citizen, flag';

-- =============================================
-- 2. Create indexes
-- =============================================

CREATE INDEX IF NOT EXISTS idx_ship_category ON killmails(ship_category, killmail_time DESC);
CREATE INDEX IF NOT EXISTS idx_ship_role ON killmails(ship_role, killmail_time DESC);
CREATE INDEX IF NOT EXISTS idx_system_ship_category ON killmails(solar_system_id, ship_category, killmail_time DESC);
CREATE INDEX IF NOT EXISTS idx_region_ship_category ON killmails(region_id, ship_category, killmail_time DESC);

-- =============================================
-- 3. Backfill ship_category and ship_role
-- =============================================

UPDATE killmails k
SET
    ship_category = CASE
        -- Corvettes & Shuttles
        WHEN t."groupID" = 237 THEN 'corvette'
        WHEN t."groupID" = 2001 THEN 'corvette'
        WHEN t."groupID" = 31 THEN 'shuttle'
        WHEN t."groupID" = 29 THEN 'capsule'

        -- Frigates
        WHEN t."groupID" IN (25, 324, 831, 830, 834, 893, 1527, 1283, 1022) THEN 'frigate'

        -- Destroyers
        WHEN t."groupID" IN (420, 541, 1534, 1305) THEN 'destroyer'

        -- Cruisers
        WHEN t."groupID" IN (26, 358, 906, 833, 832, 894, 963, 1972) THEN 'cruiser'

        -- Battlecruisers
        WHEN t."groupID" IN (419, 1201, 540) THEN 'battlecruiser'

        -- Battleships
        WHEN t."groupID" IN (27, 900, 898, 381) THEN 'battleship'

        -- Dreadnoughts
        WHEN t."groupID" IN (485, 4594) THEN 'dreadnought'

        -- Carriers
        WHEN t."groupID" = 547 THEN 'carrier'

        -- Force Auxiliaries
        WHEN t."groupID" = 1538 THEN 'force_auxiliary'

        -- Supercarriers
        WHEN t."groupID" = 659 THEN 'supercarrier'

        -- Titans
        WHEN t."groupID" = 30 THEN 'titan'

        -- Mining
        WHEN t."groupID" = 463 THEN 'mining_barge'
        WHEN t."groupID" = 543 THEN 'exhumer'

        -- Industrials
        WHEN t."groupID" IN (28, 1202, 380) THEN 'industrial'

        -- Freighters
        WHEN t."groupID" IN (513, 902) THEN 'freighter'

        -- Industrial Command
        WHEN t."groupID" = 941 THEN 'industrial_command'

        -- Capital Industrial
        WHEN t."groupID" = 883 THEN 'capital_industrial'

        ELSE 'other'
    END,
    ship_role = CASE
        -- Corvettes
        WHEN t."groupID" = 237 THEN 'standard'
        WHEN t."groupID" = 2001 THEN 'citizen'

        -- Shuttles & Capsules
        WHEN t."groupID" = 31 THEN 'standard'
        WHEN t."groupID" = 29 THEN 'standard'

        -- Frigates
        WHEN t."groupID" = 25 THEN 'standard'
        WHEN t."groupID" = 324 THEN 'assault'
        WHEN t."groupID" = 831 THEN 'interceptor'
        WHEN t."groupID" = 830 THEN 'covert_ops'
        WHEN t."groupID" = 834 THEN 'stealth_bomber'
        WHEN t."groupID" = 893 THEN 'electronic_attack'
        WHEN t."groupID" = 1527 THEN 'logistics'
        WHEN t."groupID" = 1283 THEN 'expedition'
        WHEN t."groupID" = 1022 THEN 'prototype'

        -- Destroyers
        WHEN t."groupID" = 420 THEN 'standard'
        WHEN t."groupID" = 541 THEN 'interdictor'
        WHEN t."groupID" = 1534 THEN 'command'
        WHEN t."groupID" = 1305 THEN 'tactical'

        -- Cruisers
        WHEN t."groupID" = 26 THEN 'standard'
        WHEN t."groupID" = 358 THEN 'heavy_assault'
        WHEN t."groupID" IN (906, 833) THEN 'recon'
        WHEN t."groupID" = 832 THEN 'logistics'
        WHEN t."groupID" = 894 THEN 'heavy_interdictor'
        WHEN t."groupID" = 963 THEN 'strategic'
        WHEN t."groupID" = 1972 THEN 'flag'

        -- Battlecruisers
        WHEN t."groupID" = 419 THEN 'standard'
        WHEN t."groupID" = 1201 THEN 'attack'
        WHEN t."groupID" = 540 THEN 'command'

        -- Battleships
        WHEN t."groupID" = 27 THEN 'standard'
        WHEN t."groupID" = 900 THEN 'marauder'
        WHEN t."groupID" = 898 THEN 'black_ops'
        WHEN t."groupID" = 381 THEN 'elite'

        -- Capitals
        WHEN t."groupID" = 485 THEN 'standard'
        WHEN t."groupID" = 4594 THEN 'lancer'
        WHEN t."groupID" = 547 THEN 'standard'
        WHEN t."groupID" = 1538 THEN 'standard'
        WHEN t."groupID" = 659 THEN 'standard'
        WHEN t."groupID" = 30 THEN 'standard'

        -- Mining
        WHEN t."groupID" = 463 THEN 'standard'
        WHEN t."groupID" = 543 THEN 'standard'

        -- Industrials
        WHEN t."groupID" = 28 THEN 'standard'
        WHEN t."groupID" = 1202 THEN 'blockade_runner'
        WHEN t."groupID" = 380 THEN 'deep_space_transport'

        -- Freighters
        WHEN t."groupID" = 513 THEN 'standard'
        WHEN t."groupID" = 902 THEN 'jump'

        -- Industrial Command & Capital Industrial
        WHEN t."groupID" = 941 THEN 'standard'
        WHEN t."groupID" = 883 THEN 'standard'

        ELSE 'other'
    END
FROM "invTypes" t
WHERE k.ship_type_id = t."typeID"
  AND (k.ship_category IS NULL OR k.ship_role IS NULL);

-- =============================================
-- 4. Verify migration
-- =============================================

DO $$
DECLARE
    total_killmails INTEGER;
    categorized_killmails INTEGER;
    null_category_count INTEGER;
    null_role_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_killmails FROM killmails;
    SELECT COUNT(*) INTO categorized_killmails FROM killmails WHERE ship_category IS NOT NULL AND ship_role IS NOT NULL;
    SELECT COUNT(*) INTO null_category_count FROM killmails WHERE ship_category IS NULL;
    SELECT COUNT(*) INTO null_role_count FROM killmails WHERE ship_role IS NULL;

    RAISE NOTICE 'Migration 008 Statistics:';
    RAISE NOTICE '  Total killmails: %', total_killmails;
    RAISE NOTICE '  Categorized: %', categorized_killmails;
    RAISE NOTICE '  NULL category: %', null_category_count;
    RAISE NOTICE '  NULL role: %', null_role_count;

    IF null_category_count > 0 OR null_role_count > 0 THEN
        RAISE WARNING 'Some killmails still have NULL ship_category or ship_role. This may indicate missing ship_type_id or unknown ship types.';
    END IF;
END $$;

-- Show distribution by category
DO $$
DECLARE
    rec RECORD;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE 'Ship Category Distribution:';
    RAISE NOTICE '========================================';
    FOR rec IN
        SELECT ship_category, COUNT(*) as count
        FROM killmails
        WHERE ship_category IS NOT NULL
        GROUP BY ship_category
        ORDER BY count DESC
        LIMIT 15
    LOOP
        RAISE NOTICE '  %: %', RPAD(rec.ship_category, 25), rec.count;
    END LOOP;
END $$;

-- =============================================
-- SUCCESS
-- =============================================

SELECT 'Migration 008: Ship category and role columns added successfully!' AS status;
