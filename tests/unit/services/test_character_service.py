"""Tests for character service business logic."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from requests.exceptions import Timeout, RequestException

from src.core.exceptions import NotFoundError, ExternalAPIError, AuthenticationError


@pytest.fixture
def mock_esi_client():
    """Mock ESI client."""
    client = Mock()
    client.base_url = "https://esi.evetech.net/latest"
    client.session = Mock()
    return client


@pytest.fixture
def mock_auth_service():
    """Mock auth service."""
    service = Mock()
    service.get_valid_token.return_value = "valid_access_token_12345"
    return service


@pytest.fixture
def mock_db():
    """Mock database pool."""
    db = Mock()
    return db


@pytest.fixture
def character_service(mock_esi_client, mock_auth_service, mock_db):
    """Create CharacterService instance with mocked dependencies."""
    from src.services.character.service import CharacterService
    return CharacterService(mock_esi_client, mock_auth_service, mock_db)


class TestGetWalletBalance:
    """Tests for get_wallet_balance method."""

    def test_get_wallet_balance_success(self, character_service, mock_auth_service, mock_esi_client):
        """Test successful wallet balance retrieval."""
        from src.services.character.models import WalletBalance

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = 1234567890.50
        mock_esi_client.session.get.return_value = mock_response

        result = character_service.get_wallet_balance(123456)

        assert isinstance(result, WalletBalance)
        assert result.character_id == 123456
        assert result.balance == 1234567890.50
        assert result.formatted == "1,234,567,890.50 ISK"

        # Verify token was requested
        mock_auth_service.get_valid_token.assert_called_once_with(123456)

        # Verify ESI call
        mock_esi_client.session.get.assert_called_once()
        call_args = mock_esi_client.session.get.call_args
        assert "/characters/123456/wallet/" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer valid_access_token_12345"

    def test_get_wallet_balance_auth_error(self, character_service, mock_auth_service):
        """Test wallet balance with authentication failure."""
        mock_auth_service.get_valid_token.side_effect = AuthenticationError("No token")

        with pytest.raises(AuthenticationError):
            character_service.get_wallet_balance(123456)

    def test_get_wallet_balance_404(self, character_service, mock_esi_client):
        """Test wallet balance with 404 response."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Character not found"
        mock_esi_client.session.get.return_value = mock_response

        with pytest.raises(NotFoundError) as exc_info:
            character_service.get_wallet_balance(123456)

        assert exc_info.value.resource == "Character"
        assert exc_info.value.resource_id == 123456

    def test_get_wallet_balance_403(self, character_service, mock_esi_client):
        """Test wallet balance with insufficient permissions."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Insufficient permissions"
        mock_esi_client.session.get.return_value = mock_response

        with pytest.raises(ExternalAPIError) as exc_info:
            character_service.get_wallet_balance(123456)

        assert exc_info.value.service_name == "ESI"
        assert exc_info.value.status_code == 403

    def test_get_wallet_balance_timeout(self, character_service, mock_esi_client):
        """Test wallet balance with timeout."""
        mock_esi_client.session.get.side_effect = Timeout("Request timed out")

        with pytest.raises(ExternalAPIError) as exc_info:
            character_service.get_wallet_balance(123456)

        assert "timeout" in str(exc_info.value).lower()


class TestGetAssets:
    """Tests for get_assets method."""

    def test_get_assets_success_single_page(self, character_service, mock_esi_client):
        """Test successful assets retrieval with single page."""
        from src.services.character.models import AssetList

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "item_id": 1000000000001,
                "type_id": 648,
                "location_id": 60003760,
                "location_type": "station",
                "quantity": 1,
                "location_flag": "Hangar",
                "is_singleton": True
            },
            {
                "item_id": 1000000000002,
                "type_id": 34,
                "location_id": 60003760,
                "location_type": "station",
                "quantity": 10000,
                "location_flag": "Hangar",
                "is_singleton": False
            }
        ]
        mock_esi_client.session.get.return_value = mock_response

        result = character_service.get_assets(123456)

        assert isinstance(result, AssetList)
        assert result.character_id == 123456
        assert result.total_items == 2
        assert len(result.assets) == 2

    def test_get_assets_with_location_filter(self, character_service, mock_esi_client):
        """Test assets retrieval with location filter."""
        from src.services.character.models import AssetList

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "item_id": 1000000000001,
                "type_id": 648,
                "location_id": 60003760,
                "location_type": "station",
                "quantity": 1,
                "location_flag": "Hangar",
                "is_singleton": True
            },
            {
                "item_id": 1000000000002,
                "type_id": 34,
                "location_id": 60008494,
                "location_type": "station",
                "quantity": 10000,
                "location_flag": "Hangar",
                "is_singleton": False
            }
        ]
        mock_esi_client.session.get.return_value = mock_response

        result = character_service.get_assets(123456, location_id=60003760)

        assert isinstance(result, AssetList)
        assert result.total_items == 1
        assert result.assets[0].location_id == 60003760

    def test_get_assets_pagination(self, character_service, mock_esi_client):
        """Test assets retrieval with pagination."""
        from src.services.character.models import AssetList

        # First page - full 1000 items
        page1_assets = [
            {
                "item_id": i + 1,  # Start from 1, not 0
                "type_id": 34,
                "location_id": 60003760,
                "location_type": "station",
                "quantity": 100,
                "location_flag": "Hangar",
                "is_singleton": False
            }
            for i in range(1000)
        ]

        # Second page - partial
        page2_assets = [
            {
                "item_id": i + 1,  # Start from 1, not 0
                "type_id": 34,
                "location_id": 60003760,
                "location_type": "station",
                "quantity": 100,
                "location_flag": "Hangar",
                "is_singleton": False
            }
            for i in range(1000, 1500)
        ]

        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = page1_assets

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = page2_assets

        mock_esi_client.session.get.side_effect = [mock_response1, mock_response2]

        result = character_service.get_assets(123456)

        assert result.total_items == 1500
        assert mock_esi_client.session.get.call_count == 2


class TestGetAssetNames:
    """Tests for get_asset_names method."""

    def test_get_asset_names_success(self, character_service, mock_esi_client):
        """Test successful asset names retrieval."""
        from src.services.character.models import AssetName

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"item_id": 1000000000001, "name": "My Raven"},
            {"item_id": 1000000000002, "name": "Loot Container"}
        ]
        mock_esi_client.session.post.return_value = mock_response

        result = character_service.get_asset_names(123456, [1000000000001, 1000000000002])

        assert len(result) == 2
        assert all(isinstance(item, AssetName) for item in result)
        assert result[0].name == "My Raven"

        # Verify POST was used
        mock_esi_client.session.post.assert_called_once()

    def test_get_asset_names_truncates_to_1000(self, character_service, mock_esi_client):
        """Test asset names truncates item_ids to max 1000."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_esi_client.session.post.return_value = mock_response

        item_ids = list(range(2000))
        character_service.get_asset_names(123456, item_ids)

        # Check that only 1000 items were sent
        call_args = mock_esi_client.session.post.call_args
        assert len(call_args[1]["json"]) == 1000


