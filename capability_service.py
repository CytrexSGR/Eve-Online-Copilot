"""
Character Capability Service for EVE Co-Pilot
Manages ship capabilities and skill requirements
"""

from database import get_db_connection
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict
from datetime import datetime
import json


# Ship groups relevant for logistics
LOGISTICS_SHIP_GROUPS = {
    28: 'Industrial',
    380: 'Deep Space Transport',
    381: 'Blockade Runner',
    513: 'Freighter',
    902: 'Jump Freighter',
}

# Attribute IDs for skill requirements in dgmTypeAttributes
SKILL_ATTRIBUTE_IDS = {
    'requiredSkill1': 182,
    'requiredSkill1Level': 277,
    'requiredSkill2': 183,
    'requiredSkill2Level': 278,
    'requiredSkill3': 184,
    'requiredSkill3Level': 279,
}


class CapabilityService:

    def get_ship_skill_requirements(self, type_id: int) -> List[Dict]:
        """Get skill requirements for a ship from SDE"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT
                        t."typeID",
                        t."typeName",
                        -- Skill 1
                        s1."typeName" as skill1_name,
                        s1."typeID" as skill1_id,
                        a1l."valueFloat" as skill1_level,
                        -- Skill 2
                        s2."typeName" as skill2_name,
                        s2."typeID" as skill2_id,
                        a2l."valueFloat" as skill2_level,
                        -- Skill 3
                        s3."typeName" as skill3_name,
                        s3."typeID" as skill3_id,
                        a3l."valueFloat" as skill3_level
                    FROM "invTypes" t
                    -- Skill 1
                    LEFT JOIN "dgmTypeAttributes" a1 ON t."typeID" = a1."typeID" AND a1."attributeID" = 182
                    LEFT JOIN "invTypes" s1 ON a1."valueFloat" = s1."typeID"
                    LEFT JOIN "dgmTypeAttributes" a1l ON t."typeID" = a1l."typeID" AND a1l."attributeID" = 277
                    -- Skill 2
                    LEFT JOIN "dgmTypeAttributes" a2 ON t."typeID" = a2."typeID" AND a2."attributeID" = 183
                    LEFT JOIN "invTypes" s2 ON a2."valueFloat" = s2."typeID"
                    LEFT JOIN "dgmTypeAttributes" a2l ON t."typeID" = a2l."typeID" AND a2l."attributeID" = 278
                    -- Skill 3
                    LEFT JOIN "dgmTypeAttributes" a3 ON t."typeID" = a3."typeID" AND a3."attributeID" = 184
                    LEFT JOIN "invTypes" s3 ON a3."valueFloat" = s3."typeID"
                    LEFT JOIN "dgmTypeAttributes" a3l ON t."typeID" = a3l."typeID" AND a3l."attributeID" = 279
                    WHERE t."typeID" = %s
                ''', (type_id,))
                result = cur.fetchone()

                if not result:
                    return []

                requirements = []
                for i in [1, 2, 3]:
                    skill_name = result.get(f'skill{i}_name')
                    skill_id = result.get(f'skill{i}_id')
                    skill_level = result.get(f'skill{i}_level')
                    if skill_name and skill_level:
                        requirements.append({
                            'skill_id': int(skill_id),
                            'skill_name': skill_name,
                            'required_level': int(skill_level)
                        })

                return requirements

    def get_ship_cargo_capacity(self, type_id: int) -> Optional[float]:
        """Get cargo capacity for a ship from SDE"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Attribute 38 = capacity
                cur.execute('''
                    SELECT a."valueFloat" as capacity
                    FROM "dgmTypeAttributes" a
                    WHERE a."typeID" = %s AND a."attributeID" = 38
                ''', (type_id,))
                result = cur.fetchone()
                return float(result['capacity']) if result else None

    def get_ship_group(self, type_id: int) -> Optional[str]:
        """Get ship group name from SDE"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT g."groupID", g."groupName"
                    FROM "invTypes" t
                    JOIN "invGroups" g ON t."groupID" = g."groupID"
                    WHERE t."typeID" = %s
                ''', (type_id,))
                result = cur.fetchone()
                if result:
                    group_id = result['groupID']
                    return LOGISTICS_SHIP_GROUPS.get(group_id, result['groupName'])
                return None

    def check_skill_requirements(
        self,
        character_skills: List[Dict],
        requirements: List[Dict]
    ) -> tuple[bool, List[Dict]]:
        """
        Check if character meets skill requirements

        Returns: (can_fly, missing_skills)
        """
        # Build skill lookup: skill_id -> level
        skill_levels = {s['skill_id']: s['trained_skill_level'] for s in character_skills}

        missing = []
        can_fly = True

        for req in requirements:
            current_level = skill_levels.get(req['skill_id'], 0)
            if current_level < req['required_level']:
                can_fly = False
                missing.append({
                    'skill_name': req['skill_name'],
                    'skill_id': req['skill_id'],
                    'required_level': req['required_level'],
                    'current_level': current_level
                })

        return can_fly, missing

    def upsert_capability(
        self,
        character_id: int,
        character_name: str,
        type_id: int,
        ship_name: str,
        ship_group: str,
        cargo_capacity: float,
        location_id: int,
        location_name: str,
        can_fly: bool,
        missing_skills: List[Dict]
    ) -> dict:
        """Insert or update character capability"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    INSERT INTO character_capabilities
                        (character_id, character_name, type_id, ship_name, ship_group,
                         cargo_capacity, location_id, location_name, can_fly, missing_skills, last_synced)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (character_id, type_id, location_id)
                    DO UPDATE SET
                        character_name = EXCLUDED.character_name,
                        ship_name = EXCLUDED.ship_name,
                        ship_group = EXCLUDED.ship_group,
                        cargo_capacity = EXCLUDED.cargo_capacity,
                        location_name = EXCLUDED.location_name,
                        can_fly = EXCLUDED.can_fly,
                        missing_skills = EXCLUDED.missing_skills,
                        last_synced = NOW()
                    RETURNING *
                ''', (
                    character_id, character_name, type_id, ship_name, ship_group,
                    cargo_capacity, location_id, location_name, can_fly,
                    json.dumps(missing_skills) if missing_skills else None
                ))
                conn.commit()
                return dict(cur.fetchone())

    def get_character_ships(
        self,
        character_id: int,
        location_ids: Optional[List[int]] = None,
        can_fly_only: bool = True
    ) -> List[Dict]:
        """Get available ships for a character"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                where_clauses = ["character_id = %s"]
                params = [character_id]

                if can_fly_only:
                    where_clauses.append("can_fly = TRUE")

                if location_ids:
                    where_clauses.append("location_id = ANY(%s)")
                    params.append(location_ids)

                where_sql = " AND ".join(where_clauses)

                cur.execute(f'''
                    SELECT * FROM character_capabilities
                    WHERE {where_sql}
                    ORDER BY cargo_capacity DESC
                ''', params)

                return [dict(row) for row in cur.fetchall()]

    def get_all_available_ships(
        self,
        location_ids: Optional[List[int]] = None,
        can_fly_only: bool = True
    ) -> List[Dict]:
        """Get all available ships across all characters"""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                where_clauses = []
                params = []

                if can_fly_only:
                    where_clauses.append("can_fly = TRUE")

                if location_ids:
                    where_clauses.append("location_id = ANY(%s)")
                    params.append(location_ids)

                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                cur.execute(f'''
                    SELECT * FROM character_capabilities
                    WHERE {where_sql}
                    ORDER BY cargo_capacity DESC
                ''', params)

                return [dict(row) for row in cur.fetchall()]

    def clear_character_capabilities(self, character_id: int) -> int:
        """Clear all capabilities for a character (before re-sync)"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'DELETE FROM character_capabilities WHERE character_id = %s',
                    (character_id,)
                )
                conn.commit()
                return cur.rowcount


capability_service = CapabilityService()
