# War Room Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a "War Profiteering" module that analyzes EVE combat data to identify production and trading opportunities.

**Architecture:** Three data sources (EVE Ref killmails, ESI Sovereignty, ESI Faction Warfare) feed into analysis services that detect demand patterns. Results exposed via REST API and visualized in React frontend. Route safety integrates with existing shopping module.

**Tech Stack:** Python/FastAPI backend, PostgreSQL database, React/TypeScript frontend, Cron jobs for data collection.

---

## Work Packages for Parallel Execution

This plan is structured into **independent work packages** that can be executed by parallel agents. Dependencies are clearly marked.

### Dependency Graph
```
[WP1: Database] ──────────────────────────────────────────┐
      │                                                    │
      ├──► [WP2: Killmail Service] ──► [WP5: War Analyzer]│
      │                                       │            │
      ├──► [WP3: Sovereignty Service] ────────┤            │
      │                                       │            │
      ├──► [WP4: FW Service] ─────────────────┘            │
      │                                                    │
      └──► [WP6: API Router] ◄─────────────────────────────┘
                  │
                  ├──► [WP7: Route Safety Integration]
                  │
                  └──► [WP8: Frontend War Room]
                              │
                              └──► [WP9: Frontend Integration]
```

**Parallel Execution Strategy:**
- **Batch 1:** WP1 (Database) - Must complete first
- **Batch 2:** WP2, WP3, WP4 in parallel (all depend only on WP1)
- **Batch 3:** WP5, WP6 in parallel (depend on WP2-4)
- **Batch 4:** WP7, WP8 in parallel (depend on WP6)
- **Batch 5:** WP9 (depends on WP7, WP8)

---

## WP1: Database Schema & Infrastructure

**Depends on:** Nothing
**Enables:** WP2, WP3, WP4, WP5, WP6

### Task 1.1: Create Migration File

**Files:**
- Create: `migrations/003_war_room.sql`

**Step 1: Write migration SQL**

```sql
-- migrations/003_war_room.sql
-- War Room feature: combat analysis and conflict tracking

-- System-to-region mapping cache (for fast lookups)
CREATE TABLE IF NOT EXISTS system_region_map (
    solar_system_id INTEGER PRIMARY KEY,
    solar_system_name VARCHAR(100),
    region_id INTEGER NOT NULL,
    region_name VARCHAR(100),
    constellation_id INTEGER,
    security_status FLOAT
);

CREATE INDEX IF NOT EXISTS idx_srm_region ON system_region_map(region_id);

-- Daily ship losses aggregated by system
CREATE TABLE IF NOT EXISTS combat_ship_losses (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    region_id INTEGER NOT NULL,
    solar_system_id INTEGER NOT NULL,
    ship_type_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    total_value_destroyed NUMERIC(20,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, solar_system_id, ship_type_id)
);

CREATE INDEX IF NOT EXISTS idx_csl_date_region ON combat_ship_losses(date, region_id);
CREATE INDEX IF NOT EXISTS idx_csl_ship ON combat_ship_losses(ship_type_id);
CREATE INDEX IF NOT EXISTS idx_csl_system ON combat_ship_losses(solar_system_id);

-- Daily item/module losses aggregated by system
CREATE TABLE IF NOT EXISTS combat_item_losses (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    region_id INTEGER NOT NULL,
    solar_system_id INTEGER NOT NULL,
    item_type_id INTEGER NOT NULL,
    quantity_destroyed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, solar_system_id, item_type_id)
);

CREATE INDEX IF NOT EXISTS idx_cil_date_region ON combat_item_losses(date, region_id);
CREATE INDEX IF NOT EXISTS idx_cil_item ON combat_item_losses(item_type_id);

-- Alliance conflict tracking (who fights whom)
CREATE TABLE IF NOT EXISTS alliance_conflicts (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    alliance_a INTEGER NOT NULL,
    alliance_b INTEGER NOT NULL,
    kill_count INTEGER NOT NULL DEFAULT 0,
    region_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, alliance_a, alliance_b)
);

CREATE INDEX IF NOT EXISTS idx_ac_date ON alliance_conflicts(date);
CREATE INDEX IF NOT EXISTS idx_ac_alliances ON alliance_conflicts(alliance_a, alliance_b);

-- Sovereignty campaign snapshots
CREATE TABLE IF NOT EXISTS sovereignty_campaigns (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER UNIQUE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    solar_system_id INTEGER NOT NULL,
    constellation_id INTEGER,
    defender_id INTEGER,
    defender_name VARCHAR(100),
    attacker_score FLOAT,
    defender_score FLOAT,
    start_time TIMESTAMP NOT NULL,
    structure_id BIGINT,
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sc_start ON sovereignty_campaigns(start_time);
CREATE INDEX IF NOT EXISTS idx_sc_system ON sovereignty_campaigns(solar_system_id);

-- Faction Warfare system status
CREATE TABLE IF NOT EXISTS fw_system_status (
    id SERIAL PRIMARY KEY,
    solar_system_id INTEGER NOT NULL,
    owner_faction_id INTEGER NOT NULL,
    occupier_faction_id INTEGER NOT NULL,
    contested VARCHAR(20) NOT NULL,
    victory_points INTEGER NOT NULL,
    victory_points_threshold INTEGER NOT NULL,
    contested_percent FLOAT GENERATED ALWAYS AS (
        CASE WHEN victory_points_threshold > 0
             THEN (victory_points::FLOAT / victory_points_threshold * 100)
             ELSE 0 END
    ) STORED,
    snapshot_time TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fws_system ON fw_system_status(solar_system_id);
CREATE INDEX IF NOT EXISTS idx_fws_time ON fw_system_status(snapshot_time DESC);
CREATE INDEX IF NOT EXISTS idx_fws_contested ON fw_system_status(contested_percent DESC);
```

**Step 2: Run migration**

Run:
```bash
cat migrations/003_war_room.sql | sudo -S docker exec -i eve_db psql -U eve -d eve_sde
```

Password when prompted: `Aug2012#`

Expected: Tables created without errors.

**Step 3: Commit**

```bash
git add migrations/003_war_room.sql
git commit -m "feat(war-room): add database schema for combat analysis"
```

---

### Task 1.2: Populate System-Region Map

**Files:**
- Create: `scripts/populate_system_region_map.py`

**Step 1: Write population script**

```python
#!/usr/bin/env python3
"""Populate system_region_map from SDE data"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_connection

def populate_system_region_map():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Clear existing data
            cur.execute("TRUNCATE system_region_map")

            # Insert from SDE
            cur.execute('''
                INSERT INTO system_region_map
                    (solar_system_id, solar_system_name, region_id, region_name,
                     constellation_id, security_status)
                SELECT
                    s."solarSystemID",
                    s."solarSystemName",
                    s."regionID",
                    r."regionName",
                    s."constellationID",
                    s."security"
                FROM "mapSolarSystems" s
                JOIN "mapRegions" r ON s."regionID" = r."regionID"
            ''')

            count = cur.rowcount
            conn.commit()
            print(f"Inserted {count} systems into system_region_map")
            return count

if __name__ == "__main__":
    populate_system_region_map()
```

**Step 2: Run script**

Run: `python3 scripts/populate_system_region_map.py`