class TestGetSkills:
    """Tests for get_skills method."""

    def test_get_skills_success(self, character_service, mock_esi_client, mock_db):
        """Test successful skills retrieval with SDE enrichment."""
        from src.services.character.models import SkillData

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_sp": 50000000,
            "unallocated_sp": 100000,
            "skills": [
                {
                    "skill_id": 3300,
                    "active_skill_level": 5,
                    "trained_skill_level": 5,
                    "skillpoints_in_skill": 1280000
                },
                {
                    "skill_id": 3301,
                    "active_skill_level": 4,
                    "trained_skill_level": 4,
                    "skillpoints_in_skill": 226275
                }
            ]
        }
        mock_esi_client.session.get.return_value = mock_response

        # Mock database connection with context managers
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Setup context manager for get_connection
        mock_db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)

        # Setup context manager for cursor
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        # Mock skill name lookups
        def mock_fetchone():
            # Track which call this is
            if not hasattr(mock_fetchone, 'call_count'):
                mock_fetchone.call_count = 0

            call_count = mock_fetchone.call_count
            mock_fetchone.call_count += 1

            if call_count == 0:
                return {"typeName": "Gunnery"}
            elif call_count == 1:
                return {"typeName": "Small Hybrid Turret"}
            return None

        mock_cursor.fetchone.side_effect = mock_fetchone

        result = character_service.get_skills(123456)

        assert isinstance(result, SkillData)
        assert result.total_sp == 50000000
        assert result.skill_count == 2
        assert result.skills[0].skill_name == "Gunnery"
        assert result.skills[0].level == 5

    def test_get_skills_without_db_enrichment(self, character_service, mock_esi_client, mock_db):
        """Test skills retrieval when DB lookup fails."""
        from src.services.character.models import SkillData

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_sp": 50000000,
            "unallocated_sp": 0,
            "skills": [
                {
                    "skill_id": 3300,
                    "active_skill_level": 5,
                    "trained_skill_level": 5,
                    "skillpoints_in_skill": 1280000
                }
            ]
        }
        mock_esi_client.session.get.return_value = mock_response

        # Mock database connection that returns None (skill not found)
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Setup context manager for get_connection
        mock_db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)

        # Setup context manager for cursor
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        mock_cursor.fetchone.return_value = None

        result = character_service.get_skills(123456)

        assert isinstance(result, SkillData)
        assert result.skills[0].skill_name == "Unknown"


