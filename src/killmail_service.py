"""
EVE Co-Pilot Killmail Service
Downloads and processes daily killmail archives from EVE Ref
Aggregates combat data for War Room analytics
"""

import os
import requests
import tarfile
import json
import tempfile
import shutil
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from psycopg2.extras import execute_values

from src.database import get_db_connection
from config import WAR_EVEREF_BASE_URL, WAR_DATA_RETENTION_DAYS


class KillmailService:
    """Service for downloading and processing EVE killmail data"""

    def __init__(self):
        self.base_url = WAR_EVEREF_BASE_URL
        self.retention_days = WAR_DATA_RETENTION_DAYS
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "EVE-CoPilot/1.0",
            "Accept": "application/json"
        })

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
            print(f"Downloading {filename}...")
            response = self.session.get(url, stream=True, timeout=300)

            if response.status_code == 200:
                # Stream to file
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                file_size = os.path.getsize(output_path)
                print(f"  Downloaded {file_size / 1024 / 1024:.1f} MB")
                return output_path

            elif response.status_code == 404:
                print(f"  Archive not found (may not be available yet)")
                return None
            else:
                print(f"  Failed with status {response.status_code}")
                return None

        except Exception as e:
            print(f"  Error downloading: {e}")
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

                if verbose:
                    print(f"Extracting {len(members)} killmails...")

                for i, member in enumerate(members):
                    if member.isfile() and member.name.endswith('.json'):
                        try:
                            f = tar.extractfile(member)
                            if f:
                                data = json.load(f)
                                killmails.append(data)
                                f.close()
                        except json.JSONDecodeError:
                            if verbose:
                                print(f"  Warning: Could not parse {member.name}")
                        except Exception as e:
                            if verbose:
                                print(f"  Warning: Error reading {member.name}: {e}")

                    if verbose and (i + 1) % 10000 == 0:
                        print(f"  Processed {i + 1}/{len(members)} files...", end='\r')

                if verbose:
                    print(f"\n  Parsed {len(killmails)} killmails")

        except Exception as e:
            print(f"  Error extracting archive: {e}")
            return []

        return killmails

    def _get_system_region_map(self) -> Dict[int, int]:
        """Load solar_system_id -> region_id mapping from DB"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT solar_system_id, region_id FROM system_region_map")
                return {row[0]: row[1] for row in cur.fetchall()}

    def aggregate_killmails(self, killmails: List[Dict], date: date, verbose: bool = False) -> Dict:
        """
        Aggregate killmails by system/ship/item.

        Args:
            killmails: List of parsed killmail JSON objects
            date: Date these killmails are for
            verbose: Print progress

        Returns:
            Dict with 'ship_losses' and 'item_losses' aggregated data
        """
        if verbose:
            print(f"Aggregating {len(killmails)} killmails...")

        # Load system->region mapping
        system_region_map = self._get_system_region_map()

        # Aggregation structures
        # Key: (solar_system_id, ship_type_id) -> {'quantity': int, 'total_value': float}
        ship_losses = defaultdict(lambda: {'quantity': 0, 'total_value': 0.0})

        # Key: (solar_system_id, item_type_id) -> {'quantity': int}
        item_losses = defaultdict(lambda: {'quantity': 0})

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
                ship_losses[key]['quantity'] += 1
                ship_losses[key]['total_value'] += total_value

                # Aggregate item losses (from victim's cargo/modules)
                items = victim.get('items', [])
                for item in items:
                    item_type_id = item.get('item_type_id')
                    quantity_destroyed = item.get('quantity_destroyed', 0)

                    if item_type_id and quantity_destroyed > 0:
                        item_key = (solar_system_id, item_type_id)
                        item_losses[item_key]['quantity'] += quantity_destroyed

            except Exception as e:
                if verbose:
                    print(f"  Warning: Error processing killmail: {e}")

        # Convert to list format with region_id
        ship_data = []
        for (system_id, ship_id), data in ship_losses.items():
            region_id = system_region_map.get(system_id)
            if region_id:
                ship_data.append({
                    'date': date,
                    'region_id': region_id,
                    'solar_system_id': system_id,
                    'ship_type_id': ship_id,
                    'quantity': data['quantity'],
                    'total_value_destroyed': data['total_value']
                })

        item_data = []
        for (system_id, item_id), data in item_losses.items():
            region_id = system_region_map.get(system_id)
            if region_id:
                item_data.append({
                    'date': date,
                    'region_id': region_id,
                    'solar_system_id': system_id,
                    'item_type_id': item_id,
                    'quantity_destroyed': data['quantity']
                })

        if verbose:
            print(f"  Ship losses: {len(ship_data)} unique entries")
            print(f"  Item losses: {len(item_data)} unique entries")

        return {
            'ship_losses': ship_data,
            'item_losses': item_data
        }

    def save_to_database(self, date: date, aggregated: Dict, verbose: bool = False) -> Dict:
        """
        Save aggregated data to database.

        Args:
            date: Date of the data
            aggregated: Dict with 'ship_losses' and 'item_losses'
            verbose: Print progress

        Returns:
            Dict with save statistics
        """
        ship_data = aggregated['ship_losses']
        item_data = aggregated['item_losses']

        if verbose:
            print(f"Saving to database...")

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Save ship losses
                if ship_data:
                    ship_values = [
                        (
                            d['date'],
                            d['region_id'],
                            d['solar_system_id'],
                            d['ship_type_id'],
                            d['quantity'],
                            d['total_value_destroyed']
                        )
                        for d in ship_data
                    ]

                    execute_values(
                        cur,
                        """
                        INSERT INTO combat_ship_losses
                            (date, region_id, solar_system_id, ship_type_id, quantity, total_value_destroyed)
                        VALUES %s
                        ON CONFLICT (date, solar_system_id, ship_type_id)
                        DO UPDATE SET
                            quantity = combat_ship_losses.quantity + EXCLUDED.quantity,
                            total_value_destroyed = combat_ship_losses.total_value_destroyed + EXCLUDED.total_value_destroyed
                        """,
                        ship_values,
                        page_size=1000
                    )

                # Save item losses
                if item_data:
                    item_values = [
                        (
                            d['date'],
                            d['region_id'],
                            d['solar_system_id'],
                            d['item_type_id'],
                            d['quantity_destroyed']
                        )
                        for d in item_data
                    ]

                    execute_values(
                        cur,
                        """
                        INSERT INTO combat_item_losses
                            (date, region_id, solar_system_id, item_type_id, quantity_destroyed)
                        VALUES %s
                        ON CONFLICT (date, solar_system_id, item_type_id)
                        DO UPDATE SET
                            quantity_destroyed = combat_item_losses.quantity_destroyed + EXCLUDED.quantity_destroyed
                        """,
                        item_values,
                        page_size=1000
                    )

                conn.commit()

        if verbose:
            print(f"  Saved {len(ship_data)} ship loss entries")
            print(f"  Saved {len(item_data)} item loss entries")

        return {
            'ship_losses_saved': len(ship_data),
            'item_losses_saved': len(item_data)
        }

    def process_date(self, date: date, verbose: bool = False) -> Dict:
        """
        Full pipeline: download, extract, aggregate, save for one date.

        Args:
            date: Date to process
            verbose: Print detailed progress

        Returns:
            Dict with processing results
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"Processing date: {date.strftime('%Y-%m-%d')}")
            print(f"{'='*60}")

        # Create temp directory
        temp_dir = tempfile.mkdtemp()

        try:
            # Step 1: Download
            archive_path = self.download_daily_archive(date, temp_dir)
            if not archive_path:
                return {
                    'success': False,
                    'date': str(date),
                    'error': 'Download failed'
                }

            # Step 2: Extract and parse
            killmails = self.extract_and_parse(archive_path, verbose)
            if not killmails:
                return {
                    'success': False,
                    'date': str(date),
                    'error': 'No killmails extracted'
                }

            # Step 3: Aggregate
            aggregated = self.aggregate_killmails(killmails, date, verbose)

            # Step 4: Save
            save_stats = self.save_to_database(date, aggregated, verbose)

            if verbose:
                print(f"\n{'='*60}")
                print(f"Completed: {date.strftime('%Y-%m-%d')}")
                print(f"{'='*60}")

            return {
                'success': True,
                'date': str(date),
                'killmails_processed': len(killmails),
                **save_stats
            }

        finally:
            # Cleanup temp directory
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    def backfill(self, start_date: date, end_date: date, verbose: bool = False) -> List[Dict]:
        """
        Process a date range (inclusive).

        Args:
            start_date: First date to process
            end_date: Last date to process
            verbose: Print progress

        Returns:
            List of processing results per date
        """
        results = []
        current_date = start_date

        while current_date <= end_date:
            # Check if we already have data
            if self.has_data_for(current_date):
                if verbose:
                    print(f"\nSkipping {current_date} (already have data)")
                current_date += timedelta(days=1)
                continue

            result = self.process_date(current_date, verbose)
            results.append(result)

            current_date += timedelta(days=1)

        return results

    def has_data_for(self, date: date) -> bool:
        """Check if we already have data for a specific date"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM combat_ship_losses WHERE date = %s",
                    (date,)
                )
                count = cur.fetchone()[0]
                return count > 0

    def cleanup_old_data(self, verbose: bool = False) -> Dict:
        """
        Remove data older than retention period.

        Returns:
            Dict with cleanup statistics
        """
        cutoff_date = datetime.now().date() - timedelta(days=self.retention_days)

        if verbose:
            print(f"Cleaning up data older than {cutoff_date}...")

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Delete old ship losses
                cur.execute(
                    "DELETE FROM combat_ship_losses WHERE date < %s",
                    (cutoff_date,)
                )
                ship_deleted = cur.rowcount

                # Delete old item losses
                cur.execute(
                    "DELETE FROM combat_item_losses WHERE date < %s",
                    (cutoff_date,)
                )
                item_deleted = cur.rowcount

                conn.commit()

        if verbose:
            print(f"  Deleted {ship_deleted} ship loss records")
            print(f"  Deleted {item_deleted} item loss records")

        return {
            'ship_losses_deleted': ship_deleted,
            'item_losses_deleted': item_deleted,
            'cutoff_date': str(cutoff_date)
        }

    def get_ship_losses(
        self,
        region_id: Optional[int] = None,
        days: int = 7,
        verbose: bool = False
    ) -> List[Dict]:
        """
        Query ship losses for a region over N days.

        Args:
            region_id: Region to query (None = all regions)
            days: Number of days to look back
            verbose: Print query info

        Returns:
            List of aggregated ship loss records
        """
        cutoff_date = datetime.now().date() - timedelta(days=days)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if region_id:
                    cur.execute("""
                        SELECT
                            date,
                            region_id,
                            solar_system_id,
                            ship_type_id,
                            SUM(quantity) as total_quantity,
                            SUM(total_value_destroyed) as total_value
                        FROM combat_ship_losses
                        WHERE date >= %s AND region_id = %s
                        GROUP BY date, region_id, solar_system_id, ship_type_id
                        ORDER BY date DESC, total_quantity DESC
                    """, (cutoff_date, region_id))
                else:
                    cur.execute("""
                        SELECT
                            date,
                            region_id,
                            solar_system_id,
                            ship_type_id,
                            SUM(quantity) as total_quantity,
                            SUM(total_value_destroyed) as total_value
                        FROM combat_ship_losses
                        WHERE date >= %s
                        GROUP BY date, region_id, solar_system_id, ship_type_id
                        ORDER BY date DESC, total_quantity DESC
                    """, (cutoff_date,))

                results = []
                for row in cur.fetchall():
                    results.append({
                        'date': str(row[0]),
                        'region_id': row[1],
                        'solar_system_id': row[2],
                        'ship_type_id': row[3],
                        'quantity': row[4],
                        'total_value': float(row[5])
                    })

                if verbose:
                    print(f"Found {len(results)} ship loss records")

                return results

    def get_item_losses(
        self,
        region_id: Optional[int] = None,
        days: int = 7,
        verbose: bool = False
    ) -> List[Dict]:
        """
        Query item losses for a region over N days.

        Args:
            region_id: Region to query (None = all regions)
            days: Number of days to look back
            verbose: Print query info

        Returns:
            List of aggregated item loss records
        """
        cutoff_date = datetime.now().date() - timedelta(days=days)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if region_id:
                    cur.execute("""
                        SELECT
                            date,
                            region_id,
                            solar_system_id,
                            item_type_id,
                            SUM(quantity_destroyed) as total_destroyed
                        FROM combat_item_losses
                        WHERE date >= %s AND region_id = %s
                        GROUP BY date, region_id, solar_system_id, item_type_id
                        ORDER BY date DESC, total_destroyed DESC
                    """, (cutoff_date, region_id))
                else:
                    cur.execute("""
                        SELECT
                            date,
                            region_id,
                            solar_system_id,
                            item_type_id,
                            SUM(quantity_destroyed) as total_destroyed
                        FROM combat_item_losses
                        WHERE date >= %s
                        GROUP BY date, region_id, solar_system_id, item_type_id
                        ORDER BY date DESC, total_destroyed DESC
                    """, (cutoff_date,))

                results = []
                for row in cur.fetchall():
                    results.append({
                        'date': str(row[0]),
                        'region_id': row[1],
                        'solar_system_id': row[2],
                        'item_type_id': row[3],
                        'quantity_destroyed': row[4]
                    })

                if verbose:
                    print(f"Found {len(results)} item loss records")

                return results


# Singleton instance
killmail_service = KillmailService()
