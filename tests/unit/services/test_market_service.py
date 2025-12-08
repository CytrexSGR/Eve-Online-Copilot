"""Test suite for Market Service business logic - TDD approach."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List

from src.services.market.service import MarketService
from src.services.market.models import MarketPrice, CacheStats, PriceUpdate
from src.core.exceptions import EVECopilotError, ExternalAPIError


class TestMarketServiceInit:
    """Test MarketService initialization."""

    def test_service_initialization(self):
        """Test that service initializes with dependencies."""
        mock_esi = Mock()
        mock_repo = Mock()

        service = MarketService(esi_client=mock_esi, repository=mock_repo)

        assert service.esi_client == mock_esi
        assert service.repository == mock_repo
        assert isinstance(service._memory_cache, dict)
        assert len(service._memory_cache) == 0
        assert service._cache_loaded is False


class TestUpdateGlobalPrices:
    """Test update_global_prices method - fetch from ESI, bulk upsert to repo."""

    def test_successful_update(self):
        """Test successful price update from ESI."""
        mock_esi = Mock()
        mock_repo = Mock()

        # Mock ESI response
        esi_data = [
            {"type_id": 34, "adjusted_price": 1000.0, "average_price": 1100.0},
            {"type_id": 35, "adjusted_price": 2000.0, "average_price": 2200.0},
            {"type_id": 36, "adjusted_price": 3000.0}  # No average_price
        ]
        mock_esi.get_market_prices.return_value = esi_data
        mock_repo.bulk_upsert_prices.return_value = 3

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        result = service.update_global_prices()

        # Verify ESI was called
        mock_esi.get_market_prices.assert_called_once()

        # Verify repository was called with correct data
        assert mock_repo.bulk_upsert_prices.called
        prices_arg = mock_repo.bulk_upsert_prices.call_args[0][0]
        assert len(prices_arg) == 3
        assert all(isinstance(p, MarketPrice) for p in prices_arg)

        # Verify result
        assert isinstance(result, PriceUpdate)
        assert result.success is True
        assert result.items_updated == 3
        assert isinstance(result.timestamp, datetime)
        assert "3" in result.message

    def test_update_handles_missing_average_price(self):
        """Test that missing average_price defaults to 0."""
        mock_esi = Mock()
        mock_repo = Mock()

        esi_data = [
            {"type_id": 34, "adjusted_price": 1000.0}  # No average_price
        ]
        mock_esi.get_market_prices.return_value = esi_data
        mock_repo.bulk_upsert_prices.return_value = 1

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        result = service.update_global_prices()

        prices_arg = mock_repo.bulk_upsert_prices.call_args[0][0]
        assert prices_arg[0].average_price == 0.0
        assert result.success is True

    def test_update_invalidates_memory_cache(self):
        """Test that update clears memory cache."""
        mock_esi = Mock()
        mock_repo = Mock()

        esi_data = [{"type_id": 34, "adjusted_price": 1000.0, "average_price": 1100.0}]
        mock_esi.get_market_prices.return_value = esi_data
        mock_repo.bulk_upsert_prices.return_value = 1

        service = MarketService(esi_client=mock_esi, repository=mock_repo)

        # Pre-populate cache
        service._memory_cache = {34: 999.0}
        service._cache_loaded = True

        service.update_global_prices()

        # Verify cache was cleared
        assert len(service._memory_cache) == 0
        assert service._cache_loaded is False

    def test_update_handles_empty_esi_response(self):
        """Test handling of empty ESI response."""
        mock_esi = Mock()
        mock_repo = Mock()

        mock_esi.get_market_prices.return_value = []

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        result = service.update_global_prices()

        assert result.success is True
        assert result.items_updated == 0
        assert "No price data" in result.message

    def test_update_handles_esi_error(self):
        """Test handling of ESI API errors."""
        mock_esi = Mock()
        mock_repo = Mock()

        mock_esi.get_market_prices.side_effect = ExternalAPIError(
            service_name="ESI",
            status_code=500,
            message="Server error"
        )

        service = MarketService(esi_client=mock_esi, repository=mock_repo)

        with pytest.raises(ExternalAPIError):
            service.update_global_prices()

    def test_update_handles_repository_error(self):
        """Test handling of repository errors."""
        mock_esi = Mock()
        mock_repo = Mock()

        esi_data = [{"type_id": 34, "adjusted_price": 1000.0, "average_price": 1100.0}]
        mock_esi.get_market_prices.return_value = esi_data
        mock_repo.bulk_upsert_prices.side_effect = EVECopilotError("Database error")

        service = MarketService(esi_client=mock_esi, repository=mock_repo)

        with pytest.raises(EVECopilotError):
            service.update_global_prices()


class TestGetCacheStats:
    """Test get_cache_stats method - delegate to repository."""

    def test_get_cache_stats_success(self):
        """Test successful cache stats retrieval."""
        mock_esi = Mock()
        mock_repo = Mock()

        expected_stats = CacheStats(
            total_items=15000,
            oldest_entry=datetime.now() - timedelta(hours=2),
            newest_entry=datetime.now() - timedelta(minutes=30),
            cache_age_seconds=1800.0,
            is_stale=False
        )
        mock_repo.get_cache_stats.return_value = expected_stats

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        result = service.get_cache_stats()

        mock_repo.get_cache_stats.assert_called_once()
        assert result == expected_stats

    def test_get_cache_stats_empty(self):
        """Test cache stats when cache is empty."""
        mock_esi = Mock()
        mock_repo = Mock()

        expected_stats = CacheStats(
            total_items=0,
            oldest_entry=None,
            newest_entry=None,
            cache_age_seconds=None,
            is_stale=True
        )
        mock_repo.get_cache_stats.return_value = expected_stats

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        result = service.get_cache_stats()

        assert result.total_items == 0
        assert result.is_stale is True


class TestLoadPricesToMemory:
    """Test load_prices_to_memory method - load from repo to memory cache."""

    def test_load_prices_to_memory_success(self):
        """Test successful loading of prices to memory."""
        mock_esi = Mock()
        mock_repo = Mock()

        mock_prices = [
            {"type_id": 34, "adjusted_price": 1000.0},
            {"type_id": 35, "adjusted_price": 2000.0},
            {"type_id": 36, "adjusted_price": 3000.0}
        ]
        mock_repo.get_prices_bulk.return_value = mock_prices

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        count = service.load_prices_to_memory()

        assert count == 3
        assert service._cache_loaded is True
        assert service._memory_cache == {34: 1000.0, 35: 2000.0, 36: 3000.0}

    def test_load_prices_clears_existing_cache(self):
        """Test that loading prices clears existing memory cache."""
        mock_esi = Mock()
        mock_repo = Mock()

        mock_prices = [{"type_id": 34, "adjusted_price": 1000.0}]
        mock_repo.get_prices_bulk.return_value = mock_prices

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        service._memory_cache = {99: 999.0}  # Pre-existing data

        count = service.load_prices_to_memory()

        assert count == 1
        assert 99 not in service._memory_cache
        assert service._memory_cache == {34: 1000.0}

    def test_load_prices_empty_database(self):
        """Test loading when database is empty."""
        mock_esi = Mock()
        mock_repo = Mock()

        mock_repo.get_prices_bulk.return_value = []

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        count = service.load_prices_to_memory()

        assert count == 0
        assert service._cache_loaded is True
        assert len(service._memory_cache) == 0


class TestGetCachedPrice:
    """Test get_cached_price method - memory-first, fallback to repo."""

    def test_get_price_from_memory_cache(self):
        """Test price retrieval from memory cache."""
        mock_esi = Mock()
        mock_repo = Mock()

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        service._memory_cache = {34: 1000.0, 35: 2000.0}
        service._cache_loaded = True

        price = service.get_cached_price(34)

        assert price == 1000.0
        # Should NOT call repository
        mock_repo.get_price.assert_not_called()

    def test_get_price_not_in_memory(self):
        """Test that None is returned when price not in memory cache."""
        mock_esi = Mock()
        mock_repo = Mock()

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        service._memory_cache = {34: 1000.0}
        service._cache_loaded = True

        price = service.get_cached_price(99)

        assert price is None
        # Should NOT call repository when cache is loaded
        mock_repo.get_price.assert_not_called()

    def test_get_price_fallback_to_repository(self):
        """Test fallback to repository when memory cache not loaded."""
        mock_esi = Mock()
        mock_repo = Mock()

        mock_repo.get_price.return_value = {"type_id": 34, "adjusted_price": 1000.0}

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        service._cache_loaded = False

        price = service.get_cached_price(34)

        assert price == 1000.0
        mock_repo.get_price.assert_called_once_with(34)

    def test_get_price_repository_not_found(self):
        """Test repository fallback when price not found."""
        mock_esi = Mock()
        mock_repo = Mock()

        mock_repo.get_price.return_value = None

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        service._cache_loaded = False

        price = service.get_cached_price(99)

        assert price is None


class TestGetCachedPricesBulk:
    """Test get_cached_prices_bulk method - bulk lookup."""

    def test_bulk_get_from_memory_cache(self):
        """Test bulk price retrieval from memory cache."""
        mock_esi = Mock()
        mock_repo = Mock()

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        service._memory_cache = {34: 1000.0, 35: 2000.0, 36: 3000.0}
        service._cache_loaded = True

        prices = service.get_cached_prices_bulk([34, 35, 99])

        assert prices == {34: 1000.0, 35: 2000.0, 99: 0}
        mock_repo.get_prices_bulk.assert_not_called()

    def test_bulk_get_empty_list(self):
        """Test bulk get with empty list."""
        mock_esi = Mock()
        mock_repo = Mock()

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        prices = service.get_cached_prices_bulk([])

        assert prices == {}

    def test_bulk_get_fallback_to_repository(self):
        """Test bulk get falls back to repository when cache not loaded."""
        mock_esi = Mock()
        mock_repo = Mock()

        mock_repo.get_prices_bulk.return_value = [
            {"type_id": 34, "adjusted_price": 1000.0},
            {"type_id": 35, "adjusted_price": 2000.0}
        ]

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        service._cache_loaded = False

        prices = service.get_cached_prices_bulk([34, 35])

        assert prices == {34: 1000.0, 35: 2000.0}
        mock_repo.get_prices_bulk.assert_called_once_with([34, 35])

    def test_bulk_get_handles_missing_prices(self):
        """Test bulk get returns 0 for missing prices from repository."""
        mock_esi = Mock()
        mock_repo = Mock()

        # Only return price for type_id 34
        mock_repo.get_prices_bulk.return_value = [
            {"type_id": 34, "adjusted_price": 1000.0}
        ]

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        service._cache_loaded = False

        prices = service.get_cached_prices_bulk([34, 35, 36])

        # Should have 34 with real price, others default to 0
        assert prices[34] == 1000.0
        assert prices[35] == 0
        assert prices[36] == 0


class TestCalculateMaterialCost:
    """Test calculate_material_cost method - business logic."""

    def test_calculate_material_cost_success(self):
        """Test material cost calculation with valid BOM."""
        mock_esi = Mock()
        mock_repo = Mock()

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        service._memory_cache = {34: 1000.0, 35: 2000.0, 36: 3000.0}
        service._cache_loaded = True

        bom = {34: 10, 35: 5, 36: 2}  # {type_id: quantity}
        total_cost = service.calculate_material_cost(bom)

        # (1000*10) + (2000*5) + (3000*2) = 10000 + 10000 + 6000 = 26000
        assert total_cost == 26000.0

    def test_calculate_material_cost_empty_bom(self):
        """Test material cost with empty BOM."""
        mock_esi = Mock()
        mock_repo = Mock()

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        total_cost = service.calculate_material_cost({})

        assert total_cost == 0

    def test_calculate_material_cost_missing_prices(self):
        """Test material cost when some prices are missing (defaults to 0)."""
        mock_esi = Mock()
        mock_repo = Mock()

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        service._memory_cache = {34: 1000.0}
        service._cache_loaded = True

        bom = {34: 10, 99: 5}  # 99 not in cache
        total_cost = service.calculate_material_cost(bom)

        # (1000*10) + (0*5) = 10000
        assert total_cost == 10000.0

    def test_calculate_material_cost_uses_bulk_lookup(self):
        """Test that material cost uses bulk lookup for efficiency."""
        mock_esi = Mock()
        mock_repo = Mock()

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        service._cache_loaded = False

        mock_repo.get_prices_bulk.return_value = [
            {"type_id": 34, "adjusted_price": 1000.0},
            {"type_id": 35, "adjusted_price": 2000.0}
        ]

        bom = {34: 10, 35: 5}
        total_cost = service.calculate_material_cost(bom)

        assert total_cost == 20000.0
        mock_repo.get_prices_bulk.assert_called_once()


class TestEnsureCacheFresh:
    """Test ensure_cache_fresh method - orchestration logic."""

    def test_ensure_cache_fresh_when_empty(self):
        """Test that empty cache triggers update."""
        mock_esi = Mock()
        mock_repo = Mock()

        # Cache is empty
        mock_repo.get_cache_stats.return_value = CacheStats(
            total_items=0,
            oldest_entry=None,
            newest_entry=None,
            cache_age_seconds=None,
            is_stale=True
        )

        # Mock successful update
        mock_esi.get_market_prices.return_value = [
            {"type_id": 34, "adjusted_price": 1000.0, "average_price": 1100.0}
        ]
        mock_repo.bulk_upsert_prices.return_value = 1

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        result = service.ensure_cache_fresh(max_age_seconds=3600)

        assert isinstance(result, PriceUpdate)
        assert result.success is True
        mock_esi.get_market_prices.assert_called_once()

    def test_ensure_cache_fresh_when_stale(self):
        """Test that stale cache triggers update."""
        mock_esi = Mock()
        mock_repo = Mock()

        # Cache is stale (older than max_age)
        old_time = datetime.now() - timedelta(hours=2)
        mock_repo.get_cache_stats.return_value = CacheStats(
            total_items=1000,
            oldest_entry=old_time,
            newest_entry=old_time,
            cache_age_seconds=7200.0,  # 2 hours
            is_stale=True
        )

        # Mock successful update
        mock_esi.get_market_prices.return_value = [
            {"type_id": 34, "adjusted_price": 1000.0, "average_price": 1100.0}
        ]
        mock_repo.bulk_upsert_prices.return_value = 1

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        result = service.ensure_cache_fresh(max_age_seconds=3600)

        mock_esi.get_market_prices.assert_called_once()

    def test_ensure_cache_fresh_when_fresh(self):
        """Test that fresh cache does not trigger update."""
        mock_esi = Mock()
        mock_repo = Mock()

        # Cache is fresh
        recent_time = datetime.now() - timedelta(minutes=30)
        mock_repo.get_cache_stats.return_value = CacheStats(
            total_items=1000,
            oldest_entry=recent_time,
            newest_entry=recent_time,
            cache_age_seconds=1800.0,  # 30 minutes
            is_stale=False
        )

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        result = service.ensure_cache_fresh(max_age_seconds=3600)

        # Should return stats, not update
        assert isinstance(result, CacheStats)
        mock_esi.get_market_prices.assert_not_called()

    def test_ensure_cache_fresh_custom_max_age(self):
        """Test custom max_age parameter."""
        mock_esi = Mock()
        mock_repo = Mock()

        # Cache is 10 minutes old
        recent_time = datetime.now() - timedelta(minutes=10)
        mock_repo.get_cache_stats.return_value = CacheStats(
            total_items=1000,
            oldest_entry=recent_time,
            newest_entry=recent_time,
            cache_age_seconds=600.0,
            is_stale=False
        )

        service = MarketService(esi_client=mock_esi, repository=mock_repo)

        # With max_age=300 (5 minutes), cache should be considered stale
        mock_esi.get_market_prices.return_value = [
            {"type_id": 34, "adjusted_price": 1000.0, "average_price": 1100.0}
        ]
        mock_repo.bulk_upsert_prices.return_value = 1

        result = service.ensure_cache_fresh(max_age_seconds=300)

        mock_esi.get_market_prices.assert_called_once()


class TestMemoryCacheBehavior:
    """Test memory cache optimization behavior."""

    def test_memory_cache_prevents_db_calls(self):
        """Test that loaded memory cache prevents database calls."""
        mock_esi = Mock()
        mock_repo = Mock()

        service = MarketService(esi_client=mock_esi, repository=mock_repo)
        service._memory_cache = {34: 1000.0, 35: 2000.0}
        service._cache_loaded = True

        # Multiple calls should use memory cache
        price1 = service.get_cached_price(34)
        price2 = service.get_cached_price(35)
        prices_bulk = service.get_cached_prices_bulk([34, 35])

        assert price1 == 1000.0
        assert price2 == 2000.0
        assert prices_bulk == {34: 1000.0, 35: 2000.0}

        # Repository should never be called
        mock_repo.get_price.assert_not_called()
        mock_repo.get_prices_bulk.assert_not_called()

    def test_cache_invalidation_on_update(self):
        """Test that cache is properly invalidated on price update."""
        mock_esi = Mock()
        mock_repo = Mock()

        service = MarketService(esi_client=mock_esi, repository=mock_repo)

        # Load initial cache
        service._memory_cache = {34: 1000.0}
        service._cache_loaded = True

        # Update prices
        mock_esi.get_market_prices.return_value = [
            {"type_id": 34, "adjusted_price": 2000.0, "average_price": 2100.0}
        ]
        mock_repo.bulk_upsert_prices.return_value = 1

        service.update_global_prices()

        # Cache should be invalidated
        assert len(service._memory_cache) == 0
        assert service._cache_loaded is False