class TestGetSkillQueue:
    """Tests for get_skill_queue method."""

    def test_get_skill_queue_success(self, character_service, mock_esi_client):
        """Test successful skill queue retrieval."""
        from src.services.character.models import SkillQueue

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "skill_id": 3300,
                "finished_level": 5,
                "queue_position": 0,
                "start_date": "2024-01-01T00:00:00Z",
                "finish_date": "2024-01-02T00:00:00Z"
            }
        ]
        mock_esi_client.session.get.return_value = mock_response

        result = character_service.get_skill_queue(123456)

        assert isinstance(result, SkillQueue)
        assert result.queue_length == 1
        assert result.queue[0].skill_id == 3300

    def test_get_skill_queue_empty(self, character_service, mock_esi_client):
        """Test empty skill queue."""
        from src.services.character.models import SkillQueue

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_esi_client.session.get.return_value = mock_response

        result = character_service.get_skill_queue(123456)

        assert isinstance(result, SkillQueue)
        assert result.queue_length == 0


class TestGetMarketOrders:
    """Tests for get_market_orders method."""

    def test_get_market_orders_success(self, character_service, mock_esi_client):
        """Test successful market orders retrieval."""
        from src.services.character.models import MarketOrderList

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "order_id": 1,
                "type_id": 34,
                "location_id": 60003760,
                "volume_total": 1000,
                "volume_remain": 500,
                "min_volume": 1,
                "price": 5.0,
                "is_buy_order": False,
                "duration": 90,
                "issued": "2024-01-01T00:00:00Z",
                "range": "region",
                "region_id": 10000002,
                "state": "active"
            },
            {
                "order_id": 2,
                "type_id": 35,
                "location_id": 60003760,
                "volume_total": 2000,
                "volume_remain": 2000,
                "min_volume": 1,
                "price": 4.0,
                "is_buy_order": True,
                "duration": 90,
                "issued": "2024-01-01T00:00:00Z",
                "range": "station",
                "region_id": 10000002,
                "state": "active"
            }
        ]
        mock_esi_client.session.get.return_value = mock_response

        result = character_service.get_market_orders(123456)

        assert isinstance(result, MarketOrderList)
        assert result.total_orders == 2
        assert result.buy_orders == 1
        assert result.sell_orders == 1


