"""
Ship Classification Utilities.

Provides ship classification based on EVE SDE groupID.
"""

from typing import Tuple, Optional

from src.database import get_db_connection


def safe_int_value(value) -> int:
    """
    Safely convert a value to int, handling overflow and invalid values.

    Args:
        value: Value to convert (float, str, int, etc.)

    Returns:
        Int value capped at BIGINT max, or 0 if invalid
    """
    try:
        int_value = int(float(value))
        # Cap at PostgreSQL BIGINT max to prevent overflow
        BIGINT_MAX = 9223372036854775807
        if int_value > BIGINT_MAX:
            return BIGINT_MAX
        if int_value < -BIGINT_MAX:
            return -BIGINT_MAX
        return int_value
    except (ValueError, OverflowError, TypeError) as e:
        print(f"Warning: Invalid numeric value '{value}': {e}, using 0")
        return 0


def classify_ship(ship_type_id: int) -> Tuple[Optional[str], Optional[str]]:
    """
    Classify ship by type ID using EVE SDE groupID.

    Returns official EVE ship classification with category and role.

    Args:
        ship_type_id: EVE ship type ID

    Returns:
        Tuple of (ship_category, ship_role) or (None, None) if not found

    Categories:
        frigate, destroyer, cruiser, battlecruiser, battleship,
        dreadnought, carrier, force_auxiliary, supercarrier, titan,
        industrial, freighter, mining_barge, exhumer,
        industrial_command, capital_industrial, corvette, shuttle, capsule, fighter

    Roles:
        standard, assault, interceptor, covert_ops, stealth_bomber, electronic_attack,
        logistics, expedition, interdictor, command, tactical, heavy_assault, recon,
        heavy_interdictor, strategic, attack, marauder, black_ops, elite,
        blockade_runner, deep_space_transport, jump, lancer, prototype, citizen, flag,
        light, heavy, support, structure_light, structure_support, structure_heavy
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT "groupID" FROM "invTypes" WHERE "typeID" = %s',
                    (ship_type_id,)
                )
                result = cur.fetchone()
                if not result:
                    return (None, None)

                group_id = result[0]

                # Official EVE ship classification mapping
                # Based on invGroups table from EVE SDE

                # Corvettes & Shuttles
                if group_id == 237: return ('corvette', 'standard')
                if group_id == 2001: return ('corvette', 'citizen')
                if group_id == 31: return ('shuttle', 'standard')
                if group_id == 29: return ('capsule', 'standard')

                # Frigates
                if group_id == 25: return ('frigate', 'standard')
                if group_id == 324: return ('frigate', 'assault')
                if group_id == 831: return ('frigate', 'interceptor')
                if group_id == 830: return ('frigate', 'covert_ops')
                if group_id == 834: return ('frigate', 'stealth_bomber')
                if group_id == 893: return ('frigate', 'electronic_attack')
                if group_id == 1527: return ('frigate', 'logistics')
                if group_id == 1283: return ('frigate', 'expedition')
                if group_id == 1022: return ('frigate', 'prototype')

                # Destroyers
                if group_id == 420: return ('destroyer', 'standard')
                if group_id == 541: return ('destroyer', 'interdictor')
                if group_id == 1534: return ('destroyer', 'command')
                if group_id == 1305: return ('destroyer', 'tactical')

                # Cruisers
                if group_id == 26: return ('cruiser', 'standard')
                if group_id == 358: return ('cruiser', 'heavy_assault')
                if group_id in (906, 833): return ('cruiser', 'recon')
                if group_id == 832: return ('cruiser', 'logistics')
                if group_id == 894: return ('cruiser', 'heavy_interdictor')
                if group_id == 963: return ('cruiser', 'strategic')
                if group_id == 1972: return ('cruiser', 'flag')

                # Battlecruisers
                if group_id == 419: return ('battlecruiser', 'standard')
                if group_id == 1201: return ('battlecruiser', 'attack')
                if group_id == 540: return ('battlecruiser', 'command')

                # Battleships
                if group_id == 27: return ('battleship', 'standard')
                if group_id == 900: return ('battleship', 'marauder')
                if group_id == 898: return ('battleship', 'black_ops')
                if group_id == 381: return ('battleship', 'elite')

                # Capitals
                if group_id == 485: return ('dreadnought', 'standard')
                if group_id == 4594: return ('dreadnought', 'lancer')
                if group_id == 547: return ('carrier', 'standard')
                if group_id == 1538: return ('force_auxiliary', 'standard')
                if group_id == 659: return ('supercarrier', 'standard')
                if group_id == 30: return ('titan', 'standard')

                # Mining
                if group_id == 463: return ('mining_barge', 'standard')
                if group_id == 543: return ('exhumer', 'standard')

                # Industrials
                if group_id == 28: return ('industrial', 'standard')
                if group_id == 1202: return ('industrial', 'blockade_runner')
                if group_id == 380: return ('industrial', 'deep_space_transport')

                # Freighters
                if group_id == 513: return ('freighter', 'standard')
                if group_id == 902: return ('freighter', 'jump')

                # Industrial Command & Capital Industrial
                if group_id == 941: return ('industrial_command', 'standard')
                if group_id == 883: return ('capital_industrial', 'standard')

                # Fighters (Carrier drones)
                if group_id == 1652: return ('fighter', 'light')
                if group_id == 1653: return ('fighter', 'heavy')
                if group_id == 1537: return ('fighter', 'support')
                if group_id == 4777: return ('fighter', 'structure_light')
                if group_id == 4778: return ('fighter', 'structure_support')
                if group_id == 4779: return ('fighter', 'structure_heavy')

                # Deployables (Mobile structures)
                if group_id == 361: return ('deployable', 'warp_disruptor')
                if group_id == 1246: return ('deployable', 'depot')
                if group_id == 1250: return ('deployable', 'tractor_unit')
                if group_id == 1276: return ('deployable', 'micro_jump')
                if group_id == 4093: return ('deployable', 'cyno_beacon')
                if group_id == 4107: return ('deployable', 'observatory')
                if group_id == 4137: return ('deployable', 'analysis_beacon')
                if group_id == 4810: return ('deployable', 'mercenary_den')

                # Starbase (POS structures)
                if group_id == 365: return ('starbase', 'control_tower')
                if group_id == 363: return ('starbase', 'ship_maintenance')
                if group_id == 471: return ('starbase', 'hangar_array')
                if group_id in (430, 449): return ('starbase', 'sentry')
                if group_id == 441: return ('starbase', 'web_battery')
                if group_id == 443: return ('starbase', 'scram_battery')

                # Orbitals (Customs Offices, Skyhooks)
                if group_id == 1025: return ('orbital', 'customs_office')
                if group_id == 4736: return ('orbital', 'skyhook')

                # Upwell Structures (Citadels, Refineries, etc.)
                if group_id == 1657: return ('citadel', 'standard')
                if group_id == 1406: return ('refinery', 'standard')
                if group_id == 1408: return ('structure', 'jump_bridge')
                if group_id == 4744: return ('structure', 'moon_drill')
                if group_id == 1924: return ('structure', 'stronghold')

                # Unknown/Other
                return ('other', 'other')

    except Exception as e:
        print(f"Warning: Failed to classify ship {ship_type_id}: {e}")
        return (None, None)


def is_capital_ship(ship_type_id: int) -> bool:
    """
    Check if a ship is a capital ship.

    Capital ship groups: Titan, Supercarrier, Carrier, Dreadnought, Force Auxiliary, Rorqual
    """
    capital_groups = [30, 659, 547, 485, 1538, 941]  # Group IDs for capital ships
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT "groupID" FROM "invTypes" WHERE "typeID" = %s',
                    (ship_type_id,)
                )
                result = cur.fetchone()
                if result:
                    group_id = result[0]
                    return group_id in capital_groups
    except Exception:
        pass
    return False
