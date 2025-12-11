"""
Portfolio Service for Multi-Character Aggregation

Provides aggregated views across multiple EVE Online characters:
- Total ISK balance
- Combined assets
- Active jobs summary
- Skill queues
"""

from typing import List, Dict, Any
from character import character_api
from database import get_db_connection


class PortfolioService:
    """Aggregates data across multiple characters"""

    def get_character_summaries(self, character_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Get summary data for all characters

        Args:
            character_ids: List of character IDs to summarize

        Returns:
            List of character summaries with wallet, location, jobs, skills
        """
        summaries = []

        for char_id in character_ids:
            try:
                summary = self._get_character_summary(char_id)
                summaries.append(summary)
            except Exception as e:
                print(f"Error getting summary for character {char_id}: {e}")
                summaries.append({
                    'character_id': char_id,
                    'error': str(e)
                })

        return summaries

    def _get_character_summary(self, character_id: int) -> Dict[str, Any]:
        """Get summary for single character"""
        # Get character name
        char_name = self._get_character_name(character_id)

        # Get wallet balance
        wallet_data = character_api.get_wallet_balance(character_id)
        wallet = wallet_data.get('balance', 0) if isinstance(wallet_data, dict) else 0

        # Get location from ESI
        location_data = character_api.get_character_location(character_id)
        system_id = location_data.get('solar_system_id') if isinstance(location_data, dict) else None
        system_name = self._get_system_name(system_id) if system_id else "Unknown"

        # Get active jobs
        jobs_data = character_api.get_industry_jobs(character_id)
        jobs = jobs_data.get('jobs', []) if isinstance(jobs_data, dict) else []
        active_jobs = []
        for job in jobs[:3]:  # Max 3 jobs shown
            if job.get('status') == 'active':
                active_jobs.append({
                    'blueprint_id': job.get('blueprint_id'),
                    'runs': job.get('runs'),
                    'end_date': job.get('end_date')
                })

        # Get skill queue
        skill_queue_data = character_api.get_skill_queue(character_id)
        skill_queue = skill_queue_data.get('queue', []) if isinstance(skill_queue_data, dict) else []
        next_skill = None
        if skill_queue and len(skill_queue) > 0:
            skill = skill_queue[0]
            next_skill = {
                'skill_id': skill.get('skill_id'),
                'finish_date': skill.get('finish_date')
            }

        return {
            'character_id': character_id,
            'name': char_name,
            'isk_balance': wallet,
            'location': {
                'system_id': system_id,
                'system_name': system_name
            },
            'active_jobs': active_jobs,
            'skill_queue': next_skill
        }

    def get_total_portfolio_value(self, character_ids: List[int]) -> float:
        """Calculate total ISK balance across all characters"""
        total = 0.0

        for char_id in character_ids:
            try:
                wallet_data = character_api.get_wallet_balance(char_id)
                wallet = wallet_data.get('balance', 0) if isinstance(wallet_data, dict) else 0
                total += wallet
            except Exception as e:
                print(f"Error getting wallet for character {char_id}: {e}")

        return total

    def _get_character_name(self, character_id: int) -> str:
        """Get character name from database"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT character_name FROM characters WHERE character_id = %s",
                        (character_id,)
                    )
                    row = cursor.fetchone()
                    return row[0] if row else f"Character_{character_id}"
        except Exception as e:
            print(f"Error fetching character name for {character_id}: {e}")
            return f"Character_{character_id}"

    def _get_system_name(self, system_id: int) -> str:
        """Get system name from SDE"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT solarSystemName FROM mapSolarSystems WHERE solarSystemID = %s",
                        (system_id,)
                    )
                    row = cursor.fetchone()
                    return row[0] if row else "Unknown"
        except Exception as e:
            print(f"Error fetching system name for {system_id}: {e}")
            return "Unknown"
