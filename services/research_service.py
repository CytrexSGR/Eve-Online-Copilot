"""
Research Service for Skill Planning

Provides skill analysis for EVE Online characters:
- Required skills for production
- Training time calculations
- Skill recommendations based on production goals
"""

from typing import List, Dict, Any, Optional
from database import get_db_connection
import character


class ResearchService:
    """Analyzes skills required for manufacturing and provides recommendations"""

    def get_skills_for_item(
        self,
        type_id: int,
        character_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get skills required to manufacture an item

        Args:
            type_id: Item type ID to check
            character_id: Optional character to compare skills

        Returns:
            Dict with required_skills list and optionally character comparison
        """
        # Get blueprint for this item
        blueprint_id = self._get_blueprint_for_item(type_id)
        if not blueprint_id:
            return {'required_skills': [], 'error': 'No blueprint found'}

        # Get required skills from blueprint
        required_skills = self._get_blueprint_skills(blueprint_id)

        # If character provided, compare with their skills
        if character_id:
            character_skills = self._get_character_skills(character_id)
            required_skills = self._compare_skills(required_skills, character_skills)

        return {
            'type_id': type_id,
            'blueprint_id': blueprint_id,
            'required_skills': required_skills
        }

    def _get_blueprint_for_item(self, type_id: int) -> Optional[int]:
        """Find blueprint that produces this item"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT "typeID"
                        FROM "industryActivityProducts"
                        WHERE "productTypeID" = %s
                        AND "activityID" = 1  -- Manufacturing
                        LIMIT 1
                    """, (type_id,))

                    row = cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            print(f"Error finding blueprint: {e}")
            return None

    def _get_blueprint_skills(self, blueprint_id: int) -> List[Dict[str, Any]]:
        """Get skills required for blueprint"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            ias."skillID",
                            t."typeName",
                            ias."level"
                        FROM "industryActivitySkills" ias
                        JOIN "invTypes" t ON ias."skillID" = t."typeID"
                        WHERE ias."typeID" = %s
                        AND ias."activityID" = 1  -- Manufacturing
                    """, (blueprint_id,))

                    rows = cursor.fetchall()

                    skills = []
                    for row in rows:
                        skills.append({
                            'skill_id': row[0],
                            'skill_name': row[1],
                            'required_level': row[2],
                            'character_level': 0,  # Will be updated if character provided
                            'training_time_seconds': 0
                        })

                    return skills
        except Exception as e:
            print(f"Error getting blueprint skills: {e}")
            return []

    def _get_character_skills(self, character_id: int) -> Dict[int, int]:
        """Get character's current skill levels from ESI"""
        try:
            skills = character.get_character_skills(character_id)

            # Create dict of skill_id -> level
            skill_levels = {}
            for skill in skills.get('skills', []):
                skill_levels[skill['skill_id']] = skill['trained_skill_level']

            return skill_levels
        except Exception as e:
            print(f"Error getting character skills: {e}")
            return {}

    def _compare_skills(
        self,
        required_skills: List[Dict[str, Any]],
        character_skills: Dict[int, int]
    ) -> List[Dict[str, Any]]:
        """Compare required skills with character's current skills"""
        for skill in required_skills:
            skill_id = skill['skill_id']
            required_level = skill['required_level']
            character_level = character_skills.get(skill_id, 0)

            skill['character_level'] = character_level

            # Calculate training time if skill not met
            if character_level < required_level:
                training_time = self._calculate_training_time(
                    skill_id,
                    character_level,
                    required_level
                )
                skill['training_time_seconds'] = training_time
            else:
                skill['training_time_seconds'] = 0

        return required_skills

    def _calculate_training_time(
        self,
        skill_id: int,
        current_level: int,
        target_level: int
    ) -> int:
        """
        Calculate training time from current to target level

        Simplified calculation - in reality would need character attributes
        """
        # Get skill rank/multiplier
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            COALESCE("skillTimeConstant", 1) as rank
                        FROM "invTypes"
                        WHERE "typeID" = %s
                    """, (skill_id,))

                    row = cursor.fetchone()
                    rank = row[0] if row else 1
        except Exception:
            rank = 1

        # Skill points per level (simplified)
        SP_PER_LEVEL = {
            1: 250,
            2: 1415,
            3: 8000,
            4: 45255,
            5: 256000
        }

        # Calculate total SP needed
        total_sp = 0
        for level in range(current_level + 1, target_level + 1):
            total_sp += SP_PER_LEVEL.get(level, 0) * rank

        # Assume 30 SP/minute (average)
        SP_PER_MINUTE = 30
        training_minutes = total_sp / SP_PER_MINUTE

        return int(training_minutes * 60)  # Convert to seconds

    def get_skill_recommendations(self, character_id: int) -> List[Dict[str, Any]]:
        """
        Get skill training recommendations based on production history

        Analyzes what character builds most and suggests skills
        """
        # TODO: Implement based on production history
        # For now, return empty list
        return []