class TestGetIndustryJobs:
    """Tests for get_industry_jobs method."""

    def test_get_industry_jobs_active_only(self, character_service, mock_esi_client):
        """Test industry jobs retrieval (active only)."""
        from src.services.character.models import IndustryJobList

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "job_id": 1,
                "installer_id": 123456,
                "facility_id": 60003760,
                "location_id": 60003760,
                "activity_id": 1,
                "blueprint_id": 1000000000001,
                "blueprint_type_id": 1234,
                "blueprint_location_id": 60003760,
                "output_location_id": 60003760,
                "runs": 10,
                "status": "active",
                "duration": 3600,
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-01T01:00:00Z"
            }
        ]
        mock_esi_client.session.get.return_value = mock_response

        result = character_service.get_industry_jobs(123456, include_completed=False)

        assert isinstance(result, IndustryJobList)
        assert result.total_jobs == 1
        assert result.active_jobs == 1

        # Verify include_completed param
        call_args = mock_esi_client.session.get.call_args
        assert call_args[1]["params"]["include_completed"] is False

    def test_get_industry_jobs_include_completed(self, character_service, mock_esi_client):
        """Test industry jobs with completed jobs included."""
        from src.services.character.models import IndustryJobList

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "job_id": 1,
                "installer_id": 123456,
                "facility_id": 60003760,
                "location_id": 60003760,
                "activity_id": 1,
                "blueprint_id": 1000000000001,
                "blueprint_type_id": 1234,
                "blueprint_location_id": 60003760,
                "output_location_id": 60003760,
                "runs": 10,
                "status": "delivered",
                "duration": 3600,
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-01T01:00:00Z",
                "completed_date": "2024-01-01T01:00:00Z"
            }
        ]
        mock_esi_client.session.get.return_value = mock_response

        result = character_service.get_industry_jobs(123456, include_completed=True)

        assert result.total_jobs == 1
        assert result.active_jobs == 0  # No active jobs


class TestGetBlueprints:
    """Tests for get_blueprints method."""

    def test_get_blueprints_success(self, character_service, mock_esi_client):
        """Test successful blueprints retrieval."""
        from src.services.character.models import BlueprintList

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "item_id": 1000000000001,
                "type_id": 648,
                "location_id": 60003760,
                "location_flag": "Hangar",
                "quantity": -1,  # Original
                "time_efficiency": 20,
                "material_efficiency": 10
                # runs is optional and not present for originals
            },
            {
                "item_id": 1000000000002,
                "type_id": 649,
                "location_id": 60003760,
                "location_flag": "Hangar",
                "quantity": -2,  # Copy
                "time_efficiency": 0,
                "material_efficiency": 0,
                "runs": 10
            }
        ]
        mock_esi_client.session.get.return_value = mock_response

        result = character_service.get_blueprints(123456)

        assert isinstance(result, BlueprintList)
        assert result.total_blueprints == 2
        assert result.originals == 1
        assert result.copies == 1


class TestGetCharacterInfo:
    """Tests for get_character_info method."""

    def test_get_character_info_success(self, character_service, mock_esi_client):
        """Test successful character info retrieval (public endpoint)."""
        from src.services.character.models import CharacterInfo

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Test Character",
            "corporation_id": 98000001,
            "birthday": "2015-01-01T00:00:00Z",
            "gender": "male",
            "race_id": 1,
            "bloodline_id": 3
        }
        mock_esi_client.session.get.return_value = mock_response

        result = character_service.get_character_info(123456)

        assert isinstance(result, CharacterInfo)
        assert result.name == "Test Character"
        assert result.corporation_id == 98000001

        # Verify no auth token was used (public endpoint)
        call_args = mock_esi_client.session.get.call_args
        assert "Authorization" not in call_args[1].get("headers", {})

    def test_get_character_info_404(self, character_service, mock_esi_client):
        """Test character info with invalid character ID."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Character not found"
        mock_esi_client.session.get.return_value = mock_response

        with pytest.raises(NotFoundError):
            character_service.get_character_info(999999999)


class TestGetCorporationId:
    """Tests for get_corporation_id method."""

    def test_get_corporation_id_success(self, character_service, mock_esi_client):
        """Test getting corporation ID from character info."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Test Character",
            "corporation_id": 98000001,
            "birthday": "2015-01-01T00:00:00Z",
            "gender": "male",
            "race_id": 1,
            "bloodline_id": 3
        }
        mock_esi_client.session.get.return_value = mock_response

        result = character_service.get_corporation_id(123456)

        assert result == 98000001


