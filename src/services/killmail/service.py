"""Killmail Service for downloading and processing EVE killmail archives."""

import json
import os
import tarfile
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import requests

from src.services.killmail.models import ItemLoss, KillmailStats, ShipLoss
from src.services.killmail.repository import KillmailRepository


class KillmailService:
    """Service for downloading and processing EVE killmail data."""

    def __init__(
        self,
        repository: KillmailRepository,
        base_url: str,
        session: requests.Session
    ):
        """
        Initialize KillmailService.

        Args:
            repository: KillmailRepository instance for database operations
            base_url: Base URL for EVE Ref killmail archives
            session: requests.Session for HTTP operations
        """
        self.repository = repository
        self.base_url = base_url
        self.session = session

    def download_daily_archive(self, date: date, output_dir: str) -> Optional[str]:
        """
        Download killmail archive for a specific date.

        Args:
            date: Date to download (YYYY-MM-DD)
            output_dir: Directory to save the archive

        Returns:
            Path to downloaded file or None if failed
        """
        # Format: https://data.everef.net/killmails/2024/killmails-2024-12-06.tar.bz2
        year = date.year
        filename = f"killmails-{date.strftime('%Y-%m-%d')}.tar.bz2"
        url = f"{self.base_url}/{year}/{filename}"

        output_path = os.path.join(output_dir, filename)

        try:
            response = self.session.get(url, stream=True, timeout=300)

            if response.status_code == 200:
                # Stream to file
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                return output_path

            elif response.status_code == 404:
                # Archive not found (may not be available yet)
                return None
            else:
                # Other error
                return None

        except Exception:
            return None

    def extract_and_parse(self, archive_path: str, verbose: bool = False) -> List[Dict]:
        """
        Extract tar.bz2 archive and parse JSON killmails.

        Args:
            archive_path: Path to .tar.bz2 file
            verbose: Print progress

        Returns:
            List of parsed killmail dicts
        """
        killmails = []

        try:
            with tarfile.open(archive_path, 'r:bz2') as tar:
                members = tar.getmembers()

                for member in members:
                    if member.isfile() and member.name.endswith('.json'):
                        try:
                            f = tar.extractfile(member)
                            if f:
                                data = json.load(f)
                                killmails.append(data)
                                f.close()
                        except json.JSONDecodeError:
                            # Skip malformed JSON
                            continue
                        except Exception:
                            # Skip files with other errors
                            continue

        except Exception:
            return []

        return killmails

    def aggregate_ship_losses(
        self,
        killmails: List[Dict],
        target_date: date
    ) -> List[ShipLoss]:
        """
        Aggregate killmails by system/ship type.

        Args:
            killmails: List of parsed killmail JSON objects
            target_date: Date these killmails are for

        Returns:
            List of ShipLoss instances
        """
        # Load system->region mapping
        system_region_map = self.repository.get_system_region_map()

        # Aggregation structure: (system_id, ship_type_id) -> {'count': int, 'value': float}
        ship_losses = defaultdict(lambda: {'count': 0, 'value': 0.0})

        for km in killmails:
            try:
                # Extract victim info
                victim = km.get('victim', {})
                solar_system_id = km.get('solar_system_id')
                ship_type_id = victim.get('ship_type_id')

                if not solar_system_id or not ship_type_id:
                    continue

                # Skip if system not in our map (wormholes, etc.)
                if solar_system_id not in system_region_map:
                    continue

                # Aggregate ship loss
                zkb = km.get('zkb', {})
                total_value = zkb.get('totalValue', 0.0)

                key = (solar_system_id, ship_type_id)
                ship_losses[key]['count'] += 1
                ship_losses[key]['value'] += total_value

            except Exception:
                # Skip problematic killmails
                continue

        # Convert to ShipLoss instances
        result = []
        for (system_id, ship_type_id), data in ship_losses.items():
            region_id = system_region_map.get(system_id)
            if region_id:
                result.append(
                    ShipLoss(
                        system_id=system_id,
                        region_id=region_id,
                        ship_type_id=ship_type_id,
                        loss_count=data['count'],
                        date=target_date,
                        total_value_destroyed=data['value']
                    )
                )

        return result

    def aggregate_item_losses(
        self,
        killmails: List[Dict],
        target_date: date
    ) -> List[ItemLoss]:
        """
        Aggregate killmails by region/item type.

        Args:
            killmails: List of parsed killmail JSON objects
            target_date: Date these killmails are for

        Returns:
            List of ItemLoss instances
        """
        # Load system->region mapping
        system_region_map = self.repository.get_system_region_map()

        # Aggregation structure: (region_id, item_type_id) -> count
        item_losses = defaultdict(int)

        for km in killmails:
            try:
                # Extract victim info
                victim = km.get('victim', {})
                solar_system_id = km.get('solar_system_id')

                if not solar_system_id:
                    continue

                # Skip if system not in our map
                if solar_system_id not in system_region_map:
                    continue

                region_id = system_region_map[solar_system_id]

                # Aggregate item losses (from victim's cargo/modules)
                items = victim.get('items', [])
                for item in items:
                    item_type_id = item.get('item_type_id')
                    quantity_destroyed = item.get('quantity_destroyed', 0)

                    if item_type_id and quantity_destroyed > 0:
                        key = (region_id, item_type_id)
                        item_losses[key] += quantity_destroyed

            except Exception:
                # Skip problematic killmails
                continue

        # Convert to ItemLoss instances
        result = []
        for (region_id, item_type_id), count in item_losses.items():
            result.append(
                ItemLoss(
                    region_id=region_id,
                    item_type_id=item_type_id,
                    loss_count=count,
                    date=target_date
                )
            )

        return result

    def process_daily_killmails(
        self,
        target_date: date,
        temp_dir: str
    ) -> KillmailStats:
        """
        Full pipeline: download, extract, aggregate, save for one date.

        Args:
            target_date: Date to process
            temp_dir: Temporary directory for downloads

        Returns:
            KillmailStats with processing results

        Raises:
            Exception: If download or extraction fails
        """
        # Step 1: Download
        archive_path = self.download_daily_archive(target_date, temp_dir)
        if not archive_path:
            raise Exception("Failed to download archive")

        # Step 2: Extract and parse
        killmails = self.extract_and_parse(archive_path, verbose=False)
        if not killmails:
            raise Exception("No killmails extracted")

        # Step 3: Aggregate
        ship_losses = self.aggregate_ship_losses(killmails, target_date)
        item_losses = self.aggregate_item_losses(killmails, target_date)

        # Step 4: Save to database
        self.repository.store_ship_losses(ship_losses)
        self.repository.store_item_losses(item_losses)

        # Calculate statistics
        total_ships = sum(loss.loss_count for loss in ship_losses)
        total_items = sum(loss.loss_count for loss in item_losses)
        total_isk = sum(loss.total_value_destroyed for loss in ship_losses)

        return KillmailStats(
            total_kills=len(killmails),
            ships_destroyed=total_ships,
            items_lost=total_items,
            isk_destroyed=total_isk,
            date_range=(target_date, target_date)
        )

    def cleanup_old_data(self, retention_days: int) -> int:
        """
        Delete data older than retention period.

        Args:
            retention_days: Number of days to retain

        Returns:
            Number of records deleted
        """
        return self.repository.cleanup_old_data(retention_days)