Expected: "Inserted 8436 systems into system_region_map" (approximately)

**Step 3: Verify**

Run:
```bash
echo 'Aug2012#' | sudo -S docker exec eve_db psql -U eve -d eve_sde -c "SELECT COUNT(*) FROM system_region_map"
```

Expected: Count > 8000

**Step 4: Commit**

```bash
git add scripts/populate_system_region_map.py
git commit -m "feat(war-room): add system-region map population script"
```

---

### Task 1.3: Add Config Settings

**Files:**
- Modify: `config.py` (append to end)

**Step 1: Add War Room config**

Append to `config.py`:

```python
# War Room Configuration
WAR_DATA_RETENTION_DAYS = 30
WAR_DOCTRINE_MIN_FLEET_SIZE = 10
WAR_HEATMAP_MIN_KILLS = 5
WAR_EVEREF_BASE_URL = "https://data.everef.net/killmails"

# Discord War Alerts (customizable thresholds)
WAR_DISCORD_ENABLED = True
WAR_ALERT_DEMAND_SCORE_THRESHOLD = 2.0  # losses/market_volume ratio
WAR_ALERT_MIN_GAP_UNITS = 50  # Minimum units short to trigger alert
```

**Step 2: Commit**

```bash
git add config.py
git commit -m "feat(war-room): add configuration settings"
```

---

## WP2: Killmail Service

**Depends on:** WP1
**Enables:** WP5, WP6

### Task 2.1: Create Killmail Service

**Files:**
- Create: `killmail_service.py`

**Step 1: Write the service**

```python
#!/usr/bin/env python3
"""
Killmail Service - Download and process EVE Ref killmail bulk data
"""

import os
import json
import tarfile
import tempfile
import requests
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set
from collections import Counter, defaultdict

from database import get_db_connection
from config import WAR_EVEREF_BASE_URL, WAR_DATA_RETENTION_DAYS


class KillmailService:
    """Fetches and processes EVE Ref killmail bulk data"""

    def __init__(self):
        self._system_region_cache: Optional[Dict[int, int]] = None

    def _load_system_region_cache(self):
        """Load system->region mapping from database"""
        if self._system_region_cache is not None:
            return

        self._system_region_cache = {}
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT solar_system_id, region_id FROM system_region_map")
                for row in cur.fetchall():
                    self._system_region_cache[row[0]] = row[1]

    def get_region_for_system(self, solar_system_id: int) -> Optional[int]:
        """Get region ID for a solar system"""
        self._load_system_region_cache()
        return self._system_region_cache.get(solar_system_id)

    def download_daily_archive(self, target_date: date, output_dir: Path) -> Optional[Path]:
        """
        Download killmails-YYYY-MM-DD.tar.bz2 from EVE Ref
        Returns path to downloaded file or None if not available
        """
        filename = f"killmails-{target_date.isoformat()}.tar.bz2"
        url = f"{WAR_EVEREF_BASE_URL}/{target_date.year}/{filename}"
        output_path = output_dir / filename

        try:
            response = requests.get(url, stream=True, timeout=120)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return output_path
            elif response.status_code == 404:
                print(f"  No data available for {target_date}")
                return None
            else:
                print(f"  Error downloading {filename}: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"  Download error: {e}")
            return None

    def extract_and_parse(self, archive_path: Path) -> List[dict]:
        """Extract tar.bz2 and parse all JSON killmails"""
        killmails = []

        with tarfile.open(archive_path, 'r:bz2') as tar:
            for member in tar.getmembers():
                if member.name.endswith('.json'):
                    f = tar.extractfile(member)
                    if f:
                        try:
                            km = json.loads(f.read().decode('utf-8'))
                            killmails.append(km)
                        except json.JSONDecodeError:
                            continue

        return killmails

    def aggregate_killmails(self, killmails: List[dict], target_date: date) -> dict:
        """
        Aggregate killmails into:
        - ship_losses: {(system_id, ship_type_id): {'qty': N, 'value': V}}
        - item_losses: {(system_id, item_type_id): qty}
        - alliance_conflicts: {(alliance_a, alliance_b): count}
        """
        ship_losses = defaultdict(lambda: {'qty': 0, 'value': 0})
        item_losses = defaultdict(int)
        alliance_conflicts = defaultdict(int)

        for km in killmails:
            system_id = km.get('solar_system_id')
            if not system_id:
                continue

            victim = km.get('victim', {})
            ship_type_id = victim.get('ship_type_id')

            if ship_type_id:
                key = (system_id, ship_type_id)
                ship_losses[key]['qty'] += 1
                # Value from zkb metadata if available, otherwise estimate
                ship_losses[key]['value'] += 0  # Will be enriched later

            # Item losses
            for item in victim.get('items', []):
                if 'quantity_destroyed' in item:
                    item_key = (system_id, item['item_type_id'])
                    item_losses[item_key] += item['quantity_destroyed']

            # Alliance conflicts
            victim_alliance = victim.get('alliance_id') or victim.get('corporation_id')
            if victim_alliance:
                for attacker in km.get('attackers', []):
                    attacker_alliance = attacker.get('alliance_id') or attacker.get('corporation_id')
                    if attacker_alliance and attacker_alliance != victim_alliance:
                        # Normalize: smaller ID first
                        pair = tuple(sorted([attacker_alliance, victim_alliance]))
                        alliance_conflicts[pair] += 1

        return {
            'ship_losses': dict(ship_losses),
            'item_losses': dict(item_losses),
            'alliance_conflicts': dict(alliance_conflicts)
        }

    def save_to_database(self, target_date: date, aggregated: dict) -> dict:
        """Insert aggregated data into database tables"""
        stats = {'ships': 0, 'items': 0, 'conflicts': 0}

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Ship losses
                for (system_id, ship_type_id), data in aggregated['ship_losses'].items():
                    region_id = self.get_region_for_system(system_id)
                    if not region_id:
                        continue

                    cur.execute('''
                        INSERT INTO combat_ship_losses
                            (date, region_id, solar_system_id, ship_type_id, quantity, total_value_destroyed)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (date, solar_system_id, ship_type_id)
                        DO UPDATE SET
                            quantity = EXCLUDED.quantity,
                            total_value_destroyed = EXCLUDED.total_value_destroyed
                    ''', (target_date, region_id, system_id, ship_type_id, data['qty'], data['value']))
                    stats['ships'] += 1

                # Item losses
                for (system_id, item_type_id), qty in aggregated['item_losses'].items():
                    region_id = self.get_region_for_system(system_id)
                    if not region_id:
                        continue

                    cur.execute('''
                        INSERT INTO combat_item_losses
                            (date, region_id, solar_system_id, item_type_id, quantity_destroyed)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (date, solar_system_id, item_type_id)
                        DO UPDATE SET quantity_destroyed = EXCLUDED.quantity_destroyed
                    ''', (target_date, region_id, system_id, item_type_id, qty))
                    stats['items'] += 1

                # Alliance conflicts
                for (alliance_a, alliance_b), count in aggregated['alliance_conflicts'].items():
                    cur.execute('''
                        INSERT INTO alliance_conflicts (date, alliance_a, alliance_b, kill_count)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (date, alliance_a, alliance_b)
                        DO UPDATE SET kill_count = EXCLUDED.kill_count
                    ''', (target_date, alliance_a, alliance_b, count))
                    stats['conflicts'] += 1

                conn.commit()

        return stats

    def process_date(self, target_date: date, verbose: bool = False) -> Optional[dict]:
        """Download, parse, aggregate, and save killmails for a single date"""
        if verbose:
            print(f"Processing {target_date}...")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Download
            archive = self.download_daily_archive(target_date, tmppath)
            if not archive:
                return None

            if verbose:
                print(f"  Downloaded: {archive.stat().st_size / 1024 / 1024:.1f} MB")

            # Parse
            killmails = self.extract_and_parse(archive)
            if verbose:
                print(f"  Parsed: {len(killmails)} killmails")

            # Aggregate
            aggregated = self.aggregate_killmails(killmails, target_date)
            if verbose:
                print(f"  Aggregated: {len(aggregated['ship_losses'])} ship types, "
                      f"{len(aggregated['item_losses'])} item types")

            # Save
            stats = self.save_to_database(target_date, aggregated)
            if verbose:
                print(f"  Saved: {stats['ships']} ships, {stats['items']} items, "
                      f"{stats['conflicts']} conflicts")

            return {
                'date': target_date.isoformat(),
                'killmails': len(killmails),
                'ships_saved': stats['ships'],
                'items_saved': stats['items'],
                'conflicts_saved': stats['conflicts']
            }

    def backfill(self, start_date: date, end_date: date, verbose: bool = False) -> List[dict]:
        """Process killmails for a date range"""
        results = []
        current = start_date

        while current <= end_date:
            result = self.process_date(current, verbose)
            if result:
                results.append(result)
            current += timedelta(days=1)

        return results

    def has_data_for(self, target_date: date) -> bool:
        """Check if we already have data for a date"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM combat_ship_losses WHERE date = %s",
                    (target_date,)
                )
                return cur.fetchone()[0] > 0

    def cleanup_old_data(self):
        """Remove data older than retention period"""
        cutoff = date.today() - timedelta(days=WAR_DATA_RETENTION_DAYS)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM combat_ship_losses WHERE date < %s", (cutoff,))
                ships = cur.rowcount
                cur.execute("DELETE FROM combat_item_losses WHERE date < %s", (cutoff,))
                items = cur.rowcount
                cur.execute("DELETE FROM alliance_conflicts WHERE date < %s", (cutoff,))
                conflicts = cur.rowcount
                conn.commit()

        return {'ships': ships, 'items': items, 'conflicts': conflicts}

    def get_ship_losses(self, region_id: int, days: int = 7) -> List[dict]:
        """Get top ship losses for a region"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT
                        csl.ship_type_id,
                        it."typeName" as ship_name,
                        SUM(csl.quantity) as total_lost,
                        SUM(csl.total_value_destroyed) as total_value
                    FROM combat_ship_losses csl
                    JOIN "invTypes" it ON csl.ship_type_id = it."typeID"
                    WHERE csl.region_id = %s
                    AND csl.date >= CURRENT_DATE - %s
                    GROUP BY csl.ship_type_id, it."typeName"
                    ORDER BY total_lost DESC
                    LIMIT 50
                ''', (region_id, days))

                return [
                    {
                        'type_id': row[0],
                        'name': row[1],
                        'quantity': row[2],
                        'value': float(row[3]) if row[3] else 0
                    }
                    for row in cur.fetchall()
                ]

    def get_item_losses(self, region_id: int, days: int = 7) -> List[dict]:
        """Get top item losses for a region"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT
                        cil.item_type_id,
                        it."typeName" as item_name,
                        SUM(cil.quantity_destroyed) as total_lost
                    FROM combat_item_losses cil
                    JOIN "invTypes" it ON cil.item_type_id = it."typeID"
                    WHERE cil.region_id = %s
                    AND cil.date >= CURRENT_DATE - %s
                    GROUP BY cil.item_type_id, it."typeName"
                    ORDER BY total_lost DESC
                    LIMIT 50
                ''', (region_id, days))

                return [
                    {
                        'type_id': row[0],
                        'name': row[1],
                        'quantity': row[2]
                    }
                    for row in cur.fetchall()
                ]


# Singleton instance
killmail_service = KillmailService()
```

