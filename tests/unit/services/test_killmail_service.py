"""Tests for Killmail Service."""

import json
import tarfile
import tempfile
from datetime import date
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest
import requests

from src.services.killmail.models import ItemLoss, KillmailStats, ShipLoss
from src.services.killmail.service import KillmailService


@pytest.fixture
def mock_repository():
    """Create a mock KillmailRepository."""
    repo = MagicMock()
    repo.get_system_region_map.return_value = {
        30001234: 10000002,
        30001235: 10000002,
        30001236: 10000043
    }
    return repo


@pytest.fixture
def mock_session():
    """Create a mock requests.Session."""
    return MagicMock(spec=requests.Session)


@pytest.fixture
def service(mock_repository, mock_session):
    """Create a KillmailService with mocks."""
    return KillmailService(
        repository=mock_repository,
        base_url="https://data.everef.net/killmails",
        session=mock_session
    )


@pytest.fixture
def sample_killmail():
    """Create a sample killmail JSON structure."""
    return {
        "killmail_id": 123456,
        "solar_system_id": 30001234,
        "victim": {
            "character_id": 123,
            "ship_type_id": 648,
            "items": [
                {"item_type_id": 456, "quantity_destroyed": 10, "quantity_dropped": 0},
                {"item_type_id": 457, "quantity_destroyed": 5, "quantity_dropped": 3}
            ]
        },
        "zkb": {
            "totalValue": 100000000.0
        }
    }


class TestKillmailServiceDownload:
    """Test Killmail download functionality."""

    def test_download_daily_archive_success(self, service, mock_session):
        """Test successful archive download."""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b'data chunk 1', b'data chunk 2']
        mock_session.get.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            # Execute
            result = service.download_daily_archive(
                date=date(2025, 12, 7),
                output_dir=temp_dir
            )

            # Verify
            assert result is not None
            assert result.endswith('killmails-2025-12-07.tar.bz2')
            mock_session.get.assert_called_once()
            call_args = mock_session.get.call_args
            assert '2025/killmails-2025-12-07.tar.bz2' in call_args[0][0]
            assert call_args[1]['stream'] is True
            assert call_args[1]['timeout'] == 300

    def test_download_daily_archive_not_found(self, service, mock_session):
        """Test download when archive is not found (404)."""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            # Execute
            result = service.download_daily_archive(
                date=date(2025, 12, 7),
                output_dir=temp_dir
            )

            # Verify
            assert result is None

    def test_download_daily_archive_server_error(self, service, mock_session):
        """Test download when server returns error."""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_session.get.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            # Execute
            result = service.download_daily_archive(
                date=date(2025, 12, 7),
                output_dir=temp_dir
            )

            # Verify
            assert result is None

    def test_download_daily_archive_network_error(self, service, mock_session):
        """Test download with network exception."""
        # Setup
        mock_session.get.side_effect = requests.RequestException("Network error")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Execute
            result = service.download_daily_archive(
                date=date(2025, 12, 7),
                output_dir=temp_dir
            )

            # Verify
            assert result is None


class TestKillmailServiceExtraction:
    """Test Killmail extraction and parsing."""

    def test_extract_and_parse_success(self, service, sample_killmail):
        """Test successful extraction and parsing of killmails."""
        # Create a tar.bz2 archive in memory with sample killmail
        with tempfile.NamedTemporaryFile(suffix='.tar.bz2', delete=False) as tmp_file:
            archive_path = tmp_file.name

            # Create tar.bz2 archive
            with tarfile.open(archive_path, 'w:bz2') as tar:
                # Add a JSON file
                json_data = json.dumps(sample_killmail).encode('utf-8')
                tarinfo = tarfile.TarInfo(name='killmail_123456.json')
                tarinfo.size = len(json_data)
                tar.addfile(tarinfo, BytesIO(json_data))

            try:
                # Execute
                result = service.extract_and_parse(archive_path, verbose=False)

                # Verify
                assert len(result) == 1
                assert result[0]['killmail_id'] == 123456
                assert result[0]['solar_system_id'] == 30001234
            finally:
                Path(archive_path).unlink()

    def test_extract_and_parse_malformed_json(self, service):
        """Test extraction with malformed JSON file."""
        with tempfile.NamedTemporaryFile(suffix='.tar.bz2', delete=False) as tmp_file:
            archive_path = tmp_file.name

            # Create tar.bz2 archive with malformed JSON
            with tarfile.open(archive_path, 'w:bz2') as tar:
                json_data = b'{invalid json}'
                tarinfo = tarfile.TarInfo(name='killmail_bad.json')
                tarinfo.size = len(json_data)
                tar.addfile(tarinfo, BytesIO(json_data))

            try:
                # Execute
                result = service.extract_and_parse(archive_path, verbose=False)

                # Verify - should skip malformed JSON
                assert len(result) == 0
            finally:
                Path(archive_path).unlink()

    def test_extract_and_parse_empty_archive(self, service):
        """Test extraction with empty archive."""
        with tempfile.NamedTemporaryFile(suffix='.tar.bz2', delete=False) as tmp_file:
            archive_path = tmp_file.name

            # Create empty tar.bz2 archive
            with tarfile.open(archive_path, 'w:bz2') as tar:
                pass

            try:
                # Execute
                result = service.extract_and_parse(archive_path, verbose=False)

                # Verify
                assert len(result) == 0
            finally:
                Path(archive_path).unlink()

    def test_extract_and_parse_invalid_archive(self, service):
        """Test extraction with invalid archive file."""
        with tempfile.NamedTemporaryFile(suffix='.tar.bz2', delete=False) as tmp_file:
            archive_path = tmp_file.name
            tmp_file.write(b'not a tar archive')

        try:
            # Execute
            result = service.extract_and_parse(archive_path, verbose=False)

            # Verify
            assert len(result) == 0
        finally:
            Path(archive_path).unlink()


