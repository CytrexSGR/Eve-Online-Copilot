#!/usr/bin/env python3
"""
EVE Co-Pilot Bulk Blueprint Scanner

Scans all T1 blueprints and calculates profitability using cached market prices.
Uses only ONE ESI API call for the entire scan.

Usage:
    python3 -m jobs.bulk_scanner
    python3 -m jobs.bulk_scanner --top 100
    python3 -m jobs.bulk_scanner --min-margin 10 --output results.json
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db_connection
from src.market_service import market_service
from src.production_simulator import ProductionSimulator


def get_all_t1_blueprints() -> List[Dict]:
    """
    Get all T1 blueprints from the SDE.

    Returns list of dicts with blueprint_id, product_id, product_name
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get all manufacturing blueprints that produce items
            # Filter for T1 items (metaGroupID = 1 or NULL, techLevel = 1)
            cur.execute('''
                SELECT DISTINCT
                    iap."typeID" as blueprint_id,
                    iap."productTypeID" as product_id,
                    it."typeName" as product_name,
                    ig."groupName" as group_name,
                    ic."categoryName" as category_name
                FROM "industryActivityProducts" iap
                JOIN "invTypes" it ON it."typeID" = iap."productTypeID"
                JOIN "invGroups" ig ON ig."groupID" = it."groupID"
                JOIN "invCategories" ic ON ic."categoryID" = ig."categoryID"
                LEFT JOIN "invMetaTypes" imt ON imt."typeID" = iap."productTypeID"
                WHERE iap."activityID" = 1
                AND it."published" = 1
                AND (imt."metaGroupID" IS NULL OR imt."metaGroupID" = 1)
                AND ic."categoryName" NOT IN ('Blueprint', 'Skill', 'Implant', 'Apparel')
                ORDER BY ic."categoryName", ig."groupName", it."typeName"
            ''')

            results = []
            for row in cur.fetchall():
                results.append({
                    "blueprint_id": row[0],
                    "product_id": row[1],
                    "product_name": row[2],
                    "group_name": row[3],
                    "category_name": row[4]
                })

            return results


def scan_all_blueprints(
    blueprints: List[Dict],
    runs: int = 1,
    me: int = 10,
    min_margin: float = None,
    min_profit: float = None,
    progress_callback=None
) -> List[Dict]:
    """
    Scan all blueprints and calculate profitability.

    Args:
        blueprints: List of blueprint dicts from get_all_t1_blueprints()
        runs: Number of runs to simulate
        me: Material Efficiency level
        min_margin: Filter for minimum margin percent
        min_profit: Filter for minimum profit ISK
        progress_callback: Optional callback for progress updates

    Returns:
        List of profitable blueprints sorted by margin
    """
    simulator = ProductionSimulator(source='cache')
    results = []
    total = len(blueprints)
    errors = 0

    for i, bp in enumerate(blueprints):
        if progress_callback and i % 100 == 0:
            progress_callback(i, total)

        try:
            result = simulator.quick_profit_check(
                type_id=bp["product_id"],
                runs=runs,
                me=me
            )

            if result:
                # Add category/group info
                result["group_name"] = bp["group_name"]
                result["category_name"] = bp["category_name"]

                # Apply filters
                if min_margin and result["margin_percent"] < min_margin:
                    continue
                if min_profit and result["profit"] < min_profit:
                    continue

                results.append(result)
        except Exception as e:
            errors += 1
            if errors < 10:
                print(f"Error scanning {bp['product_name']}: {e}")

    # Sort by margin descending
    results.sort(key=lambda x: x["margin_percent"], reverse=True)

    return results