**Step 2: Verify syntax**

Run: `python3 -c "import killmail_service; print('OK')"`

Expected: "OK"

**Step 3: Commit**

```bash
git add killmail_service.py
git commit -m "feat(war-room): add killmail service for EVE Ref bulk data"
```

---

### Task 2.2: Create Killmail Fetcher Cron Job

**Files:**
- Create: `jobs/killmail_fetcher.py`
- Create: `jobs/cron_killmail_fetcher.sh`

**Step 1: Write the job script**

```python
#!/usr/bin/env python3
"""
Killmail Fetcher Cron Job
Downloads yesterday's killmail data from EVE Ref and processes it.

Usage:
    python3 -m jobs.killmail_fetcher
    python3 -m jobs.killmail_fetcher --backfill 7  # Backfill last 7 days
    python3 -m jobs.killmail_fetcher --date 2025-12-01  # Specific date
"""

import sys
import os
import argparse
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from killmail_service import killmail_service


def main():
    parser = argparse.ArgumentParser(description='Killmail Fetcher')
    parser.add_argument('--backfill', type=int, help='Backfill N days')
    parser.add_argument('--date', type=str, help='Process specific date (YYYY-MM-DD)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    print("=" * 60)
    print("EVE Co-Pilot Killmail Fetcher")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if args.backfill:
        # Backfill mode
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=args.backfill - 1)
        print(f"Backfilling {args.backfill} days: {start_date} to {end_date}")

        results = killmail_service.backfill(start_date, end_date, verbose=True)

        print(f"\nBackfill complete: {len(results)} days processed")
        total_kills = sum(r['killmails'] for r in results)
        print(f"Total killmails: {total_kills:,}")

    elif args.date:
        # Specific date mode
        target = date.fromisoformat(args.date)
        result = killmail_service.process_date(target, verbose=True)

        if result:
            print(f"\nProcessed {result['killmails']} killmails")
        else:
            print("\nNo data available for this date")

    else:
        # Default: yesterday
        yesterday = date.today() - timedelta(days=1)

        if killmail_service.has_data_for(yesterday):
            print(f"Data for {yesterday} already exists, skipping")
        else:
            result = killmail_service.process_date(yesterday, verbose=True)

            if result:
                print(f"\nProcessed {result['killmails']} killmails")

        # Cleanup old data
        print("\nCleaning up old data...")
        cleanup = killmail_service.cleanup_old_data()
        if any(cleanup.values()):
            print(f"  Removed: {cleanup['ships']} ships, {cleanup['items']} items, "
                  f"{cleanup['conflicts']} conflicts")

    print("=" * 60)


if __name__ == "__main__":
    main()
```

**Step 2: Write shell wrapper**

Create `jobs/cron_killmail_fetcher.sh`:

```bash
#!/bin/bash
cd /home/cytrex/eve_copilot
python3 -m jobs.killmail_fetcher >> logs/killmail_fetcher.log 2>&1
```

**Step 3: Make executable**

Run: `chmod +x jobs/cron_killmail_fetcher.sh`

**Step 4: Test the job**

Run: `python3 -m jobs.killmail_fetcher --backfill 1 --verbose`

