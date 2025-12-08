"""Market Service - Business logic layer combining ESI Client and Repository."""

from datetime import datetime
from typing import Dict, List, Optional

from src.integrations.esi.client import ESIClient
from src.services.market.repository import MarketRepository
from src.services.market.models import MarketPrice, CacheStats, PriceUpdate
from src.core.exceptions import EVECopilotError, ExternalAPIError


class MarketService:
    """
    Market Service provides business logic for market price operations.

    This service combines the ESI Client (for external API calls) with the
    Market Repository (for database operations) and adds memory caching
    for ultra-fast price lookups.

    Responsibilities:
    - Orchestrate price updates from ESI to database
    - Manage in-memory cache for performance optimization
    - Provide high-level business logic for material cost calculations
    - Ensure cache freshness with automatic updates

    Pattern: Dependency Injection
    - No direct database access (delegates to repository)
    - No direct API access (delegates to ESI client)
    - Returns Pydantic models for type safety
    """

    def __init__(self, esi_client: ESIClient, repository: MarketRepository):
        """
        Initialize Market Service with dependencies.

        Args:
            esi_client: ESI API client for fetching market prices
            repository: Market repository for database operations
        """
        self.esi_client = esi_client
        self.repository = repository

        # Memory cache for ultra-fast lookups
        self._memory_cache: Dict[int, float] = {}
        self._cache_loaded: bool = False

    def update_global_prices(self) -> PriceUpdate:
        """
        Fetch all market prices from ESI and bulk upsert to database.

        This method orchestrates the complete price update workflow:
        1. Fetch prices from ESI API
        2. Convert to MarketPrice models
        3. Bulk upsert to database via repository
        4. Invalidate memory cache
        5. Return update statistics

        Returns:
            PriceUpdate: Update result with statistics

        Raises:
            ExternalAPIError: If ESI API call fails
            EVECopilotError: If database operation fails
        """
        # Fetch prices from ESI
        esi_data = self.esi_client.get_market_prices()

        if not esi_data:
            # Empty response is valid (no error, just no data)
            return PriceUpdate(
                success=True,
                items_updated=0,
                timestamp=datetime.now(),
                message="No price data received from ESI"
            )

        # Convert to MarketPrice models
        now = datetime.now()
        prices = []

        for item in esi_data:
            type_id = item.get("type_id")
            if type_id:
                prices.append(MarketPrice(
                    type_id=type_id,
                    adjusted_price=item.get("adjusted_price", 0.0) or 0.0,
                    average_price=item.get("average_price", 0.0) or 0.0,
                    last_updated=now
                ))

        # Bulk upsert to database
        rows_affected = self.repository.bulk_upsert_prices(prices)

        # Invalidate memory cache
        self._memory_cache.clear()
        self._cache_loaded = False

        return PriceUpdate(
            success=True,
            items_updated=rows_affected,
            timestamp=now,
            message=f"Updated {rows_affected:,} market prices in cache"
        )

    def get_cache_stats(self) -> CacheStats:
        """
        Get statistics about the price cache.

        Delegates to repository to retrieve database cache statistics.

        Returns:
            CacheStats: Cache statistics including age and staleness

        Raises:
            EVECopilotError: If database operation fails
        """
        return self.repository.get_cache_stats()

    def load_prices_to_memory(self) -> int:
        """
        Load all cached prices into memory for ultra-fast lookups.

        This method loads all prices from the database into a memory dictionary,
        enabling O(1) lookup performance for price queries. Ideal for bulk
        operations or when making many price lookups.

        The memory cache uses {type_id: adjusted_price} mapping.

        Returns:
            int: Number of prices loaded into memory

        Raises:
            EVECopilotError: If database operation fails
        """
        # Fetch all prices from repository
        all_prices = self.repository.get_prices_bulk([])

        # Clear existing cache
        self._memory_cache.clear()

        # Load into memory cache
        for price_data in all_prices:
            type_id = price_data.get("type_id")
            adjusted_price = price_data.get("adjusted_price")

            if type_id and adjusted_price is not None:
                self._memory_cache[type_id] = adjusted_price

        # Mark cache as loaded
        self._cache_loaded = True

        return len(self._memory_cache)

    def get_cached_price(self, type_id: int) -> Optional[float]:
        """
        Get adjusted price from cache (memory-first, fallback to database).

        Performance optimization:
        - If memory cache is loaded: O(1) dictionary lookup
        - If memory cache not loaded: Database query via repository

        Args:
            type_id: EVE type ID to lookup

        Returns:
            Optional[float]: Adjusted price or None if not found

        Raises:
            EVECopilotError: If database operation fails (when falling back)
        """
        # Use memory cache if loaded
        if self._cache_loaded:
            return self._memory_cache.get(type_id)

        # Fallback to database
        price_data = self.repository.get_price(type_id)
        if price_data:
            return price_data.get("adjusted_price")

        return None

    def get_cached_prices_bulk(self, type_ids: List[int]) -> Dict[int, float]:
        """
        Get multiple prices at once for efficiency.

        Returns a dictionary mapping type_id to adjusted_price. Missing prices
        default to 0.0 for consistent behavior in calculations.

        Performance:
        - Memory cache: O(n) where n = len(type_ids)
        - Database: Single bulk query

        Args:
            type_ids: List of type IDs to fetch

        Returns:
            Dict[int, float]: Mapping of type_id to adjusted_price (0.0 if missing)

        Raises:
            EVECopilotError: If database operation fails (when falling back)
        """
        if not type_ids:
            return {}

        # Use memory cache if loaded
        if self._cache_loaded:
            return {
                type_id: self._memory_cache.get(type_id, 0.0)
                for type_id in type_ids
            }

        # Fallback to database bulk query
        price_data_list = self.repository.get_prices_bulk(type_ids)

        # Convert to dictionary
        result = {type_id: 0.0 for type_id in type_ids}
        for price_data in price_data_list:
            type_id = price_data.get("type_id")
            adjusted_price = price_data.get("adjusted_price")
            if type_id and adjusted_price is not None:
                result[type_id] = adjusted_price

        return result

    def calculate_material_cost(self, bom: Dict[int, int]) -> float:
        """
        Calculate total material cost from cached prices.

        This is a business logic method that uses bulk price lookups to
        efficiently calculate the total cost of materials in a bill of materials.

        Args:
            bom: Bill of materials as {type_id: quantity}

        Returns:
            float: Total cost based on adjusted prices

        Raises:
            EVECopilotError: If database operation fails (when prices not cached)

        Example:
            >>> service = MarketService(esi_client, repository)
            >>> bom = {34: 10, 35: 5}  # 10x Tritanium, 5x Pyerite
            >>> total_cost = service.calculate_material_cost(bom)
            >>> print(f"Total: {total_cost:,.2f} ISK")
        """
        if not bom:
            return 0.0

        # Get all prices in one bulk operation
        prices = self.get_cached_prices_bulk(list(bom.keys()))

        # Calculate total cost
        total = 0.0
        for type_id, quantity in bom.items():
            price = prices.get(type_id, 0.0)
            total += price * quantity

        return total

    def ensure_cache_fresh(self, max_age_seconds: int = 3600) -> CacheStats | PriceUpdate:
        """
        Ensure cache is fresh, update if stale or empty.

        This orchestration method implements the following logic:
        1. Check cache statistics
        2. If cache is empty: trigger update
        3. If cache is older than max_age: trigger update
        4. Otherwise: return cache stats (cache is fresh)

        Args:
            max_age_seconds: Maximum age before cache is considered stale (default: 1 hour)

        Returns:
            CacheStats | PriceUpdate: Cache stats if fresh, update result if updated

        Raises:
            ExternalAPIError: If ESI API call fails during update
            EVECopilotError: If database operation fails
        """
        # Get current cache statistics
        stats = self.get_cache_stats()

        # Check if cache is empty
        if stats.total_items == 0:
            # Cache empty, need to update
            return self.update_global_prices()

        # Check if cache is stale
        age = stats.cache_age_seconds
        if age is None or age > max_age_seconds:
            # Cache stale, need to update
            return self.update_global_prices()

        # Cache is fresh
        return stats
