#!/usr/bin/env python3
"""
EVE Co-Pilot Faction Warfare Tracker

Tracks FW system status and detects hotspots.
Runs as a cronjob periodically.

Workflow:
1. Fetch current FW system status from ESI
2. Snapshot to database
3. Detect and display hotspots (>70% contested)
4. Cleanup old snapshots

Usage:
    python3 -m jobs.fw_tracker
    python3 -m jobs.fw_tracker --verbose
"""

import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fw_service import fw_service


def run_fw_tracker(verbose: bool = False):
    """
    Runs the FW tracker workflow.
    """
    if verbose:
        print("=" * 60)
        print("EVE Co-Pilot Faction Warfare Tracker")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()

    # Step 1: Update status
    if verbose:
        print("Step 1: Fetching FW system status from ESI...")

    result = fw_service.update_status()

    if result.get("success"):
        if verbose:
            print(f"  ✓ {result['message']}")
    else:
        error_msg = result.get("error", "Unknown error")
        print(f"  ✗ ERROR: {error_msg}")
        return

    # Step 2: Show hotspots
    if verbose:
        print()
        print("Step 2: Detecting hotspots (>70% contested)...")

    hotspots = fw_service.get_hotspots(min_contested_percent=70.0)

    if verbose:
        print(f"  Found {len(hotspots)} hotspots")

        if hotspots:
            print()
            print("  Top Hotspots:")
            print("  " + "-" * 58)
            print(f"  {'System':<20} {'Region':<15} {'Contested':<10} {'Status':<12}")
            print("  " + "-" * 58)

            for hotspot in hotspots[:10]:  # Top 10
                system_name = hotspot.get('solar_system_name', 'Unknown')
                region_name = hotspot.get('region_name', 'Unknown')
                contested_percent = hotspot.get('contested_percent', 0)
                occupier = hotspot.get('occupier_faction_name', 'Unknown')

                print(f"  {system_name:<20} {region_name:<15} {contested_percent:>6.1f}%    {occupier:<12}")

            print("  " + "-" * 58)
    else:
        print(f"FW Tracker: {result['systems_updated']} systems tracked, {len(hotspots)} hotspots")

    # Step 3: Cleanup old snapshots
    if verbose:
        print()
        print("Step 3: Cleaning up old snapshots (>7 days)...")

    cleanup_result = fw_service.cleanup_old_snapshots(days=7)

    if verbose:
        print(f"  ✓ {cleanup_result['message']}")

    # Step 4: Show faction statistics
    if verbose:
        print()
        print("Step 4: Faction Statistics...")

    faction_stats = fw_service.get_faction_statistics()

    if verbose and faction_stats:
        print()
        print("  Faction Control Overview:")
        print("  " + "-" * 80)
        print(f"  {'Faction':<25} {'Systems':<10} {'Contested':<12} {'Vulnerable':<12} {'Avg %':<10}")
        print("  " + "-" * 80)

        for faction_name, stats in faction_stats.items():
            systems = stats['systems_owned']
            contested = stats['systems_contested']
            vulnerable = stats['systems_vulnerable']
            avg_pct = stats['avg_contested_percent']

            print(f"  {faction_name:<25} {systems:<10} {contested:<12} {vulnerable:<12} {avg_pct:>6.1f}%")

        print("  " + "-" * 80)

    if verbose:
        print()
        print("=" * 60)
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Faction Warfare Tracker - Updates FW system status in DB'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    run_fw_tracker(verbose=args.verbose)


if __name__ == "__main__":
    main()