Expected: Downloads and processes yesterday's killmails.

**Step 5: Add to crontab**

Run: `crontab -e`

Add line:
```
0 6 * * * /home/cytrex/eve_copilot/jobs/cron_killmail_fetcher.sh
```

**Step 6: Commit**

```bash
git add jobs/killmail_fetcher.py jobs/cron_killmail_fetcher.sh
git commit -m "feat(war-room): add killmail fetcher cron job"
```

---

## WP3: Sovereignty Service

**Depends on:** WP1
**Enables:** WP5, WP6

### Task 3.1: Create Sovereignty Service

**Files:**
- Create: `sovereignty_service.py`

**Step 1: Write the service**

```python
#!/usr/bin/env python3
"""
Sovereignty Service - Track sovereignty campaigns from ESI
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests

from database import get_db_connection
from config import ESI_BASE_URL, ESI_USER_AGENT


class SovereigntyService:
    """Tracks sovereignty campaigns and predicts battles"""

    def __init__(self):
        self._alliance_names: Dict[int, str] = {}

    def fetch_campaigns(self) -> List[dict]:
        """Fetch current sovereignty campaigns from ESI"""
        url = f"{ESI_BASE_URL}/sovereignty/campaigns/"

        try:
            response = requests.get(
                url,
                headers={"User-Agent": ESI_USER_AGENT},
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"ESI error: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error fetching campaigns: {e}")
            return []

    def get_alliance_name(self, alliance_id: int) -> Optional[str]:
        """Get alliance name from ESI (cached)"""
        if alliance_id in self._alliance_names:
            return self._alliance_names[alliance_id]

        url = f"{ESI_BASE_URL}/alliances/{alliance_id}/"

        try:
            response = requests.get(
                url,
                headers={"User-Agent": ESI_USER_AGENT},
                timeout=10
            )

            if response.status_code == 200:
                name = response.json().get('name', f'Alliance {alliance_id}')
                self._alliance_names[alliance_id] = name
                return name
        except:
            pass

        return f"Alliance {alliance_id}"

    def update_campaigns(self) -> dict:
        """Fetch and save campaigns to database"""
        campaigns = self.fetch_campaigns()

        if not campaigns:
            return {'updated': 0, 'new': 0}

        stats = {'updated': 0, 'new': 0}

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for c in campaigns:
                    defender_name = None
                    if c.get('defender_id'):
                        defender_name = self.get_alliance_name(c['defender_id'])

                    cur.execute('''
                        INSERT INTO sovereignty_campaigns (
                            campaign_id, event_type, solar_system_id, constellation_id,
                            defender_id, defender_name, attacker_score, defender_score,
                            start_time, structure_id, last_updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (campaign_id) DO UPDATE SET
                            attacker_score = EXCLUDED.attacker_score,
                            defender_score = EXCLUDED.defender_score,
                            last_updated_at = NOW()
                        RETURNING (xmax = 0) as is_new
                    ''', (
                        c['campaign_id'],
                        c['event_type'],
                        c['solar_system_id'],
                        c.get('constellation_id'),
                        c.get('defender_id'),
                        defender_name,
                        c.get('attackers_score'),
                        c.get('defender_score'),
                        c['start_time'],
                        c.get('structure_id')
                    ))

                    is_new = cur.fetchone()[0]
                    if is_new:
                        stats['new'] += 1
                    else:
                        stats['updated'] += 1

                # Clean up old campaigns (past their start time by more than 24h)
                cur.execute('''
                    DELETE FROM sovereignty_campaigns
                    WHERE start_time < NOW() - INTERVAL '24 hours'
                ''')

                conn.commit()

        return stats

    def get_upcoming_battles(self, hours: int = 48) -> List[dict]:
        """Get campaigns starting in next X hours"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT
                        sc.campaign_id,
                        sc.event_type,
                        sc.solar_system_id,
                        srm.solar_system_name,
                        srm.region_id,
                        srm.region_name,
                        sc.defender_id,
                        sc.defender_name,
                        sc.attacker_score,
                        sc.defender_score,
                        sc.start_time
                    FROM sovereignty_campaigns sc
                    LEFT JOIN system_region_map srm ON sc.solar_system_id = srm.solar_system_id
                    WHERE sc.start_time > NOW()
                    AND sc.start_time < NOW() + INTERVAL '%s hours'
                    ORDER BY sc.start_time ASC
                ''', (hours,))

                return [
                    {
                        'campaign_id': row[0],
                        'event_type': row[1],
                        'solar_system_id': row[2],
                        'system_name': row[3],
                        'region_id': row[4],
                        'region_name': row[5],
                        'defender_id': row[6],
                        'defender_name': row[7],
                        'attacker_score': row[8],
                        'defender_score': row[9],
                        'start_time': row[10].isoformat() if row[10] else None
                    }
                    for row in cur.fetchall()
                ]


# Singleton instance
sovereignty_service = SovereigntyService()
```

**Step 2: Verify syntax**

Run: `python3 -c "import sovereignty_service; print('OK')"`

Expected: "OK"

**Step 3: Commit**

```bash
git add sovereignty_service.py
git commit -m "feat(war-room): add sovereignty campaign tracking service"
```

---

### Task 3.2: Create Sovereignty Tracker Cron Job

**Files:**
- Create: `jobs/sov_tracker.py`
- Create: `jobs/cron_sov_tracker.sh`

**Step 1: Write the job**

```python
#!/usr/bin/env python3
"""
Sovereignty Tracker - Updates campaign data every 30 minutes
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sovereignty_service import sovereignty_service


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sovereignty Tracker")

    stats = sovereignty_service.update_campaigns()
    print(f"  Campaigns: {stats['new']} new, {stats['updated']} updated")

    upcoming = sovereignty_service.get_upcoming_battles(hours=24)
    if upcoming:
        print(f"  Upcoming battles (24h): {len(upcoming)}")
        for battle in upcoming[:5]:
            print(f"    - {battle['system_name']} ({battle['event_type']}) at {battle['start_time']}")


if __name__ == "__main__":
    main()
```

**Step 2: Write shell wrapper**

Create `jobs/cron_sov_tracker.sh`:

```bash
#!/bin/bash
cd /home/cytrex/eve_copilot
python3 -m jobs.sov_tracker >> logs/sov_tracker.log 2>&1
```

**Step 3: Make executable and add to crontab**

Run:
```bash
chmod +x jobs/cron_sov_tracker.sh
(crontab -l 2>/dev/null; echo "*/30 * * * * /home/cytrex/eve_copilot/jobs/cron_sov_tracker.sh") | crontab -
```

**Step 4: Test**

Run: `python3 -m jobs.sov_tracker`

Expected: Output showing campaigns fetched.

**Step 5: Commit**

```bash
git add jobs/sov_tracker.py jobs/cron_sov_tracker.sh
git commit -m "feat(war-room): add sovereignty tracker cron job"
```

---

## WP4: Faction Warfare Service

**Depends on:** WP1
**Enables:** WP5, WP6

### Task 4.1: Create FW Service

**Files:**
- Create: `fw_service.py`

**Step 1: Write the service**

