#!/usr/bin/env python3
"""
EVE Co-Pilot Sovereignty Tracker Job

Fetches sovereignty campaigns from ESI and syncs to database.
Runs as cronjob every 30 minutes.

Workflow:
1. Fetch campaigns from ESI /sovereignty/campaigns/
2. Get alliance names for defenders
3. Sync to sovereignty_campaigns table
4. Clean up old campaigns (>24h past start time)

Usage:
    python3 -m jobs.sov_tracker
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sovereignty_service import sovereignty_service


def main():
    print("=" * 60)
    print("EVE Co-Pilot Sovereignty Tracker")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    # Update campaigns
    print("Fetching sovereignty campaigns from ESI...")
    result = sovereignty_service.update_campaigns()

    if "error" in result:
        print(f"ERROR: {result['error']}")
        return

    print(f"Total campaigns: {result['total_campaigns']}")
    print(f"New: {result['new']}")
    print(f"Updated: {result['updated']}")
    print(f"Deleted (old): {result['deleted']}")
    print()

    # Show upcoming battles
    print("Upcoming battles (next 48 hours):")
    battles = sovereignty_service.get_upcoming_battles(hours=48)

    if not battles:
        print("  No battles scheduled in the next 48 hours")
    else:
        for battle in battles[:10]:  # Show first 10
            system = battle.get('solar_system_name', f"System {battle['solar_system_id']}")
            region = battle.get('region_name', 'Unknown')
            event = battle.get('event_type', 'Unknown')
            defender = battle.get('defender_name', 'Unknown')
            hours = battle.get('hours_until_start', 0)

            print(f"  [{hours:.1f}h] {system} ({region}) - {event} - {defender}")

    print()
    print("=" * 60)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