class TestGetCorporationInfo:
    """Tests for get_corporation_info method."""

    def test_get_corporation_info_success(self, character_service, mock_esi_client):
        """Test successful corporation info retrieval."""
        from src.services.character.models import CorporationInfo

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Test Corporation",
            "ticker": "TEST",
            "member_count": 100,
            "ceo_id": 123456,
            "creator_id": 123456,
            "tax_rate": 0.05
        }
        mock_esi_client.session.get.return_value = mock_response

        result = character_service.get_corporation_info(98000001)

        assert isinstance(result, CorporationInfo)
        assert result.name == "Test Corporation"
        assert result.ticker == "TEST"


class TestGetCorporationWallets:
    """Tests for get_corporation_wallets method."""

    def test_get_corporation_wallets_success(self, character_service, mock_esi_client):
        """Test successful corporation wallets retrieval."""
        from src.services.character.models import CorporationWallet

        # Mock character info call
        char_info_response = Mock()
        char_info_response.status_code = 200
        char_info_response.json.return_value = {
            "name": "Test Character",
            "corporation_id": 98000001,
            "birthday": "2015-01-01T00:00:00Z",
            "gender": "male",
            "race_id": 1,
            "bloodline_id": 3
        }

        # Mock corp info call
        corp_info_response = Mock()
        corp_info_response.status_code = 200
        corp_info_response.json.return_value = {
            "name": "Test Corporation",
            "ticker": "TEST",
            "member_count": 100,
            "ceo_id": 123456,
            "creator_id": 123456,
            "tax_rate": 0.05
        }

        # Mock wallets call
        wallets_response = Mock()
        wallets_response.status_code = 200
        wallets_response.json.return_value = [
            {"division": 1, "balance": 1000000.0},
            {"division": 2, "balance": 500000.0}
        ]

        mock_esi_client.session.get.side_effect = [
            char_info_response,
            corp_info_response,
            wallets_response
        ]

        result = character_service.get_corporation_wallets(123456)

        assert isinstance(result, CorporationWallet)
        assert result.corporation_name == "Test Corporation"
        assert result.total_balance == 1500000.0
        assert len(result.divisions) == 2


class TestGetCorporationWalletJournal:
    """Tests for get_corporation_wallet_journal method."""

    def test_get_corporation_wallet_journal_success(self, character_service, mock_esi_client):
        """Test successful corporation wallet journal retrieval."""
        # Mock character info call
        char_info_response = Mock()
        char_info_response.status_code = 200
        char_info_response.json.return_value = {
            "name": "Test Character",
            "corporation_id": 98000001,
            "birthday": "2015-01-01T00:00:00Z",
            "gender": "male",
            "race_id": 1,
            "bloodline_id": 3
        }

        # Mock journal call
        journal_response = Mock()
        journal_response.status_code = 200
        journal_response.json.return_value = [
            {
                "id": 1,
                "date": "2024-01-01T00:00:00Z",
                "ref_type": "bounty_prizes",
                "amount": 100000.0,
                "description": "Bounty prize"
            }
        ]

        mock_esi_client.session.get.side_effect = [char_info_response, journal_response]

        result = character_service.get_corporation_wallet_journal(123456, division=1)

        assert isinstance(result, dict)
        assert result["corporation_id"] == 98000001
        assert result["division"] == 1
        assert result["entries"] == 1
        assert len(result["journal"]) == 1

    def test_get_corporation_wallet_journal_default_division(self, character_service, mock_esi_client):
        """Test corporation wallet journal with default division."""
        # Mock character info call
        char_info_response = Mock()
        char_info_response.status_code = 200
        char_info_response.json.return_value = {
            "name": "Test Character",
            "corporation_id": 98000001,
            "birthday": "2015-01-01T00:00:00Z",
            "gender": "male",
            "race_id": 1,
            "bloodline_id": 3
        }

        # Mock journal call
        journal_response = Mock()
        journal_response.status_code = 200
        journal_response.json.return_value = []

        mock_esi_client.session.get.side_effect = [char_info_response, journal_response]

        result = character_service.get_corporation_wallet_journal(123456)

        # Verify division 1 was used
        call_args = mock_esi_client.session.get.call_args_list[1]
        assert "/wallets/1/journal/" in call_args[0][0]