```python
#!/usr/bin/env python3
"""
Faction Warfare Service - Track contested systems
"""

from datetime import datetime
from typing import List, Dict
import requests

from database import get_db_connection
from config import ESI_BASE_URL, ESI_USER_AGENT


# Faction ID to name mapping
FACTIONS = {
    500001: "Caldari State",
    500002: "Minmatar Republic",
    500003: "Amarr Empire",
    500004: "Gallente Federation"
}


class FactionWarfareService:
    """Tracks Faction Warfare contested systems"""

    def fetch_fw_systems(self) -> List[dict]:
        """Fetch FW system status from ESI"""
        url = f"{ESI_BASE_URL}/fw/systems/"

        try:
            response = requests.get(
                url,
                headers={"User-Agent": ESI_USER_AGENT},
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"ESI error: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error fetching FW systems: {e}")
            return []

    def update_status(self) -> dict:
        """Snapshot current FW status to database"""
        systems = self.fetch_fw_systems()

        if not systems:
            return {'saved': 0}

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for s in systems:
                    cur.execute('''
                        INSERT INTO fw_system_status (
                            solar_system_id, owner_faction_id, occupier_faction_id,
                            contested, victory_points, victory_points_threshold
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (
                        s['solar_system_id'],
                        s['owner_faction_id'],
                        s['occupier_faction_id'],
                        s['contested'],
                        s['victory_points'],
                        s['victory_points_threshold']
                    ))

                conn.commit()

        return {'saved': len(systems)}

    def get_hotspots(self, min_contested_percent: float = 50.0) -> List[dict]:
        """Get systems with high contested status"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get latest snapshot for each system
                cur.execute('''
                    WITH latest AS (
                        SELECT DISTINCT ON (solar_system_id)
                            solar_system_id, owner_faction_id, occupier_faction_id,
                            contested, victory_points, victory_points_threshold,
                            contested_percent, snapshot_time
                        FROM fw_system_status
                        ORDER BY solar_system_id, snapshot_time DESC
                    )
                    SELECT
                        l.solar_system_id,
                        srm.solar_system_name,
                        srm.region_id,
                        srm.region_name,
                        l.owner_faction_id,
                        l.occupier_faction_id,
                        l.contested,
                        l.contested_percent
                    FROM latest l
                    LEFT JOIN system_region_map srm ON l.solar_system_id = srm.solar_system_id
                    WHERE l.contested_percent >= %s
                    ORDER BY l.contested_percent DESC
                    LIMIT 50
                ''', (min_contested_percent,))

                return [
                    {
                        'solar_system_id': row[0],
                        'system_name': row[1],
                        'region_id': row[2],
                        'region_name': row[3],
                        'owner_faction': FACTIONS.get(row[4], f"Faction {row[4]}"),
                        'occupier_faction': FACTIONS.get(row[5], f"Faction {row[5]}"),
                        'contested_status': row[6],
                        'contested_percent': round(row[7], 1) if row[7] else 0
                    }
                    for row in cur.fetchall()
                ]

    def get_vulnerable_systems(self) -> List[dict]:
        """Get systems close to flipping (>90% contested)"""
        return self.get_hotspots(min_contested_percent=90.0)

    def cleanup_old_snapshots(self, days: int = 7):
        """Remove snapshots older than X days"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    DELETE FROM fw_system_status
                    WHERE snapshot_time < NOW() - INTERVAL '%s days'
                ''', (days,))
                deleted = cur.rowcount
                conn.commit()

        return deleted


# Singleton instance
fw_service = FactionWarfareService()
```

**Step 2: Verify syntax**

Run: `python3 -c "import fw_service; print('OK')"`

Expected: "OK"

**Step 3: Commit**

```bash
git add fw_service.py
git commit -m "feat(war-room): add faction warfare tracking service"
```

---

### Task 4.2: Create FW Tracker Cron Job

**Files:**
- Create: `jobs/fw_tracker.py`
- Create: `jobs/cron_fw_tracker.sh`

**Step 1: Write the job**

```python
#!/usr/bin/env python3
"""
Faction Warfare Tracker - Updates FW status every 30 minutes
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fw_service import fw_service


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] FW Tracker")

    # Update status
    stats = fw_service.update_status()
    print(f"  Systems tracked: {stats['saved']}")

    # Show hotspots
    hotspots = fw_service.get_hotspots(min_contested_percent=70.0)
    if hotspots:
        print(f"  Hotspots (>70% contested): {len(hotspots)}")
        for h in hotspots[:5]:
            print(f"    - {h['system_name']}: {h['contested_percent']}% "
                  f"({h['owner_faction']} vs {h['occupier_faction']})")

    # Cleanup
    deleted = fw_service.cleanup_old_snapshots(days=7)
    if deleted > 0:
        print(f"  Cleaned up {deleted} old snapshots")


if __name__ == "__main__":
    main()
```

**Step 2: Write shell wrapper**

Create `jobs/cron_fw_tracker.sh`:

```bash
#!/bin/bash
cd /home/cytrex/eve_copilot
python3 -m jobs.fw_tracker >> logs/fw_tracker.log 2>&1
```

**Step 3: Make executable and add to crontab**

Run:
```bash
chmod +x jobs/cron_fw_tracker.sh
(crontab -l 2>/dev/null; echo "*/30 * * * * /home/cytrex/eve_copilot/jobs/cron_fw_tracker.sh") | crontab -
```

**Step 4: Test**

Run: `python3 -m jobs.fw_tracker`

Expected: Output showing FW systems tracked.

**Step 5: Commit**

```bash
git add jobs/fw_tracker.py jobs/cron_fw_tracker.sh
git commit -m "feat(war-room): add faction warfare tracker cron job"
```

---

## WP5: War Analyzer Service

**Depends on:** WP2, WP3, WP4
**Enables:** WP6

### Task 5.1: Create War Analyzer

**Files:**
- Create: `war_analyzer.py`

**Step 1: Write the analyzer**

