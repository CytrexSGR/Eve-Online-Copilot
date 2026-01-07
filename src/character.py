"""
EVE Co-Pilot Character Data Module
Fetches character-specific data using authenticated ESI requests
"""

import requests
from typing import Optional
from src.auth import eve_auth
from config import ESI_BASE_URL, ESI_USER_AGENT


class CharacterAPI:
    """API client for character-specific ESI endpoints"""

    def __init__(self):
        self.base_url = ESI_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": ESI_USER_AGENT,
            "Accept": "application/json"
        })

    def _authenticated_get(self, character_id: int, endpoint: str, params: dict = None) -> dict | list | None:
        """Make authenticated GET request to ESI"""
        access_token = eve_auth.get_valid_token(character_id)

        if not access_token:
            return {"error": f"No valid token for character {character_id}"}

        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            response = self.session.get(
                url,
                params=params or {"datasource": "tranquility"},
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                return {"error": "Insufficient permissions", "status": 403}
            else:
                return {
                    "error": f"ESI request failed",
                    "status": response.status_code,
                    "details": response.text
                }

        except Exception as e:
            return {"error": f"Request error: {str(e)}"}

    def get_wallet_balance(self, character_id: int) -> dict:
        """Get character's wallet balance"""
        result = self._authenticated_get(
            character_id,
            f"/characters/{character_id}/wallet/"
        )

        if isinstance(result, (int, float)):
            return {
                "character_id": character_id,
                "balance": result,
                "formatted": f"{result:,.2f} ISK"
            }

        return result

    def get_assets(self, character_id: int, location_id: Optional[int] = None) -> dict:
        """Get character's assets"""
        all_assets = []
        page = 1

        while True:
            result = self._authenticated_get(
                character_id,
                f"/characters/{character_id}/assets/",
                {"datasource": "tranquility", "page": page}
            )

            if isinstance(result, dict) and "error" in result:
                return result

            if not result:
                break

            all_assets.extend(result)

            if len(result) < 1000:
                break
            page += 1

        # Filter by location if specified
        if location_id:
            all_assets = [a for a in all_assets if a.get("location_id") == location_id]

        return {
            "character_id": character_id,
            "total_items": len(all_assets),
            "assets": all_assets
        }

    def get_asset_names(self, character_id: int, item_ids: list) -> dict:
        """Get names for specific assets (containers, ships, etc.)"""
        access_token = eve_auth.get_valid_token(character_id)

        if not access_token:
            return {"error": f"No valid token for character {character_id}"}

        url = f"{self.base_url}/characters/{character_id}/assets/names/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        try:
            response = self.session.post(
                url,
                json=item_ids[:1000],  # Max 1000 per request
                headers=headers,
                params={"datasource": "tranquility"},
                timeout=30
            )

            if response.status_code == 200:
                return {"names": response.json()}

            return {"error": f"Failed to get asset names: {response.status_code}"}

        except Exception as e:
            return {"error": f"Request error: {str(e)}"}

    def get_skills(self, character_id: int) -> dict:
        """Get character's skills with names from SDE"""
        result = self._authenticated_get(
            character_id,
            f"/characters/{character_id}/skills/"
        )

        if isinstance(result, dict) and "error" not in result:
            skills = result.get("skills", [])

            # Enrich skills with names from database
            from database import get_item_info
            enriched_skills = []
            for skill in skills:
                skill_info = get_item_info(skill.get("skill_id"))
                skill_data = {
                    "skill_id": skill.get("skill_id"),
                    "skill_name": skill_info.get("typeName", "Unknown") if skill_info else "Unknown",
                    "level": skill.get("active_skill_level", 0),
                    "trained_level": skill.get("trained_skill_level", 0),
                    "skillpoints": skill.get("skillpoints_in_skill", 0)
                }
                enriched_skills.append(skill_data)

            # Sort by skill name
            enriched_skills.sort(key=lambda x: x["skill_name"])

            return {
                "character_id": character_id,
                "total_sp": result.get("total_sp", 0),
                "unallocated_sp": result.get("unallocated_sp", 0),
                "skill_count": len(enriched_skills),
                "skills": enriched_skills
            }

        return result

    def get_skill_queue(self, character_id: int) -> dict:
        """Get character's skill queue"""
        result = self._authenticated_get(
            character_id,
            f"/characters/{character_id}/skillqueue/"
        )

        if isinstance(result, list):
            return {
                "character_id": character_id,
                "queue_length": len(result),
                "queue": result
            }

        return result

    def get_market_orders(self, character_id: int) -> dict:
        """Get character's active market orders"""
        result = self._authenticated_get(
            character_id,
            f"/characters/{character_id}/orders/"
        )

        if isinstance(result, list):
            buy_orders = [o for o in result if o.get("is_buy_order", False)]
            sell_orders = [o for o in result if not o.get("is_buy_order", True)]

            return {
                "character_id": character_id,
                "total_orders": len(result),
                "buy_orders": len(buy_orders),
                "sell_orders": len(sell_orders),
                "orders": result
            }

        return result

    def get_industry_jobs(self, character_id: int, include_completed: bool = False) -> dict:
        """Get character's industry jobs"""
        result = self._authenticated_get(
            character_id,
            f"/characters/{character_id}/industry/jobs/",
            {"datasource": "tranquility", "include_completed": include_completed}
        )

        if isinstance(result, list):
            active_jobs = [j for j in result if j.get("status") == "active"]
            return {
                "character_id": character_id,
                "total_jobs": len(result),
                "active_jobs": len(active_jobs),
                "jobs": result
            }

        return result

    def get_blueprints(self, character_id: int) -> dict:
        """Get character's blueprints"""
        all_blueprints = []
        page = 1

        while True:
            result = self._authenticated_get(
                character_id,
                f"/characters/{character_id}/blueprints/",
                {"datasource": "tranquility", "page": page}
            )

            if isinstance(result, dict) and "error" in result:
                return result

            if not result:
                break

            all_blueprints.extend(result)

            if len(result) < 1000:
                break
            page += 1

        # Categorize blueprints
        originals = [b for b in all_blueprints if b.get("quantity") == -1]
        copies = [b for b in all_blueprints if b.get("quantity") == -2]

        return {
            "character_id": character_id,
            "total_blueprints": len(all_blueprints),
            "originals": len(originals),
            "copies": len(copies),
            "blueprints": all_blueprints
        }

    def get_character_info(self, character_id: int) -> dict:
        """Get public character information (no auth required)"""
        try:
            response = self.session.get(
                f"{self.base_url}/characters/{character_id}/",
                params={"datasource": "tranquility"},
                timeout=30
            )

            if response.status_code == 200:
                return response.json()

            return {"error": f"Failed to get character info: {response.status_code}"}

        except Exception as e:
            return {"error": f"Request error: {str(e)}"}

    def get_character_location(self, character_id: int) -> dict:
        """Get character's current location (requires auth)"""
        try:
            response = self.session.get(
                f"{self.base_url}/characters/{character_id}/location/",
                headers=self._get_headers(character_id),
                params={"datasource": "tranquility"},
                timeout=30
            )

            if response.status_code == 200:
                return response.json()

            return {"error": f"Failed to get character location: {response.status_code}"}

        except Exception as e:
            return {"error": f"Request error: {str(e)}"}

    def get_corporation_id(self, character_id: int) -> int | None:
        """Get corporation ID for a character"""
        info = self.get_character_info(character_id)
        if isinstance(info, dict) and "corporation_id" in info:
            return info["corporation_id"]
        return None

    def get_corporation_info(self, corporation_id: int) -> dict:
        """Get public corporation information (no auth required)"""
        try:
            response = self.session.get(
                f"{self.base_url}/corporations/{corporation_id}/",
                params={"datasource": "tranquility"},
                timeout=30
            )

            if response.status_code == 200:
                return response.json()

            return {"error": f"Failed to get corporation info: {response.status_code}"}

        except Exception as e:
            return {"error": f"Request error: {str(e)}"}

    def get_corporation_wallets(self, character_id: int) -> dict:
        """
        Get corporation wallet balances (requires Director or Accountant role)
        Uses character's token to access their corporation's wallets
        """
        # First get corporation ID
        corp_id = self.get_corporation_id(character_id)
        if not corp_id:
            return {"error": "Could not determine corporation ID"}

        # Get corporation info
        corp_info = self.get_corporation_info(corp_id)
        corp_name = corp_info.get("name", "Unknown") if isinstance(corp_info, dict) else "Unknown"

        # Get wallet divisions
        result = self._authenticated_get(
            character_id,
            f"/corporations/{corp_id}/wallets/"
        )

        if isinstance(result, list):
            total_balance = sum(w.get("balance", 0) for w in result)
            return {
                "corporation_id": corp_id,
                "corporation_name": corp_name,
                "divisions": result,
                "total_balance": total_balance,
                "formatted_total": f"{total_balance:,.2f} ISK"
            }

        return result

    def get_corporation_wallet_journal(self, character_id: int, division: int = 1) -> dict:
        """Get corporation wallet journal for a division"""
        corp_id = self.get_corporation_id(character_id)
        if not corp_id:
            return {"error": "Could not determine corporation ID"}

        result = self._authenticated_get(
            character_id,
            f"/corporations/{corp_id}/wallets/{division}/journal/"
        )

        if isinstance(result, list):
            return {
                "corporation_id": corp_id,
                "division": division,
                "entries": len(result),
                "journal": result
            }

        return result


# Global character API instance
character_api = CharacterAPI()
