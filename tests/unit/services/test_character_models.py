"""
Tests for Character Service Pydantic Models

Following TDD approach - tests written first before model implementation.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from pydantic import ValidationError

from src.services.character.models import (
    WalletBalance,
    Asset,
    AssetList,
    AssetName,
    Skill,
    SkillData,
    SkillQueueItem,
    SkillQueue,
    MarketOrder,
    MarketOrderList,
    IndustryJob,
    IndustryJobList,
    Blueprint,
    BlueprintList,
    CharacterInfo,
    CorporationInfo,
    CorporationWalletDivision,
    CorporationWallet,
)


class TestWalletBalance:
    """Test WalletBalance model"""

    def test_create_wallet_balance(self):
        """Test creating a wallet balance with valid data"""
        wallet = WalletBalance(
            character_id=526379435,
            balance=1500000.50
        )

        assert wallet.character_id == 526379435
        assert wallet.balance == 1500000.50
        assert wallet.formatted == "1,500,000.50 ISK"

    def test_wallet_balance_negative(self):
        """Test wallet balance can be negative"""
        wallet = WalletBalance(
            character_id=526379435,
            balance=-1000.00
        )

        assert wallet.balance == -1000.00
        assert wallet.formatted == "-1,000.00 ISK"

    def test_wallet_balance_zero(self):
        """Test wallet balance can be zero"""
        wallet = WalletBalance(
            character_id=526379435,
            balance=0
        )

        assert wallet.balance == 0
        assert wallet.formatted == "0.00 ISK"

    def test_wallet_balance_large_value(self):
        """Test wallet balance with large value"""
        wallet = WalletBalance(
            character_id=526379435,
            balance=1234567890.12
        )

        assert wallet.formatted == "1,234,567,890.12 ISK"

    def test_wallet_balance_invalid_character_id(self):
        """Test wallet balance with invalid character ID"""
        with pytest.raises(ValidationError):
            WalletBalance(character_id=-1, balance=1000.00)

    def test_wallet_balance_serialization(self):
        """Test wallet balance serialization"""
        wallet = WalletBalance(character_id=526379435, balance=1500000.50)
        data = wallet.model_dump()

        assert data["character_id"] == 526379435
        assert data["balance"] == 1500000.50
        assert data["formatted"] == "1,500,000.50 ISK"


class TestAsset:
    """Test Asset model"""

    def test_create_asset(self):
        """Test creating an asset with valid data"""
        asset = Asset(
            item_id=1234567890,
            type_id=648,
            location_id=60003760,
            quantity=100,
            is_singleton=False
        )

        assert asset.item_id == 1234567890
        assert asset.type_id == 648
        assert asset.location_id == 60003760
        assert asset.quantity == 100
        assert asset.is_singleton is False
        assert asset.location_flag is None
        assert asset.location_type is None

    def test_create_asset_with_optional_fields(self):
        """Test creating asset with all optional fields"""
        asset = Asset(
            item_id=1234567890,
            type_id=648,
            location_id=60003760,
            quantity=1,
            is_singleton=True,
            location_flag="Hangar",
            location_type="station"
        )

        assert asset.location_flag == "Hangar"
        assert asset.location_type == "station"

    def test_asset_invalid_quantity(self):
        """Test asset with invalid quantity"""
        with pytest.raises(ValidationError):
            Asset(
                item_id=1234567890,
                type_id=648,
                location_id=60003760,
                quantity=-1,
                is_singleton=False
            )

    def test_asset_zero_quantity(self):
        """Test asset with zero quantity"""
        with pytest.raises(ValidationError):
            Asset(
                item_id=1234567890,
                type_id=648,
                location_id=60003760,
                quantity=0,
                is_singleton=False
            )


class TestAssetList:
    """Test AssetList model"""

    def test_create_asset_list(self):
        """Test creating an asset list"""
        assets = [
            Asset(item_id=1, type_id=648, location_id=60003760, quantity=100, is_singleton=False),
            Asset(item_id=2, type_id=649, location_id=60003760, quantity=50, is_singleton=False),
        ]

        asset_list = AssetList(
            character_id=526379435,
            total_items=2,
            assets=assets
        )

        assert asset_list.character_id == 526379435
        assert asset_list.total_items == 2
        assert len(asset_list.assets) == 2

    def test_create_empty_asset_list(self):
        """Test creating an empty asset list"""
        asset_list = AssetList(
            character_id=526379435,
            total_items=0,
            assets=[]
        )

        assert asset_list.total_items == 0
        assert len(asset_list.assets) == 0

    def test_asset_list_count_mismatch(self):
        """Test that total_items should match assets length (validation)"""
        # This should work - the model should validate this
        assets = [
            Asset(item_id=1, type_id=648, location_id=60003760, quantity=100, is_singleton=False),
        ]

        # We expect validation to check this
        with pytest.raises(ValidationError):
            AssetList(
                character_id=526379435,
                total_items=5,  # Mismatch!
                assets=assets
            )


class TestAssetName:
    """Test AssetName model"""

    def test_create_asset_name(self):
        """Test creating an asset name"""
        asset_name = AssetName(
            item_id=1234567890,
            name="My Awesome Ship"
        )

        assert asset_name.item_id == 1234567890
        assert asset_name.name == "My Awesome Ship"

    def test_asset_name_empty_string(self):
        """Test asset name with empty string"""
        with pytest.raises(ValidationError):
            AssetName(item_id=1234567890, name="")

    def test_asset_name_max_length(self):
        """Test asset name with very long name"""
        long_name = "A" * 255
        asset_name = AssetName(item_id=1234567890, name=long_name)
        assert len(asset_name.name) == 255


class TestSkill:
    """Test Skill model"""

    def test_create_skill(self):
        """Test creating a skill"""
        skill = Skill(
            skill_id=3416,
            skill_name="Shield Management",
            level=5,
            trained_level=5,
            skillpoints=256000
        )

        assert skill.skill_id == 3416
        assert skill.skill_name == "Shield Management"
        assert skill.level == 5
        assert skill.trained_level == 5
        assert skill.skillpoints == 256000

    def test_skill_level_validation(self):
        """Test skill level must be 0-5"""
        with pytest.raises(ValidationError):
            Skill(
                skill_id=3416,
                skill_name="Shield Management",
                level=6,  # Invalid
                trained_level=5,
                skillpoints=256000
            )

    def test_skill_trained_level_validation(self):
        """Test trained level must be 0-5"""
        with pytest.raises(ValidationError):
            Skill(
                skill_id=3416,
                skill_name="Shield Management",
                level=5,
                trained_level=-1,  # Invalid
                skillpoints=256000
            )

    def test_skill_negative_skillpoints(self):
        """Test skillpoints cannot be negative"""
        with pytest.raises(ValidationError):
            Skill(
                skill_id=3416,
                skill_name="Shield Management",
                level=5,
                trained_level=5,
                skillpoints=-1000
            )

    def test_skill_zero_skillpoints(self):
        """Test skill with zero skillpoints"""
        skill = Skill(
            skill_id=3416,
            skill_name="Shield Management",
            level=0,
            trained_level=0,
            skillpoints=0
        )

        assert skill.skillpoints == 0


class TestSkillData:
    """Test SkillData model"""

    def test_create_skill_data(self):
        """Test creating skill data"""
        skills = [
            Skill(skill_id=3416, skill_name="Shield Management", level=5, trained_level=5, skillpoints=256000),
            Skill(skill_id=3426, skill_name="Gunnery", level=5, trained_level=5, skillpoints=256000),
        ]

        skill_data = SkillData(
            character_id=526379435,
            total_sp=5000000,
            unallocated_sp=50000,
            skill_count=2,
            skills=skills
        )

        assert skill_data.character_id == 526379435
        assert skill_data.total_sp == 5000000
        assert skill_data.unallocated_sp == 50000
        assert skill_data.skill_count == 2
        assert len(skill_data.skills) == 2

    def test_skill_data_no_unallocated_sp(self):
        """Test skill data with no unallocated SP"""
        skill_data = SkillData(
            character_id=526379435,
            total_sp=5000000,
            unallocated_sp=0,
            skill_count=0,
            skills=[]
        )

        assert skill_data.unallocated_sp == 0

    def test_skill_data_count_validation(self):
        """Test skill count matches skills length"""
        skills = [
            Skill(skill_id=3416, skill_name="Shield Management", level=5, trained_level=5, skillpoints=256000),
        ]

        with pytest.raises(ValidationError):
            SkillData(
                character_id=526379435,
                total_sp=5000000,
                unallocated_sp=0,
                skill_count=10,  # Mismatch
                skills=skills
            )


class TestSkillQueue:
    """Test SkillQueue model"""

    def test_create_skill_queue_item(self):
        """Test creating a skill queue item"""
        item = SkillQueueItem(
            skill_id=3416,
            finish_date="2025-12-25T10:00:00Z",
            finished_level=5,
            queue_position=0
        )

        assert item.skill_id == 3416
        assert item.finish_date == "2025-12-25T10:00:00Z"
        assert item.finished_level == 5
        assert item.queue_position == 0

    def test_create_skill_queue(self):
        """Test creating a skill queue"""
        items = [
            SkillQueueItem(skill_id=3416, finish_date="2025-12-25T10:00:00Z", finished_level=5, queue_position=0),
            SkillQueueItem(skill_id=3426, finish_date="2025-12-26T10:00:00Z", finished_level=4, queue_position=1),
        ]

        queue = SkillQueue(
            character_id=526379435,
            queue_length=2,
            queue=items
        )

        assert queue.character_id == 526379435
        assert queue.queue_length == 2
        assert len(queue.queue) == 2

    def test_empty_skill_queue(self):
        """Test empty skill queue"""
        queue = SkillQueue(
            character_id=526379435,
            queue_length=0,
            queue=[]
        )

        assert queue.queue_length == 0
        assert len(queue.queue) == 0


class TestMarketOrder:
    """Test MarketOrder model"""

    def test_create_buy_order(self):
        """Test creating a buy order"""
        order = MarketOrder(
            order_id=123456,
            type_id=648,
            location_id=60003760,
            volume_total=100,
            volume_remain=50,
            price=1000000.00,
            is_buy_order=True
        )

        assert order.order_id == 123456
        assert order.type_id == 648
        assert order.is_buy_order is True
        assert order.price == 1000000.00

    def test_create_sell_order(self):
        """Test creating a sell order"""
        order = MarketOrder(
            order_id=123456,
            type_id=648,
            location_id=60003760,
            volume_total=100,
            volume_remain=50,
            price=1000000.00,
            is_buy_order=False
        )

        assert order.is_buy_order is False

    def test_market_order_invalid_price(self):
        """Test market order with invalid price"""
        with pytest.raises(ValidationError):
            MarketOrder(
                order_id=123456,
                type_id=648,
                location_id=60003760,
                volume_total=100,
                volume_remain=50,
                price=-1000.00,  # Invalid
                is_buy_order=True
            )

    def test_market_order_volume_remain_exceeds_total(self):
        """Test volume_remain cannot exceed volume_total"""
        with pytest.raises(ValidationError):
            MarketOrder(
                order_id=123456,
                type_id=648,
                location_id=60003760,
                volume_total=100,
                volume_remain=150,  # Invalid
                price=1000000.00,
                is_buy_order=True
            )


class TestMarketOrderList:
    """Test MarketOrderList model"""

    def test_create_market_order_list(self):
        """Test creating a market order list"""
        orders = [
            MarketOrder(order_id=1, type_id=648, location_id=60003760, volume_total=100, volume_remain=50, price=1000000.00, is_buy_order=True),
            MarketOrder(order_id=2, type_id=649, location_id=60003760, volume_total=200, volume_remain=100, price=2000000.00, is_buy_order=False),
        ]

        order_list = MarketOrderList(
            character_id=526379435,
            total_orders=2,
            buy_orders=1,
            sell_orders=1,
            orders=orders
        )

        assert order_list.total_orders == 2
        assert order_list.buy_orders == 1
        assert order_list.sell_orders == 1
        assert len(order_list.orders) == 2

    def test_market_order_list_counts_validation(self):
        """Test buy_orders + sell_orders equals total_orders"""
        orders = [
            MarketOrder(order_id=1, type_id=648, location_id=60003760, volume_total=100, volume_remain=50, price=1000000.00, is_buy_order=True),
        ]

        with pytest.raises(ValidationError):
            MarketOrderList(
                character_id=526379435,
                total_orders=1,
                buy_orders=1,
                sell_orders=5,  # Mismatch
                orders=orders
            )


class TestIndustryJob:
    """Test IndustryJob model"""

    def test_create_industry_job(self):
        """Test creating an industry job"""
        job = IndustryJob(
            job_id=123456,
            activity_id=1,
            blueprint_type_id=648,
            status="active",
            duration=86400,
            installer_id=526379435
        )

        assert job.job_id == 123456
        assert job.activity_id == 1
        assert job.blueprint_type_id == 648
        assert job.status == "active"
        assert job.duration == 86400
        assert job.installer_id == 526379435

    def test_industry_job_status_validation(self):
        """Test industry job status must be valid"""
        valid_statuses = ["active", "cancelled", "delivered", "paused", "ready", "reverted"]

        for status in valid_statuses:
            job = IndustryJob(
                job_id=123456,
                activity_id=1,
                blueprint_type_id=648,
                status=status,
                duration=86400,
                installer_id=526379435
            )
            assert job.status == status

    def test_industry_job_invalid_status(self):
        """Test industry job with invalid status"""
        with pytest.raises(ValidationError):
            IndustryJob(
                job_id=123456,
                activity_id=1,
                blueprint_type_id=648,
                status="invalid_status",
                duration=86400,
                installer_id=526379435
            )


class TestIndustryJobList:
    """Test IndustryJobList model"""

    def test_create_industry_job_list(self):
        """Test creating an industry job list"""
        jobs = [
            IndustryJob(job_id=1, activity_id=1, blueprint_type_id=648, status="active", duration=86400, installer_id=526379435),
            IndustryJob(job_id=2, activity_id=1, blueprint_type_id=649, status="ready", duration=86400, installer_id=526379435),
        ]

        job_list = IndustryJobList(
            character_id=526379435,
            total_jobs=2,
            active_jobs=1,
            jobs=jobs
        )

        assert job_list.total_jobs == 2
        assert job_list.active_jobs == 1
        assert len(job_list.jobs) == 2

    def test_industry_job_list_active_jobs_validation(self):
        """Test active_jobs cannot exceed total_jobs"""
        jobs = [
            IndustryJob(job_id=1, activity_id=1, blueprint_type_id=648, status="active", duration=86400, installer_id=526379435),
        ]

        with pytest.raises(ValidationError):
            IndustryJobList(
                character_id=526379435,
                total_jobs=1,
                active_jobs=10,  # Invalid
                jobs=jobs
            )


class TestBlueprint:
    """Test Blueprint model"""

    def test_create_blueprint_original(self):
        """Test creating a blueprint original"""
        bp = Blueprint(
            item_id=1234567890,
            type_id=648,
            location_id=60003760,
            quantity=-1,  # -1 = original
            material_efficiency=10,
            time_efficiency=20
        )

        assert bp.item_id == 1234567890
        assert bp.type_id == 648
        assert bp.quantity == -1
        assert bp.material_efficiency == 10
        assert bp.time_efficiency == 20

    def test_create_blueprint_copy(self):
        """Test creating a blueprint copy"""
        bp = Blueprint(
            item_id=1234567890,
            type_id=648,
            location_id=60003760,
            quantity=-2,  # -2 = copy
            material_efficiency=10,
            time_efficiency=20,
            runs=10
        )

        assert bp.quantity == -2
        assert bp.runs == 10

    def test_blueprint_me_validation(self):
        """Test material efficiency must be 0-10"""
        with pytest.raises(ValidationError):
            Blueprint(
                item_id=1234567890,
                type_id=648,
                location_id=60003760,
                quantity=-1,
                material_efficiency=11,  # Invalid
                time_efficiency=20
            )

    def test_blueprint_te_validation(self):
        """Test time efficiency must be 0-20"""
        with pytest.raises(ValidationError):
            Blueprint(
                item_id=1234567890,
                type_id=648,
                location_id=60003760,
                quantity=-1,
                material_efficiency=10,
                time_efficiency=21  # Invalid
            )


class TestBlueprintList:
    """Test BlueprintList model"""

    def test_create_blueprint_list(self):
        """Test creating a blueprint list"""
        blueprints = [
            Blueprint(item_id=1, type_id=648, location_id=60003760, quantity=-1, material_efficiency=10, time_efficiency=20),
            Blueprint(item_id=2, type_id=649, location_id=60003760, quantity=-2, material_efficiency=10, time_efficiency=20, runs=10),
        ]

        bp_list = BlueprintList(
            character_id=526379435,
            total_blueprints=2,
            originals=1,
            copies=1,
            blueprints=blueprints
        )

        assert bp_list.total_blueprints == 2
        assert bp_list.originals == 1
        assert bp_list.copies == 1
        assert len(bp_list.blueprints) == 2

    def test_blueprint_list_counts_validation(self):
        """Test originals + copies equals total_blueprints"""
        blueprints = [
            Blueprint(item_id=1, type_id=648, location_id=60003760, quantity=-1, material_efficiency=10, time_efficiency=20),
        ]

        with pytest.raises(ValidationError):
            BlueprintList(
                character_id=526379435,
                total_blueprints=1,
                originals=1,
                copies=5,  # Mismatch
                blueprints=blueprints
            )


class TestCharacterInfo:
    """Test CharacterInfo model"""

    def test_create_character_info(self):
        """Test creating character info"""
        info = CharacterInfo(
            character_id=526379435,
            name="Artallus",
            corporation_id=98785281,
            birthday="2010-01-01T00:00:00Z"
        )

        assert info.character_id == 526379435
        assert info.name == "Artallus"
        assert info.corporation_id == 98785281
        assert info.birthday == "2010-01-01T00:00:00Z"
        assert info.alliance_id is None

    def test_create_character_info_with_alliance(self):
        """Test creating character info with alliance"""
        info = CharacterInfo(
            character_id=526379435,
            name="Artallus",
            corporation_id=98785281,
            birthday="2010-01-01T00:00:00Z",
            alliance_id=123456
        )

        assert info.alliance_id == 123456


class TestCorporationInfo:
    """Test CorporationInfo model"""

    def test_create_corporation_info(self):
        """Test creating corporation info"""
        info = CorporationInfo(
            corporation_id=98785281,
            name="Minimal Industries",
            ticker="MINDI",
            member_count=10,
            ceo_id=526379435
        )

        assert info.corporation_id == 98785281
        assert info.name == "Minimal Industries"
        assert info.ticker == "MINDI"
        assert info.member_count == 10
        assert info.ceo_id == 526379435
        assert info.alliance_id is None

    def test_create_corporation_info_with_alliance(self):
        """Test creating corporation info with alliance"""
        info = CorporationInfo(
            corporation_id=98785281,
            name="Minimal Industries",
            ticker="MINDI",
            member_count=10,
            ceo_id=526379435,
            alliance_id=123456
        )

        assert info.alliance_id == 123456

    def test_corporation_member_count_validation(self):
        """Test member count must be positive"""
        with pytest.raises(ValidationError):
            CorporationInfo(
                corporation_id=98785281,
                name="Minimal Industries",
                ticker="MINDI",
                member_count=-1,  # Invalid
                ceo_id=526379435
            )


class TestCorporationWallet:
    """Test CorporationWallet model"""

    def test_create_corporation_wallet_division(self):
        """Test creating a corporation wallet division"""
        division = CorporationWalletDivision(
            division=1,
            balance=50000000.00
        )

        assert division.division == 1
        assert division.balance == 50000000.00

    def test_wallet_division_validation(self):
        """Test division must be 1-7"""
        with pytest.raises(ValidationError):
            CorporationWalletDivision(division=0, balance=1000.00)

        with pytest.raises(ValidationError):
            CorporationWalletDivision(division=8, balance=1000.00)

    def test_create_corporation_wallet(self):
        """Test creating a corporation wallet"""
        divisions = [
            CorporationWalletDivision(division=1, balance=50000000.00),
            CorporationWalletDivision(division=2, balance=25000000.00),
        ]

        wallet = CorporationWallet(
            corporation_id=98785281,
            corporation_name="Minimal Industries",
            divisions=divisions,
            total_balance=75000000.00,
            formatted_total="75,000,000.00 ISK"
        )

        assert wallet.corporation_id == 98785281
        assert wallet.corporation_name == "Minimal Industries"
        assert len(wallet.divisions) == 2
        assert wallet.total_balance == 75000000.00
        assert wallet.formatted_total == "75,000,000.00 ISK"

    def test_corporation_wallet_empty_divisions(self):
        """Test corporation wallet with no divisions"""
        wallet = CorporationWallet(
            corporation_id=98785281,
            corporation_name="Minimal Industries",
            divisions=[],
            total_balance=0.00,
            formatted_total="0.00 ISK"
        )

        assert len(wallet.divisions) == 0
        assert wallet.total_balance == 0.00