```python
#!/usr/bin/env python3
"""
War Analyzer - Combines combat data for demand analysis
"""

from datetime import date, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

from database import get_db_connection
from config import WAR_DOCTRINE_MIN_FLEET_SIZE, WAR_HEATMAP_MIN_KILLS


class WarAnalyzer:
    """Combines all data sources for demand analysis"""

    def analyze_demand(self, region_id: int, days: int = 7) -> dict:
        """
        Full demand analysis for a region.
        Returns ships lost, items lost, market gaps, upcoming battles, FW hotspots.
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Top ships lost
                cur.execute('''
                    SELECT
                        csl.ship_type_id,
                        it."typeName",
                        SUM(csl.quantity) as total,
                        COALESCE(mp.sell_volume, 0) as market_stock
                    FROM combat_ship_losses csl
                    JOIN "invTypes" it ON csl.ship_type_id = it."typeID"
                    LEFT JOIN market_prices mp ON mp.type_id = csl.ship_type_id
                        AND mp.region_id = %s
                    WHERE csl.region_id = %s
                    AND csl.date >= CURRENT_DATE - %s
                    GROUP BY csl.ship_type_id, it."typeName", mp.sell_volume
                    ORDER BY total DESC
                    LIMIT 20
                ''', (region_id, region_id, days))

                ships_lost = [
                    {
                        'type_id': row[0],
                        'name': row[1],
                        'quantity': row[2],
                        'market_stock': row[3],
                        'gap': max(0, row[2] - row[3])
                    }
                    for row in cur.fetchall()
                ]

                # Top items lost
                cur.execute('''
                    SELECT
                        cil.item_type_id,
                        it."typeName",
                        SUM(cil.quantity_destroyed) as total,
                        COALESCE(mp.sell_volume, 0) as market_stock
                    FROM combat_item_losses cil
                    JOIN "invTypes" it ON cil.item_type_id = it."typeID"
                    LEFT JOIN market_prices mp ON mp.type_id = cil.item_type_id
                        AND mp.region_id = %s
                    WHERE cil.region_id = %s
                    AND cil.date >= CURRENT_DATE - %s
                    GROUP BY cil.item_type_id, it."typeName", mp.sell_volume
                    ORDER BY total DESC
                    LIMIT 20
                ''', (region_id, region_id, days))

                items_lost = [
                    {
                        'type_id': row[0],
                        'name': row[1],
                        'quantity': row[2],
                        'market_stock': row[3],
                        'gap': max(0, row[2] - row[3])
                    }
                    for row in cur.fetchall()
                ]

                # Market gaps (where losses exceed stock)
                market_gaps = [s for s in ships_lost if s['gap'] > 0][:10]
                market_gaps.extend([i for i in items_lost if i['gap'] > 0][:10])
                market_gaps.sort(key=lambda x: x['gap'], reverse=True)

        return {
            'region_id': region_id,
            'days': days,
            'ships_lost': ships_lost,
            'items_lost': items_lost,
            'market_gaps': market_gaps[:15]
        }

    def get_heatmap_data(self, days: int = 7, min_kills: int = None) -> List[dict]:
        """Get kill data with coordinates for heatmap visualization"""
        if min_kills is None:
            min_kills = WAR_HEATMAP_MIN_KILLS

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT
                        csl.solar_system_id,
                        srm.solar_system_name,
                        srm.region_id,
                        srm.region_name,
                        srm.security_status,
                        s.x / 1e16 as x,
                        s.z / 1e16 as z,
                        SUM(csl.quantity) as kills
                    FROM combat_ship_losses csl
                    JOIN system_region_map srm ON csl.solar_system_id = srm.solar_system_id
                    JOIN "mapSolarSystems" s ON csl.solar_system_id = s."solarSystemID"
                    WHERE csl.date >= CURRENT_DATE - %s
                    GROUP BY csl.solar_system_id, srm.solar_system_name,
                             srm.region_id, srm.region_name, srm.security_status,
                             s.x, s.z
                    HAVING SUM(csl.quantity) >= %s
                    ORDER BY kills DESC
                ''', (days, min_kills))

                return [
                    {
                        'system_id': row[0],
                        'name': row[1],
                        'region_id': row[2],
                        'region': row[3],
                        'security': round(float(row[4]), 2) if row[4] else 0,
                        'x': round(float(row[5]), 2) if row[5] else 0,
                        'z': round(float(row[6]), 2) if row[6] else 0,
                        'kills': row[7]
                    }
                    for row in cur.fetchall()
                ]

    def detect_doctrines(self, region_id: int, days: int = 7) -> List[dict]:
        """
        Detect fleet doctrines by finding bulk losses of same ship type.
        A doctrine is detected when MIN_FLEET_SIZE+ of same ship die in same system on same day.
        """
        min_size = WAR_DOCTRINE_MIN_FLEET_SIZE

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT
                        csl.date,
                        csl.solar_system_id,
                        srm.solar_system_name,
                        csl.ship_type_id,
                        it."typeName" as ship_name,
                        csl.quantity
                    FROM combat_ship_losses csl
                    JOIN system_region_map srm ON csl.solar_system_id = srm.solar_system_id
                    JOIN "invTypes" it ON csl.ship_type_id = it."typeID"
                    WHERE csl.region_id = %s
                    AND csl.date >= CURRENT_DATE - %s
                    AND csl.quantity >= %s
                    ORDER BY csl.quantity DESC
                    LIMIT 20
                ''', (region_id, days, min_size))

                return [
                    {
                        'date': row[0].isoformat(),
                        'system_id': row[1],
                        'system_name': row[2],
                        'ship_type_id': row[3],
                        'ship_name': row[4],
                        'quantity': row[5],
                        'estimated_restock': row[5]  # Simple estimate
                    }
                    for row in cur.fetchall()
                ]

    def get_alliance_conflicts(self, days: int = 7, top: int = 20) -> List[dict]:
        """Get top alliance conflicts"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT
                        alliance_a,
                        alliance_b,
                        SUM(kill_count) as total_kills
                    FROM alliance_conflicts
                    WHERE date >= CURRENT_DATE - %s
                    GROUP BY alliance_a, alliance_b
                    ORDER BY total_kills DESC
                    LIMIT %s
                ''', (days, top))

                return [
                    {
                        'alliance_a': row[0],
                        'alliance_b': row[1],
                        'kills': row[2]
                    }
                    for row in cur.fetchall()
                ]

    def get_system_danger_score(self, solar_system_id: int, days: int = 1) -> dict:
        """Get danger score for a system (kills in last X days)"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT COALESCE(SUM(quantity), 0)
                    FROM combat_ship_losses
                    WHERE solar_system_id = %s
                    AND date >= CURRENT_DATE - %s
                ''', (solar_system_id, days))

                kills = cur.fetchone()[0]

                # Score: 0-10 based on kill activity
                if kills == 0:
                    score = 0
                elif kills < 5:
                    score = 2
                elif kills < 20:
                    score = 5
                elif kills < 50:
                    score = 7
                else:
                    score = 10

                return {
                    'system_id': solar_system_id,
                    'kills_24h': kills,
                    'danger_score': score
                }


# Singleton instance
war_analyzer = WarAnalyzer()
```

**Step 2: Verify syntax**

Run: `python3 -c "import war_analyzer; print('OK')"`

Expected: "OK"

**Step 3: Commit**

```bash
git add war_analyzer.py
git commit -m "feat(war-room): add war analyzer service"
```

---

## WP6: API Router

**Depends on:** WP2, WP3, WP4, WP5
**Enables:** WP7, WP8

### Task 6.1: Create War Router

**Files:**
- Create: `routers/war.py`
- Modify: `main.py`

**Step 1: Write the router**