class TestKillmailServiceAggregation:
    """Test Killmail aggregation functionality."""

    def test_aggregate_ship_losses(self, service, mock_repository, sample_killmail):
        """Test ship loss aggregation."""
        killmails = [sample_killmail]
        target_date = date(2025, 12, 7)

        # Execute
        result = service.aggregate_ship_losses(killmails, target_date)

        # Verify
        assert len(result) == 1
        loss = result[0]
        assert loss.system_id == 30001234
        assert loss.region_id == 10000002
        assert loss.ship_type_id == 648
        assert loss.loss_count == 1
        assert loss.date == target_date
        assert loss.total_value_destroyed == 100000000.0

    def test_aggregate_ship_losses_multiple_same_ship(self, service, mock_repository):
        """Test aggregating multiple losses of same ship type in same system."""
        killmails = [
            {
                "solar_system_id": 30001234,
                "victim": {"ship_type_id": 648},
                "zkb": {"totalValue": 100000000.0}
            },
            {
                "solar_system_id": 30001234,
                "victim": {"ship_type_id": 648},
                "zkb": {"totalValue": 150000000.0}
            }
        ]
        target_date = date(2025, 12, 7)

        # Execute
        result = service.aggregate_ship_losses(killmails, target_date)

        # Verify
        assert len(result) == 1
        loss = result[0]
        assert loss.loss_count == 2
        assert loss.total_value_destroyed == 250000000.0

    def test_aggregate_ship_losses_skip_unknown_system(self, service, mock_repository):
        """Test that unknown systems are skipped."""
        killmails = [
            {
                "solar_system_id": 99999999,  # Unknown system
                "victim": {"ship_type_id": 648},
                "zkb": {"totalValue": 100000000.0}
            }
        ]
        target_date = date(2025, 12, 7)

        # Execute
        result = service.aggregate_ship_losses(killmails, target_date)

        # Verify - should be skipped
        assert len(result) == 0

    def test_aggregate_ship_losses_skip_missing_data(self, service, mock_repository):
        """Test that killmails with missing data are skipped."""
        killmails = [
            {"solar_system_id": 30001234},  # No victim
            {"victim": {"ship_type_id": 648}},  # No system
            {}  # Empty
        ]
        target_date = date(2025, 12, 7)

        # Execute
        result = service.aggregate_ship_losses(killmails, target_date)

        # Verify - all should be skipped
        assert len(result) == 0

    def test_aggregate_item_losses(self, service, mock_repository, sample_killmail):
        """Test item loss aggregation."""
        killmails = [sample_killmail]
        target_date = date(2025, 12, 7)

        # Execute
        result = service.aggregate_item_losses(killmails, target_date)

        # Verify
        assert len(result) == 2
        # Sort by item_type_id for consistent testing
        result.sort(key=lambda x: x.item_type_id)

        assert result[0].region_id == 10000002
        assert result[0].item_type_id == 456
        assert result[0].loss_count == 10
        assert result[0].date == target_date

        assert result[1].item_type_id == 457
        assert result[1].loss_count == 5

    def test_aggregate_item_losses_multiple_killmails(self, service, mock_repository):
        """Test aggregating items from multiple killmails."""
        killmails = [
            {
                "solar_system_id": 30001234,
                "victim": {
                    "ship_type_id": 648,
                    "items": [
                        {"item_type_id": 456, "quantity_destroyed": 10}
                    ]
                }
            },
            {
                "solar_system_id": 30001234,
                "victim": {
                    "ship_type_id": 649,
                    "items": [
                        {"item_type_id": 456, "quantity_destroyed": 5}
                    ]
                }
            }
        ]
        target_date = date(2025, 12, 7)

        # Execute
        result = service.aggregate_item_losses(killmails, target_date)

        # Verify - should combine same item type
        assert len(result) == 1
        assert result[0].item_type_id == 456
        assert result[0].loss_count == 15

    def test_aggregate_item_losses_skip_zero_destroyed(self, service, mock_repository):
        """Test that items with zero destroyed are skipped."""
        killmails = [
            {
                "solar_system_id": 30001234,
                "victim": {
                    "ship_type_id": 648,
                    "items": [
                        {"item_type_id": 456, "quantity_destroyed": 0},
                        {"item_type_id": 457, "quantity_destroyed": 10}
                    ]
                }
            }
        ]
        target_date = date(2025, 12, 7)

        # Execute
        result = service.aggregate_item_losses(killmails, target_date)

        # Verify - only item with destroyed > 0
        assert len(result) == 1
        assert result[0].item_type_id == 457


