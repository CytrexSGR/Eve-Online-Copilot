#!/usr/bin/env python3
"""
EVE Co-Pilot Killmail Fetcher

Downloads and processes daily killmail archives from EVE Ref.
Runs as cron job daily at 06:00 UTC to process yesterday's data.

Usage:
    python3 -m jobs.killmail_fetcher                    # Process yesterday
    python3 -m jobs.killmail_fetcher --verbose          # Verbose output
    python3 -m jobs.killmail_fetcher --backfill 7       # Backfill last 7 days
    python3 -m jobs.killmail_fetcher --date 2024-12-06  # Specific date
"""

import sys
import os
import argparse
from datetime import datetime, timedelta, date

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.killmail_service import killmail_service


def parse_date_string(date_str: str) -> date:
    """Parse YYYY-MM-DD string to date object"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def main():
    parser = argparse.ArgumentParser(
        description='Killmail Fetcher - Download and process EVE killmail archives'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--backfill', '-b',
        type=int,
        metavar='N',
        help='Backfill last N days'
    )
    parser.add_argument(
        '--date', '-d',
        type=parse_date_string,
        metavar='YYYY-MM-DD',
        help='Process specific date'
    )

    args = parser.parse_args()

    # Determine date(s) to process
    if args.date:
        # Specific date
        target_date = args.date
        if args.verbose:
            print(f"Processing specific date: {target_date}")
        result = killmail_service.process_date(target_date, verbose=args.verbose)
        results = [result]

    elif args.backfill:
        # Backfill N days
        end_date = datetime.now().date() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=args.backfill - 1)

        if args.verbose:
            print(f"Backfilling {args.backfill} days: {start_date} to {end_date}")

        results = killmail_service.backfill(start_date, end_date, verbose=args.verbose)

    else:
        # Default: process yesterday
        yesterday = datetime.now().date() - timedelta(days=1)

        if args.verbose:
            print(f"Processing yesterday: {yesterday}")

        result = killmail_service.process_date(yesterday, verbose=args.verbose)
        results = [result]

    # Cleanup old data
    if args.verbose:
        print("\nCleaning up old data...")

    cleanup_stats = killmail_service.cleanup_old_data(verbose=args.verbose)

    # Summary
    if args.verbose:
        print("\n" + "=" * 60)
        print("Summary:")
        print("=" * 60)

        for result in results:
            if result.get('success'):
                print(f"  {result['date']}: {result['killmails_processed']} killmails, "
                      f"{result['ship_losses_saved']} ships, {result['item_losses_saved']} items")
            else:
                print(f"  {result['date']}: FAILED - {result.get('error', 'Unknown error')}")

        print(f"\nCleanup: Removed {cleanup_stats['ship_losses_deleted']} ship records, "
              f"{cleanup_stats['item_losses_deleted']} item records (cutoff: {cleanup_stats['cutoff_date']})")
        print("=" * 60)
    else:
        # Compact output for cron logs
        successful = sum(1 for r in results if r.get('success'))
        total_killmails = sum(r.get('killmails_processed', 0) for r in results if r.get('success'))
        total_ships = sum(r.get('ship_losses_saved', 0) for r in results if r.get('success'))
        total_items = sum(r.get('item_losses_saved', 0) for r in results if r.get('success'))

        print(f"Killmail Fetcher: {successful}/{len(results)} dates processed, "
              f"{total_killmails} killmails, {total_ships} ships, {total_items} items saved")


if __name__ == "__main__":
    main()
