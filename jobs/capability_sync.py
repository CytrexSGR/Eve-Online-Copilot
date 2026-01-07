#!/usr/bin/env python3
"""
Character Capability Sync Job
Syncs ship capabilities for all authenticated characters

Run daily via cron to cache ship/skill data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime

# Import modules from parent directory
from src.auth import eve_auth
from src.character import CharacterAPI
from src.capability_service import capability_service, LOGISTICS_SHIP_GROUPS

# Initialize character API
character_api = CharacterAPI()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


def get_ship_type_ids() -> set:
    """Get all ship type IDs from logistics groups"""
    from database import get_db_connection
    from psycopg2.extras import RealDictCursor

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            group_ids = list(LOGISTICS_SHIP_GROUPS.keys())
            cur.execute('''
                SELECT "typeID" FROM "invTypes"
                WHERE "groupID" = ANY(%s) AND published = 1
            ''', (group_ids,))
            return {row['typeID'] for row in cur.fetchall()}


def sync_character(character_id: int, character_name: str, ship_type_ids: set) -> int:
    """Sync capabilities for a single character"""
    synced = 0

    try:
        # Get character assets
        assets_result = character_api.get_assets(character_id)
        if isinstance(assets_result, dict) and 'error' in assets_result:
            log.warning(f"Failed to get assets for {character_name}: {assets_result['error']}")
            return 0

        assets = assets_result.get('assets', [])

        # Filter to ships only
        ships = [a for a in assets if a.get('type_id') in ship_type_ids]
        log.info(f"Found {len(ships)} logistics ships for {character_name}")

        if not ships:
            return 0

        # Get character skills
        skills_result = character_api.get_skills(character_id)
        if isinstance(skills_result, dict) and 'error' in skills_result:
            log.warning(f"Failed to get skills for {character_name}: {skills_result['error']}")
            return 0

        skills = skills_result.get('skills', [])

        # Map the enriched skill data back to the format expected by capability_service
        # CharacterAPI returns 'trained_level' but capability_service expects 'trained_skill_level'
        mapped_skills = []
        for skill in skills:
            mapped_skills.append({
                'skill_id': skill['skill_id'],
                'trained_skill_level': skill.get('trained_level', skill.get('trained_skill_level', 0))
            })

        # Process each ship
        for ship in ships:
            type_id = ship['type_id']
            location_id = ship.get('location_id', 0)

            # Get ship info from SDE
            from database import get_db_connection
            from psycopg2.extras import RealDictCursor

            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute('SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s', (type_id,))
                    type_info = cur.fetchone()
                    ship_name = type_info['typeName'] if type_info else f"Unknown ({type_id})"

            # Get skill requirements
            requirements = capability_service.get_ship_skill_requirements(type_id)
            can_fly, missing = capability_service.check_skill_requirements(mapped_skills, requirements)

            # Get cargo capacity
            cargo_capacity = capability_service.get_ship_cargo_capacity(type_id)

            # Get ship group
            ship_group = capability_service.get_ship_group(type_id)

            # Resolve location name (simplified - would use ESI for citadels)
            location_name = resolve_location_name(location_id)

            # Upsert capability
            capability_service.upsert_capability(
                character_id=character_id,
                character_name=character_name,
                type_id=type_id,
                ship_name=ship_name,
                ship_group=ship_group,
                cargo_capacity=cargo_capacity or 0,
                location_id=location_id,
                location_name=location_name,
                can_fly=can_fly,
                missing_skills=missing
            )
            synced += 1

    except Exception as e:
        log.error(f"Error syncing {character_name}: {e}")

    return synced


def resolve_location_name(location_id: int) -> str:
    """Resolve location ID to name"""
    from database import get_db_connection
    from psycopg2.extras import RealDictCursor

    # Try station first
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT "stationName" FROM "staStations"
                WHERE "stationID" = %s
            ''', (location_id,))
            result = cur.fetchone()
            if result:
                return result['stationName']

    # Try solar system
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT "solarSystemName" FROM "mapSolarSystems"
                WHERE "solarSystemID" = %s
            ''', (location_id,))
            result = cur.fetchone()
            if result:
                return result['solarSystemName']

    return f"Location {location_id}"


def main():
    log.info("Starting capability sync job")
    start_time = datetime.now()

    # Get all authenticated characters
    characters = eve_auth.get_authenticated_characters()
    log.info(f"Found {len(characters)} authenticated characters")

    # Get ship type IDs
    ship_type_ids = get_ship_type_ids()
    log.info(f"Tracking {len(ship_type_ids)} ship types")

    total_synced = 0
    for char in characters:
        char_id = char['character_id']
        char_name = char['character_name']
        log.info(f"Syncing {char_name} ({char_id})...")

        synced = sync_character(char_id, char_name, ship_type_ids)
        total_synced += synced
        log.info(f"  Synced {synced} ships")

    elapsed = (datetime.now() - start_time).total_seconds()
    log.info(f"Capability sync complete: {total_synced} ships synced in {elapsed:.1f}s")


if __name__ == '__main__':
    main()