class TestKillmailServiceProcessing:
    """Test full killmail processing pipeline."""

    @patch.object(KillmailService, 'download_daily_archive')
    @patch.object(KillmailService, 'extract_and_parse')
    @patch.object(KillmailService, 'aggregate_ship_losses')
    @patch.object(KillmailService, 'aggregate_item_losses')
    def test_process_daily_killmails_success(
        self,
        mock_aggregate_items,
        mock_aggregate_ships,
        mock_extract,
        mock_download,
        service,
        mock_repository
    ):
        """Test successful daily killmail processing."""
        # Setup
        target_date = date(2025, 12, 7)
        temp_dir = "/tmp/test"

        mock_download.return_value = "/tmp/test/archive.tar.bz2"
        mock_extract.return_value = [{"killmail_id": 1}, {"killmail_id": 2}]

        ship_losses = [
            ShipLoss(
                system_id=30001234,
                region_id=10000002,
                ship_type_id=648,
                loss_count=2,
                date=target_date
            )
        ]
        item_losses = [
            ItemLoss(
                region_id=10000002,
                item_type_id=456,
                loss_count=10,
                date=target_date
            )
        ]

        mock_aggregate_ships.return_value = ship_losses
        mock_aggregate_items.return_value = item_losses
        mock_repository.store_ship_losses.return_value = 1
        mock_repository.store_item_losses.return_value = 1

        # Execute
        result = service.process_daily_killmails(target_date, temp_dir)

        # Verify
        assert isinstance(result, KillmailStats)
        assert result.total_kills == 2
        assert result.ships_destroyed == 2
        assert result.items_lost == 10

        mock_download.assert_called_once_with(target_date, temp_dir)
        mock_extract.assert_called_once()
        mock_aggregate_ships.assert_called_once()
        mock_aggregate_items.assert_called_once()
        mock_repository.store_ship_losses.assert_called_once_with(ship_losses)
        mock_repository.store_item_losses.assert_called_once_with(item_losses)

    @patch.object(KillmailService, 'download_daily_archive')
    def test_process_daily_killmails_download_failed(
        self,
        mock_download,
        service,
        mock_repository
    ):
        """Test processing when download fails."""
        # Setup
        target_date = date(2025, 12, 7)
        temp_dir = "/tmp/test"
        mock_download.return_value = None

        # Execute & Verify
        with pytest.raises(Exception, match="Failed to download archive"):
            service.process_daily_killmails(target_date, temp_dir)

    @patch.object(KillmailService, 'download_daily_archive')
    @patch.object(KillmailService, 'extract_and_parse')
    def test_process_daily_killmails_no_killmails(
        self,
        mock_extract,
        mock_download,
        service,
        mock_repository
    ):
        """Test processing when no killmails are extracted."""
        # Setup
        target_date = date(2025, 12, 7)
        temp_dir = "/tmp/test"

        mock_download.return_value = "/tmp/test/archive.tar.bz2"
        mock_extract.return_value = []

        # Execute & Verify
        with pytest.raises(Exception, match="No killmails extracted"):
            service.process_daily_killmails(target_date, temp_dir)

    def test_cleanup_old_data(self, service, mock_repository):
        """Test cleanup of old data."""
        # Setup
        mock_repository.cleanup_old_data.return_value = 100

        # Execute
        result = service.cleanup_old_data(retention_days=30)

        # Verify
        assert result == 100
        mock_repository.cleanup_old_data.assert_called_once_with(30)