def run_bulk_scan(
    top_n: int = 50,
    runs: int = 1,
    me: int = 10,
    min_margin: float = None,
    min_profit: float = None,
    output_file: str = None,
    verbose: bool = True
) -> Dict:
    """
    Run a complete bulk scan with a single API call.

    Args:
        top_n: Number of top results to return
        runs: Production runs to simulate
        me: Material Efficiency level
        min_margin: Minimum margin filter
        min_profit: Minimum profit filter
        output_file: Optional JSON output file
        verbose: Print progress to console

    Returns:
        Dict with scan results and statistics
    """
    start_time = time.time()

    if verbose:
        print("=" * 60)
        print("EVE Co-Pilot Bulk Blueprint Scanner")
        print("=" * 60)
        print()

    # Step 1: Update global prices (1 API call)
    if verbose:
        print("Step 1: Updating global market prices (single API call)...")

    cache_result = market_service.ensure_cache_fresh(max_age_seconds=3600)

    if "error" in cache_result:
        print(f"ERROR: {cache_result['error']}")
        return {"error": cache_result["error"]}

    if cache_result.get("cached"):
        if verbose:
            print(f"  Using cached prices ({int(cache_result.get('cache_age_seconds', 0))}s old)")
    else:
        if verbose:
            print(f"  Updated {cache_result.get('items_updated', 0):,} prices")

    # Load prices to memory for fast access
    count = market_service.load_prices_to_memory()
    if verbose:
        print(f"  Loaded {count:,} prices to memory")
        print()

    # Step 2: Get all T1 blueprints
    if verbose:
        print("Step 2: Loading T1 blueprint definitions from SDE...")

    blueprints = get_all_t1_blueprints()

    if verbose:
        print(f"  Found {len(blueprints):,} T1 blueprints")
        print()

    # Step 3: Scan all blueprints
    if verbose:
        print(f"Step 3: Scanning blueprints (ME={me}, runs={runs})...")

    def progress_callback(current, total):
        if verbose:
            pct = current / total * 100
            print(f"  Progress: {current:,}/{total:,} ({pct:.1f}%)", end='\r')

    results = scan_all_blueprints(
        blueprints,
        runs=runs,
        me=me,
        min_margin=min_margin,
        min_profit=min_profit,
        progress_callback=progress_callback
    )

    if verbose:
        print(f"  Scanned {len(blueprints):,} blueprints                    ")
        print(f"  Found {len(results):,} profitable items")
        print()

    elapsed = time.time() - start_time

    # Step 4: Format results
    top_results = results[:top_n]

    scan_result = {
        "timestamp": datetime.now().isoformat(),
        "parameters": {
            "runs": runs,
            "me": me,
            "min_margin": min_margin,
            "min_profit": min_profit
        },
        "statistics": {
            "total_blueprints_scanned": len(blueprints),
            "profitable_items": len(results),
            "scan_time_seconds": round(elapsed, 2),
            "api_calls_made": 1 if not cache_result.get("cached") else 0
        },
        "top_results": top_results
    }

    # Output results
    if verbose:
        print(f"Step 4: Top {len(top_results)} most profitable items:")
        print("-" * 80)
        print(f"{'#':>3} {'Name':<35} {'Cost':>12} {'Price':>12} {'Margin':>8}")
        print("-" * 80)

        for i, item in enumerate(top_results, 1):
            print(f"{i:>3} {item['name'][:35]:<35} {item['material_cost']:>12,.0f} {item['product_price']:>12,.0f} {item['margin_percent']:>7.1f}%")

        print("-" * 80)
        print()
        print(f"Scan completed in {elapsed:.2f} seconds")
        print(f"API calls made: {scan_result['statistics']['api_calls_made']}")

    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(scan_result, f, indent=2)
        if verbose:
            print(f"Results saved to: {output_file}")

    return scan_result


def main():
    parser = argparse.ArgumentParser(
        description='Bulk scan all T1 blueprints for profitability'
    )
    parser.add_argument(
        '--top', '-n',
        type=int,
        default=50,
        help='Number of top results to show (default: 50)'
    )
    parser.add_argument(
        '--runs', '-r',
        type=int,
        default=1,
        help='Number of production runs (default: 1)'
    )
    parser.add_argument(
        '--me',
        type=int,
        default=10,
        help='Material Efficiency level 0-10 (default: 10)'
    )
    parser.add_argument(
        '--min-margin',
        type=float,
        help='Minimum margin percent filter'
    )
    parser.add_argument(
        '--min-profit',
        type=float,
        help='Minimum profit ISK filter'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output JSON file path'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Quiet mode (no console output)'
    )

    args = parser.parse_args()

    run_bulk_scan(
        top_n=args.top,
        runs=args.runs,
        me=args.me,
        min_margin=args.min_margin,
        min_profit=args.min_profit,
        output_file=args.output,
        verbose=not args.quiet
    )


if __name__ == "__main__":
    main()
