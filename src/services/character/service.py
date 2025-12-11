"""Character service - business logic layer for ESI character data."""

from typing import List, Optional, Dict, Any, Protocol
from requests.exceptions import Timeout, RequestException
from psycopg2.extras import RealDictCursor

from src.services.character.models import (
    WalletBalance,
    AssetList,
    Asset,
    AssetName,
    SkillData,
    Skill,
    SkillQueue,
    SkillQueueItem,
    MarketOrderList,
    MarketOrder,
    IndustryJobList,
    IndustryJob,
    BlueprintList,
    Blueprint,
    CharacterInfo,
    CorporationInfo,
    CorporationWallet,
    CorporationWalletDivision,
)
from src.core.exceptions import NotFoundError, ExternalAPIError, AuthenticationError


class ESIClientProtocol(Protocol):
    """Protocol for ESI client dependency."""
    base_url: str
    session: Any


class AuthServiceProtocol(Protocol):
    """Protocol for auth service dependency."""
    def get_valid_token(self, character_id: int) -> str: ...


class DatabasePoolProtocol(Protocol):
    """Protocol for database pool dependency."""
    def get_connection(self): ...


class CharacterService:
    """Business logic for character-specific ESI endpoints."""

    def __init__(
        self,
        esi_client: ESIClientProtocol,
        auth_service: AuthServiceProtocol,
        db: DatabasePoolProtocol
    ):
        """Initialize service with dependencies.

        Args:
            esi_client: ESI client for API calls
            auth_service: Auth service for token management
            db: Database pool for SDE data queries
        """
        self.esi = esi_client
        self.auth = auth_service
        self.db = db

    def _authenticated_get(
        self,
        character_id: int,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Make authenticated GET request to ESI.

        Args:
            character_id: Character ID for authentication
            endpoint: ESI endpoint path
            params: Optional query parameters

        Returns:
            Response data (dict or list)

        Raises:
            AuthenticationError: If token retrieval fails
            NotFoundError: If resource not found (404)
            ExternalAPIError: If ESI request fails
        """
        # Get valid access token
        access_token = self.auth.get_valid_token(character_id)

        url = f"{self.esi.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {access_token}"}

        if params is None:
            params = {"datasource": "tranquility"}
        elif "datasource" not in params:
            params["datasource"] = "tranquility"

        try:
            response = self.esi.session.get(
                url,
                params=params,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                raise NotFoundError("Character", character_id)
            elif response.status_code == 403:
                raise ExternalAPIError(
                    service_name="ESI",
                    status_code=403,
                    message="Insufficient permissions"
                )
            else:
                raise ExternalAPIError(
                    service_name="ESI",
                    status_code=response.status_code,
                    message=f"ESI request failed: {response.text}"
                )

        except Timeout as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Request timeout: {str(e)}"
            )
        except RequestException as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Request failed: {str(e)}"
            )
        except (NotFoundError, ExternalAPIError, AuthenticationError):
            # Re-raise our own exceptions
            raise
        except Exception as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Unexpected error: {str(e)}"
            )

    def _public_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make public (non-authenticated) GET request to ESI.

        Args:
            endpoint: ESI endpoint path
            params: Optional query parameters

        Returns:
            Response data (dict or list)

        Raises:
            NotFoundError: If resource not found (404)
            ExternalAPIError: If ESI request fails
        """
        url = f"{self.esi.base_url}{endpoint}"

        if params is None:
            params = {"datasource": "tranquility"}
        elif "datasource" not in params:
            params["datasource"] = "tranquility"

        try:
            response = self.esi.session.get(
                url,
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                # Extract resource ID from endpoint for better error message
                resource_id = endpoint.split('/')[-2] if '/' in endpoint else "unknown"
                raise NotFoundError("Resource", resource_id)
            else:
                raise ExternalAPIError(
                    service_name="ESI",
                    status_code=response.status_code,
                    message=f"ESI request failed: {response.text}"
                )

        except Timeout as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Request timeout: {str(e)}"
            )
        except RequestException as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Request failed: {str(e)}"
            )
        except (NotFoundError, ExternalAPIError):
            raise
        except Exception as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Unexpected error: {str(e)}"
            )

    def get_wallet_balance(self, character_id: int) -> WalletBalance:
        """Get character's wallet balance.

        Args:
            character_id: Character ID

        Returns:
            WalletBalance: Wallet balance with formatted ISK

        Raises:
            AuthenticationError: If token retrieval fails
            NotFoundError: If character not found
            ExternalAPIError: If ESI request fails
        """
        balance = self._authenticated_get(
            character_id,
            f"/characters/{character_id}/wallet/"
        )

        return WalletBalance(
            character_id=character_id,
            balance=balance
        )

    def get_assets(
        self,
        character_id: int,
        location_id: Optional[int] = None
    ) -> AssetList:
        """Get character's assets with optional location filter.

        Args:
            character_id: Character ID
            location_id: Optional location ID to filter by

        Returns:
            AssetList: Character assets

        Raises:
            AuthenticationError: If token retrieval fails
            NotFoundError: If character not found
            ExternalAPIError: If ESI request fails
        """
        all_assets = []
        page = 1

        # Fetch all pages
        while True:
            result = self._authenticated_get(
                character_id,
                f"/characters/{character_id}/assets/",
                {"datasource": "tranquility", "page": page}
            )

            if not result:
                break

            all_assets.extend(result)

            # ESI returns max 1000 items per page
            if len(result) < 1000:
                break

            page += 1

        # Filter by location if specified
        if location_id:
            all_assets = [a for a in all_assets if a.get("location_id") == location_id]

        # Convert to Asset models
        assets = [Asset(**asset) for asset in all_assets]

        return AssetList(
            character_id=character_id,
            total_items=len(assets),
            assets=assets
        )

    def get_asset_names(
        self,
        character_id: int,
        item_ids: List[int]
    ) -> List[AssetName]:
        """Get custom names for specific assets.

        Args:
            character_id: Character ID
            item_ids: List of item IDs (max 1000)

        Returns:
            List[AssetName]: Asset names

        Raises:
            AuthenticationError: If token retrieval fails
            ExternalAPIError: If ESI request fails
        """
        # Get valid access token
        access_token = self.auth.get_valid_token(character_id)

        url = f"{self.esi.base_url}/characters/{character_id}/assets/names/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        try:
            response = self.esi.session.post(
                url,
                json=item_ids[:1000],  # Max 1000 per request
                headers=headers,
                params={"datasource": "tranquility"},
                timeout=30
            )

            if response.status_code == 200:
                names_data = response.json()
                return [AssetName(**name) for name in names_data]
            else:
                raise ExternalAPIError(
                    service_name="ESI",
                    status_code=response.status_code,
                    message=f"Failed to get asset names: {response.text}"
                )

        except Exception as e:
            if isinstance(e, ExternalAPIError):
                raise
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Request error: {str(e)}"
            )

    def get_skills(self, character_id: int) -> SkillData:
        """Get character's skills with names enriched from SDE.

        Args:
            character_id: Character ID

        Returns:
            SkillData: Character skills

        Raises:
            AuthenticationError: If token retrieval fails
            NotFoundError: If character not found
            ExternalAPIError: If ESI request fails
        """
        result = self._authenticated_get(
            character_id,
            f"/characters/{character_id}/skills/"
        )

        skills_data = result.get("skills", [])

        # Enrich skills with names from database
        enriched_skills = []
        for skill in skills_data:
            skill_name = "Unknown"

            # Query SDE for skill name
            try:
                with self.db.get_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute(
                            'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                            (skill.get("skill_id"),)
                        )
                        row = cur.fetchone()
                        if row:
                            skill_name = row["typeName"]
            except Exception:
                # If DB query fails, use "Unknown"
                pass

            enriched_skills.append(Skill(
                skill_id=skill.get("skill_id"),
                skill_name=skill_name,
                level=skill.get("active_skill_level", 0),
                trained_level=skill.get("trained_skill_level", 0),
                skillpoints=skill.get("skillpoints_in_skill", 0)
            ))

        # Sort by skill name
        enriched_skills.sort(key=lambda x: x.skill_name)

        return SkillData(
            character_id=character_id,
            total_sp=result.get("total_sp", 0),
            unallocated_sp=result.get("unallocated_sp", 0),
            skill_count=len(enriched_skills),
            skills=enriched_skills
        )

    def get_skill_queue(self, character_id: int) -> SkillQueue:
        """Get character's skill training queue.

        Args:
            character_id: Character ID

        Returns:
            SkillQueue: Skill queue

        Raises:
            AuthenticationError: If token retrieval fails
            NotFoundError: If character not found
            ExternalAPIError: If ESI request fails
        """
        result = self._authenticated_get(
            character_id,
            f"/characters/{character_id}/skillqueue/"
        )

        queue_items = [SkillQueueItem(**item) for item in result]

        return SkillQueue(
            character_id=character_id,
            queue_length=len(queue_items),
            queue=queue_items
        )

    def get_market_orders(self, character_id: int) -> MarketOrderList:
        """Get character's active market orders.

        Args:
            character_id: Character ID

        Returns:
            MarketOrderList: Market orders

        Raises:
            AuthenticationError: If token retrieval fails
            NotFoundError: If character not found
            ExternalAPIError: If ESI request fails
        """
        result = self._authenticated_get(
            character_id,
            f"/characters/{character_id}/orders/"
        )

        orders = [MarketOrder(**order) for order in result]
        buy_orders = [o for o in orders if o.is_buy_order]
        sell_orders = [o for o in orders if not o.is_buy_order]

        return MarketOrderList(
            character_id=character_id,
            total_orders=len(orders),
            buy_orders=len(buy_orders),
            sell_orders=len(sell_orders),
            orders=orders
        )

    def get_industry_jobs(
        self,
        character_id: int,
        include_completed: bool = False
    ) -> IndustryJobList:
        """Get character's industry jobs.

        Args:
            character_id: Character ID
            include_completed: Include completed jobs

        Returns:
            IndustryJobList: Industry jobs

        Raises:
            AuthenticationError: If token retrieval fails
            NotFoundError: If character not found
            ExternalAPIError: If ESI request fails
        """
        result = self._authenticated_get(
            character_id,
            f"/characters/{character_id}/industry/jobs/",
            {"datasource": "tranquility", "include_completed": include_completed}
        )

        jobs = [IndustryJob(**job) for job in result]
        active_jobs = [j for j in jobs if j.status == "active"]

        return IndustryJobList(
            character_id=character_id,
            total_jobs=len(jobs),
            active_jobs=len(active_jobs),
            jobs=jobs
        )

    def get_blueprints(self, character_id: int) -> BlueprintList:
        """Get character's blueprints.

        Args:
            character_id: Character ID

        Returns:
            BlueprintList: Blueprints

        Raises:
            AuthenticationError: If token retrieval fails
            NotFoundError: If character not found
            ExternalAPIError: If ESI request fails
        """
        all_blueprints = []
        page = 1

        # Fetch all pages
        while True:
            result = self._authenticated_get(
                character_id,
                f"/characters/{character_id}/blueprints/",
                {"datasource": "tranquility", "page": page}
            )

            if not result:
                break

            all_blueprints.extend(result)

            # ESI returns max 1000 items per page
            if len(result) < 1000:
                break

            page += 1

        # Convert to Blueprint models
        blueprints = [Blueprint(**bp) for bp in all_blueprints]

        # Categorize blueprints
        originals = [b for b in blueprints if b.quantity == -1]
        copies = [b for b in blueprints if b.quantity == -2]

        return BlueprintList(
            character_id=character_id,
            total_blueprints=len(blueprints),
            originals=len(originals),
            copies=len(copies),
            blueprints=blueprints
        )

    def get_character_info(self, character_id: int) -> CharacterInfo:
        """Get public character information (no auth required).

        Args:
            character_id: Character ID

        Returns:
            CharacterInfo: Character information

        Raises:
            NotFoundError: If character not found
            ExternalAPIError: If ESI request fails
        """
        result = self._public_get(f"/characters/{character_id}/")

        # Add character_id to result if not present
        result["character_id"] = character_id

        return CharacterInfo(**result)

    def get_corporation_id(self, character_id: int) -> Optional[int]:
        """Get corporation ID for a character.

        Args:
            character_id: Character ID

        Returns:
            Optional[int]: Corporation ID or None if not found

        Raises:
            NotFoundError: If character not found
            ExternalAPIError: If ESI request fails
        """
        info = self.get_character_info(character_id)
        return info.corporation_id

    def get_corporation_info(self, corporation_id: int) -> CorporationInfo:
        """Get public corporation information (no auth required).

        Args:
            corporation_id: Corporation ID

        Returns:
            CorporationInfo: Corporation information

        Raises:
            NotFoundError: If corporation not found
            ExternalAPIError: If ESI request fails
        """
        result = self._public_get(f"/corporations/{corporation_id}/")

        # Add corporation_id to result if not present
        result["corporation_id"] = corporation_id

        return CorporationInfo(**result)

    def get_corporation_wallets(self, character_id: int) -> CorporationWallet:
        """Get corporation wallet balances (requires Director or Accountant role).

        Args:
            character_id: Character ID (uses their token to access corp wallets)

        Returns:
            CorporationWallet: Corporation wallets

        Raises:
            AuthenticationError: If token retrieval fails
            NotFoundError: If corporation not found
            ExternalAPIError: If ESI request fails (e.g., insufficient permissions)
        """
        # Get corporation ID
        corp_id = self.get_corporation_id(character_id)
        if not corp_id:
            raise NotFoundError("Corporation", "unknown")

        # Get corporation info for name
        corp_info = self.get_corporation_info(corp_id)

        # Get wallet divisions
        result = self._authenticated_get(
            character_id,
            f"/corporations/{corp_id}/wallets/"
        )

        divisions = [CorporationWalletDivision(**div) for div in result]
        total_balance = sum(d.balance for d in divisions)

        return CorporationWallet(
            corporation_id=corp_id,
            corporation_name=corp_info.name,
            divisions=divisions,
            total_balance=total_balance,
            formatted_total=f"{total_balance:,.2f} ISK"
        )

    def get_corporation_wallet_journal(
        self,
        character_id: int,
        division: int = 1
    ) -> Dict[str, Any]:
        """Get corporation wallet journal for a division.

        Args:
            character_id: Character ID (uses their token to access corp journal)
            division: Wallet division (1-7)

        Returns:
            Dict[str, Any]: Journal entries with metadata

        Raises:
            AuthenticationError: If token retrieval fails
            NotFoundError: If corporation not found
            ExternalAPIError: If ESI request fails
        """
        # Get corporation ID
        corp_id = self.get_corporation_id(character_id)
        if not corp_id:
            raise NotFoundError("Corporation", "unknown")

        # Get journal entries
        result = self._authenticated_get(
            character_id,
            f"/corporations/{corp_id}/wallets/{division}/journal/"
        )

        return {
            "corporation_id": corp_id,
            "division": division,
            "entries": len(result),
            "journal": result
        }

    def get_character_portrait(self, character_id: int) -> Dict[str, str]:
        """
        Get character portrait URL with 24h caching.

        This method fetches the character portrait from ESI and caches it
        in the database for 24 hours to reduce API calls.

        Args:
            character_id: Character ID

        Returns:
            Dict containing portrait URL: {"url": "https://..."}

        Raises:
            ExternalAPIError: If ESI request fails
        """
        from datetime import datetime, timedelta

        # Check cache first
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT portrait_url, last_updated
                        FROM character_portraits_cache
                        WHERE character_id = %s
                    """, (character_id,))
                    cached = cur.fetchone()

                    # If cache exists and is less than 24h old, return it
                    if cached:
                        age = datetime.now() - cached['last_updated']
                        if age < timedelta(hours=24):
                            return {"url": cached['portrait_url']}
        except Exception:
            # If cache lookup fails, continue to fetch from ESI
            pass

        # Fetch from ESI
        try:
            url = f"{self.esi.base_url}/characters/{character_id}/portrait/"
            response = self.esi.session.get(
                url,
                params={"datasource": "tranquility"},
                timeout=10
            )

            if response.status_code == 404:
                # Character not found - return default avatar
                default_url = "https://images.evetech.net/characters/1/portrait?size=256"
                return {"url": default_url}

            if response.status_code != 200:
                raise ExternalAPIError(
                    service_name="ESI",
                    status_code=response.status_code,
                    message=f"Failed to fetch character portrait: {response.text}"
                )

            data = response.json()
            portrait_url = data.get("px256x256", "")

            # Cache the result
            try:
                with self.db.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO character_portraits_cache (character_id, portrait_url, last_updated)
                            VALUES (%s, %s, NOW())
                            ON CONFLICT (character_id)
                            DO UPDATE SET
                                portrait_url = EXCLUDED.portrait_url,
                                last_updated = NOW()
                        """, (character_id, portrait_url))
                        conn.commit()
            except Exception:
                # If cache write fails, still return the result
                pass

            return {"url": portrait_url}

        except Timeout:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message="Request timeout while fetching character portrait"
            )
        except RequestException as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Request failed: {str(e)}"
            )
        except ExternalAPIError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Unexpected error: {str(e)}"
            )