```python
"""
War Room Router
Endpoints for combat analysis and demand forecasting
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from killmail_service import killmail_service
from sovereignty_service import sovereignty_service
from fw_service import fw_service
from war_analyzer import war_analyzer
from config import REGIONS

router = APIRouter(prefix="/api/war", tags=["War Room"])


@router.get("/losses/{region_id}")
async def get_losses(
    region_id: int,
    days: int = Query(7, ge=1, le=30),
    type: str = Query("all", regex="^(all|ships|items)$")
):
    """Get combat losses for a region"""
    try:
        if type == "ships":
            return {"ships": killmail_service.get_ship_losses(region_id, days)}
        elif type == "items":
            return {"items": killmail_service.get_item_losses(region_id, days)}
        else:
            return {
                "ships": killmail_service.get_ship_losses(region_id, days),
                "items": killmail_service.get_item_losses(region_id, days)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demand/{region_id}")
async def get_demand(
    region_id: int,
    days: int = Query(7, ge=1, le=30)
):
    """Full demand analysis for a region"""
    try:
        return war_analyzer.analyze_demand(region_id, days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heatmap")
async def get_heatmap(
    days: int = Query(7, ge=1, le=30),
    min_kills: int = Query(5, ge=1)
):
    """Get heatmap data for galaxy visualization"""
    try:
        return {"systems": war_analyzer.get_heatmap_data(days, min_kills)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns")
async def get_campaigns(
    hours: int = Query(48, ge=1, le=168)
):
    """Get upcoming sovereignty battles"""
    try:
        return {"campaigns": sovereignty_service.get_upcoming_battles(hours)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fw/hotspots")
async def get_fw_hotspots(
    min_contested: float = Query(50.0, ge=0, le=100)
):
    """Get Faction Warfare hotspots"""
    try:
        return {"hotspots": fw_service.get_hotspots(min_contested)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/doctrines/{region_id}")
async def get_doctrines(
    region_id: int,
    days: int = Query(7, ge=1, le=30)
):
    """Detect fleet doctrines from loss patterns"""
    try:
        return {"doctrines": war_analyzer.detect_doctrines(region_id, days)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflicts")
async def get_conflicts(
    days: int = Query(7, ge=1, le=30),
    top: int = Query(20, ge=1, le=100)
):
    """Get top alliance conflicts"""
    try:
        return {"conflicts": war_analyzer.get_alliance_conflicts(days, top)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/{system_id}/danger")
async def get_system_danger(
    system_id: int,
    days: int = Query(1, ge=1, le=7)
):
    """Get danger score for a solar system"""
    try:
        return war_analyzer.get_system_danger_score(system_id, days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 2: Register router in main.py**

Add to imports at top of `main.py`:

```python
from routers.war import router as war_router
```

Add after other router registrations (around line 48):

```python
app.include_router(war_router)
```

**Step 3: Verify**

Run: `python3 -c "from main import app; print('OK')"`

Expected: "OK"

**Step 4: Start server and test**

Run: `curl http://localhost:8000/api/war/heatmap?days=1`

Expected: JSON response with systems array.

**Step 5: Commit**

```bash
git add routers/war.py main.py
git commit -m "feat(war-room): add REST API endpoints"
```

---

## WP7: Route Safety Integration

**Depends on:** WP5, WP6
**Enables:** WP9

### Task 7.1: Extend Route Service

**Files:**
- Modify: `route_service.py`

**Step 1: Add danger overlay method**

Add to `RouteService` class in `route_service.py`:

```python
def get_route_with_danger(
    self,
    from_system_id: int,
    to_system_id: int,
    avoid_lowsec: bool = True,
    avoid_nullsec: bool = True
) -> Optional[dict]:
    """
    Find route with danger scores for each system.
    Returns route with kill activity overlay.
    """
    from war_analyzer import war_analyzer

    route = self.find_route(from_system_id, to_system_id, avoid_lowsec, avoid_nullsec)

    if not route:
        return None

    # Add danger scores
    total_danger = 0
    dangerous_systems = []

    for system in route:
        danger = war_analyzer.get_system_danger_score(system['system_id'], days=1)
        system['danger_score'] = danger['danger_score']
        system['kills_24h'] = danger['kills_24h']
        total_danger += danger['danger_score']

        if danger['danger_score'] >= 5:
            dangerous_systems.append({
                'name': system['name'],
                'kills': danger['kills_24h'],
                'score': danger['danger_score']
            })

    return {
        'route': route,
        'total_jumps': len(route),
        'total_danger_score': total_danger,
        'average_danger': round(total_danger / len(route), 1) if route else 0,
        'dangerous_systems': dangerous_systems,
        'warning': len(dangerous_systems) > 0
    }
```

**Step 2: Add API endpoint**

Add to `main.py` or create endpoint in router:

```python
@app.get("/api/route/safe/{from_system}/{to_system}")
async def get_safe_route(
    from_system: int,
    to_system: int,
    avoid_lowsec: bool = True,
    avoid_nullsec: bool = True
):
    """Get route with danger analysis"""
    from route_service import RouteService

    service = RouteService()
    result = service.get_route_with_danger(from_system, to_system, avoid_lowsec, avoid_nullsec)

    if not result:
        raise HTTPException(status_code=404, detail="No route found")

    return result
```

**Step 3: Commit**

```bash
git add route_service.py main.py
git commit -m "feat(war-room): add route safety with danger scoring"
```

---

## WP8: Frontend - War Room Page

**Depends on:** WP6
**Enables:** WP9

### Task 8.1: Create War Room Page

**Files:**
- Create: `frontend/src/pages/WarRoom.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api.ts`

**Step 1: Add API functions**

Add to `frontend/src/api.ts`:

```typescript
// War Room API
export const getWarLosses = (regionId: number, days = 7) =>
  api.get(`/api/war/losses/${regionId}`, { params: { days } });

export const getWarDemand = (regionId: number, days = 7) =>
  api.get(`/api/war/demand/${regionId}`, { params: { days } });

export const getWarHeatmap = (days = 7, minKills = 5) =>
  api.get('/api/war/heatmap', { params: { days, min_kills: minKills } });

export const getWarCampaigns = (hours = 48) =>
  api.get('/api/war/campaigns', { params: { hours } });

export const getFWHotspots = (minContested = 50) =>
  api.get('/api/war/fw/hotspots', { params: { min_contested: minContested } });

export const getWarDoctrines = (regionId: number, days = 7) =>
  api.get(`/api/war/doctrines/${regionId}`, { params: { days } });

export const getWarConflicts = (days = 7) =>
  api.get('/api/war/conflicts', { params: { days } });
```

**Step 2: Create WarRoom component**

Create `frontend/src/pages/WarRoom.tsx`:

```tsx
import React, { useState, useEffect } from 'react';
import {
  getWarDemand,
  getWarHeatmap,
  getWarCampaigns,
  getFWHotspots,
  getWarDoctrines,
  getWarConflicts
} from '../api';
import { formatNumber } from '../utils/format';

const REGIONS = {
  10000002: 'The Forge (Jita)',
  10000043: 'Domain (Amarr)',
  10000030: 'Heimatar (Rens)',
  10000032: 'Sinq Laison (Dodixie)',
  10000042: 'Metropolis (Hek)',
};

export default function WarRoom() {
  const [regionId, setRegionId] = useState(10000002);
  const [days, setDays] = useState(7);
  const [demand, setDemand] = useState<any>(null);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [fwHotspots, setFwHotspots] = useState<any[]>([]);
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [regionId, days]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [demandRes, campaignsRes, fwRes, heatmapRes] = await Promise.all([
        getWarDemand(regionId, days),
        getWarCampaigns(48),
        getFWHotspots(50),
        getWarHeatmap(days, 5)
      ]);

      setDemand(demandRes.data);
      setCampaigns(campaignsRes.data.campaigns || []);
      setFwHotspots(fwRes.data.hotspots || []);
      setHeatmap(heatmapRes.data.systems || []);
    } catch (error) {
      console.error('Failed to load war data:', error);
    }
    setLoading(false);
  };

  if (loading) {
    return <div className="p-4">Loading war data...</div>;
  }

  return (
    <div className="p-4 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">War Room</h1>
        <div className="flex gap-4">
          <select
            value={regionId}
            onChange={(e) => setRegionId(Number(e.target.value))}
            className="border rounded px-3 py-2"
          >
            {Object.entries(REGIONS).map(([id, name]) => (
              <option key={id} value={id}>{name}</option>
            ))}
          </select>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="border rounded px-3 py-2"
          >
            <option value={1}>24 hours</option>
            <option value={3}>3 days</option>
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Ships Destroyed */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-3">Ships Destroyed</h2>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {demand?.ships_lost?.slice(0, 10).map((ship: any) => (
              <div key={ship.type_id} className="flex justify-between text-sm">
                <span>{ship.name}</span>
                <span className="font-mono">{formatNumber(ship.quantity)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Items Destroyed */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-3">Items Destroyed</h2>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {demand?.items_lost?.slice(0, 10).map((item: any) => (
              <div key={item.type_id} className="flex justify-between text-sm">
                <span className="truncate flex-1">{item.name}</span>
                <span className="font-mono ml-2">{formatNumber(item.quantity)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Market Gaps */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-3 text-red-600">Market Gaps</h2>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {demand?.market_gaps?.length > 0 ? (
              demand.market_gaps.map((item: any) => (
                <div key={item.type_id} className="text-sm">
                  <div className="flex justify-between">
                    <span className="truncate">{item.name}</span>
                    <span className="text-red-600 font-mono">-{formatNumber(item.gap)}</span>
                  </div>
                  <div className="text-xs text-gray-500">
                    Lost: {formatNumber(item.quantity)} | Stock: {formatNumber(item.market_stock)}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-gray-500 text-sm">No significant gaps detected</div>
            )}
          </div>
        </div>
      </div>

      {/* Sovereignty Campaigns */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h2 className="font-semibold mb-3">Upcoming Battles (Sov Timers)</h2>
        {campaigns.length > 0 ? (
          <div className="space-y-2">
            {campaigns.slice(0, 5).map((c: any) => (
              <div key={c.campaign_id} className="flex justify-between items-center text-sm border-b pb-2">
                <div>
                  <span className="font-medium">{c.system_name}</span>
                  <span className="text-gray-500 ml-2">({c.region_name})</span>
                  <span className="ml-2 px-2 py-0.5 bg-gray-100 rounded text-xs">{c.event_type}</span>
                </div>
                <div className="text-right">
                  <div>{new Date(c.start_time).toLocaleString()}</div>
                  <div className="text-xs text-gray-500">Defender: {c.defender_name}</div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-gray-500 text-sm">No upcoming campaigns</div>
        )}
      </div>

      {/* FW Hotspots */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h2 className="font-semibold mb-3">Faction Warfare Hotspots</h2>
        {fwHotspots.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {fwHotspots.slice(0, 8).map((h: any) => (
              <div key={h.solar_system_id} className="text-sm p-2 bg-orange-50 rounded">
                <div className="font-medium">{h.system_name}</div>
                <div className="text-orange-600">{h.contested_percent}% contested</div>
                <div className="text-xs text-gray-500">{h.owner_faction}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-gray-500 text-sm">No active hotspots</div>
        )}
      </div>

      {/* Simple Heatmap (Top Systems) */}
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="font-semibold mb-3">Combat Hotspots (Top Systems)</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {heatmap.slice(0, 10).map((s: any) => (
            <div
              key={s.system_id}
              className="p-2 rounded text-sm"
              style={{
                backgroundColor: `rgba(239, 68, 68, ${Math.min(s.kills / 100, 0.8)})`
              }}
            >
              <div className="font-medium">{s.name}</div>
              <div>{s.kills} kills</div>
              <div className="text-xs opacity-75">{s.region}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

**Step 3: Add route to App.tsx**

Add import:
```typescript
import WarRoom from './pages/WarRoom';
```

Add route (inside Routes):
```tsx
<Route path="/war-room" element={<WarRoom />} />
```

Add navigation link where appropriate.

**Step 4: Build and test**

Run:
```bash
cd frontend && npm run build
```

Expected: Build succeeds.

**Step 5: Commit**

```bash
git add frontend/src/pages/WarRoom.tsx frontend/src/App.tsx frontend/src/api.ts
git commit -m "feat(war-room): add frontend War Room page"
```

---

## WP9: Frontend Integration

**Depends on:** WP7, WP8

### Task 9.1: Add Conflict Alert Component

**Files:**
- Create: `frontend/src/components/ConflictAlert.tsx`

**Step 1: Create component**

```tsx
import React from 'react';

interface DangerousSystem {
  name: string;
  kills: number;
  score: number;
}

interface ConflictAlertProps {
  dangerousSystems: DangerousSystem[];
  totalDanger: number;
}

export default function ConflictAlert({ dangerousSystems, totalDanger }: ConflictAlertProps) {
  if (dangerousSystems.length === 0) {
    return null;
  }

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
      <div className="flex items-center gap-2 text-red-700 font-medium mb-2">
        <span>⚠️</span>
        <span>Route passes through conflict zone</span>
      </div>
      <div className="text-sm text-red-600">
        {dangerousSystems.map((sys, i) => (
          <span key={sys.name}>
            {sys.name} ({sys.kills} kills/24h)
            {i < dangerousSystems.length - 1 ? ', ' : ''}
          </span>
        ))}
      </div>
      <div className="text-xs text-red-500 mt-1">
        Total danger score: {totalDanger}
      </div>
    </div>
  );
}
```

**Step 2: Integrate into ShoppingPlanner**

Import and use `ConflictAlert` component when displaying routes. Pass route danger data from `/api/route/safe/` endpoint.

**Step 3: Commit**

```bash
git add frontend/src/components/ConflictAlert.tsx
git commit -m "feat(war-room): add conflict alert component for route warnings"
```

---

## Execution Summary

### Parallel Batch Execution Order

**Batch 1 (Sequential - Must complete first):**
- WP1: Database Schema & Infrastructure

**Batch 2 (Parallel - 3 agents):**
- Agent A: WP2 (Killmail Service + Cron)
- Agent B: WP3 (Sovereignty Service + Cron)
- Agent C: WP4 (FW Service + Cron)

**Batch 3 (Parallel - 2 agents):**
- Agent A: WP5 (War Analyzer)
- Agent B: WP6 (API Router)

**Batch 4 (Parallel - 2 agents):**
- Agent A: WP7 (Route Safety Integration)
- Agent B: WP8 (Frontend War Room Page)

**Batch 5 (Sequential):**
- WP9: Frontend Integration (Conflict Alert)

### Agent Dispatch Commands

For each batch, dispatch agents with:

```
Task: Implement WP[N] from /home/cytrex/eve_copilot/docs/plans/2025-12-07-war-room-implementation.md

Follow each task step-by-step:
1. Create/modify files exactly as specified
2. Run verification commands
3. Commit after each task
4. Report completion status
```

### Post-Implementation

After all batches complete:

1. **Backfill data:** `python3 -m jobs.killmail_fetcher --backfill 7`
2. **Run trackers:** `python3 -m jobs.sov_tracker && python3 -m jobs.fw_tracker`
3. **Verify API:** `curl http://localhost:8000/api/war/heatmap`
4. **Build frontend:** `cd frontend && npm run build`
5. **Test War Room page:** Open http://localhost:5173/war-room
