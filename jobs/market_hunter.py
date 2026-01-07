#!/usr/bin/env python3
"""
EVE Co-Pilot Market Hunter

Automated profitable blueprint scanner with Discord notifications.

Workflow:
1. Update market price cache (1 API call)
2. Pre-scan all T1 blueprints using cached prices (fast)
3. Live-validate top candidates with real Jita prices (accurate)
4. Filter by ROI > 15% AND profit > 500,000 ISK
5. Send Discord notification if opportunities found

Usage:
    python3 -m jobs.market_hunter
    python3 -m jobs.market_hunter --dry-run
    python3 -m jobs.market_hunter --min-roi 20 --min-profit 1000000
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime
from typing import List, Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db_connection
from src.market_service import market_service
from src.production_simulator import ProductionSimulator
from src.notification_service import notification_service
from src.material_classifier import material_classifier, MaterialSource
from src.esi_client import esi_client
from config import (
    HUNTER_MIN_ROI,
    HUNTER_MIN_PROFIT,
    HUNTER_TOP_CANDIDATES,
    HUNTER_DEFAULT_ME,
    REGIONS
)


def get_all_t1_blueprints() -> List[Dict]:
    """Get all T1 blueprints from SDE (same as bulk_scanner)"""

    # Blueprints that exist in SDE but are not obtainable in-game
    # SoCT ships, event shuttles, special items
    EXCLUDED_TYPE_IDS = {
        # SoCT Event Ships (blueprints don't exist)
        47466,  # Praxis
        3756,   # Gnosis
        42685,  # Sunesis
        # Special Shuttles (not manufacturable)
        30842,  # InterBus Shuttle
        33513,  # Leopard
        33515,  # Victorieux Luxury Yacht (if exists)
        # Civilian modules (tutorial items, not profitable)
        # Data Interfaces (require rare components from exploration)
    }

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT DISTINCT
                    iap."typeID" as blueprint_id,
                    iap."productTypeID" as product_id,
                    it."typeName" as product_name,
                    ig."groupName" as group_name,
                    ic."categoryName" as category_name,
                    (SELECT COUNT(*) FROM "industryActivityMaterials" iam
                     WHERE iam."typeID" = iap."typeID" AND iam."activityID" = 1) as material_count
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
                product_id = row[1]
                material_count = row[5]

                # Skip excluded items
                if product_id in EXCLUDED_TYPE_IDS:
                    continue

                # Skip items with less than 2 materials (likely fake/event blueprints)
                if material_count < 2:
                    continue

                results.append({
                    "blueprint_id": row[0],
                    "product_id": product_id,
                    "product_name": row[2],
                    "group_name": row[3],
                    "category_name": row[4]
                })

            return results


def run_market_hunter(
    min_roi: float = None,
    min_profit: float = None,
    top_candidates: int = None,
    me: int = None,
    max_difficulty: int = 2,
    dry_run: bool = False,
    verbose: bool = True,
    quick_mode: bool = False
) -> Dict:
    """
    Run the Market Hunter scan.

    Args:
        min_roi: Minimum ROI percentage (default from config)
        min_profit: Minimum profit in ISK (default from config)
        top_candidates: Number of candidates for live validation
        me: Material Efficiency level
        max_difficulty: Max material difficulty (1=minerals only, 2=+PI/salvage, 3=+moon, 4=exploration)
        dry_run: If True, don't send Discord notifications
        verbose: Print progress to console
        quick_mode: If True, skip live validation (much faster, uses cached prices only)

    Returns:
        Dict with results and statistics
    """
    # Use defaults from config
    min_roi = min_roi or HUNTER_MIN_ROI
    min_profit = min_profit or HUNTER_MIN_PROFIT
    top_candidates = top_candidates or HUNTER_TOP_CANDIDATES
    me = me or HUNTER_DEFAULT_ME

    start_time = time.time()
    api_calls = 0

    difficulty_names = {1: "minerals only", 2: "minerals+PI+salvage", 3: "+moon", 4: "+exploration"}
    diff_name = difficulty_names.get(max_difficulty, f"level {max_difficulty}")

    if verbose:
        print("=" * 60)
        print("EVE Co-Pilot Market Hunter")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()
        print(f"Parameters: ROI >= {min_roi}%, Profit >= {min_profit:,.0f} ISK, ME={me}")
        print(f"Material Filter: {diff_name}")
        print()

    # Step 1: Update market price cache
    if verbose:
        print("Step 1: Updating market price cache...")

    cache_result = market_service.update_global_prices()

    if "error" in cache_result:
        error_msg = f"Cache update failed: {cache_result['error']}"
        if verbose:
            print(f"  ERROR: {error_msg}")
        return {"error": error_msg}

    api_calls += 1
    if verbose:
        print(f"  Updated {cache_result.get('items_updated', 0):,} prices")

    # Load to memory for fast access
    market_service.load_prices_to_memory()

    # Step 2: Pre-scan all blueprints with cached prices
    if verbose:
        print()
        print("Step 2: Pre-scanning all T1 blueprints (cache mode)...")

    blueprints = get_all_t1_blueprints()
    cache_simulator = ProductionSimulator(source='cache')

    cache_results = []
    filtered_out = 0

    for bp in blueprints:
        result = cache_simulator.quick_profit_check(
            type_id=bp["product_id"],
            runs=1,
            me=me
        )
        if result and result["margin_percent"] > 0:
            # Check material difficulty
            bom = cache_simulator.get_bom(bp["product_id"], runs=1, me=me)
            manufacturability = material_classifier.get_manufacturability_score(bom)

            if manufacturability["score"] > max_difficulty:
                filtered_out += 1
                continue

            result["group_name"] = bp["group_name"]
            result["category_name"] = bp["category_name"]
            result["difficulty"] = manufacturability["score"]
            result["material_sources"] = manufacturability["sources"]
            result["warnings"] = manufacturability["warnings"]
            cache_results.append(result)

    # Sort by margin and take top candidates
    cache_results.sort(key=lambda x: x["margin_percent"], reverse=True)
    candidates = cache_results[:top_candidates]

    if verbose:
        print(f"  Scanned {len(blueprints):,} blueprints")
        print(f"  Filtered out {filtered_out} (difficult materials)")
        print(f"  Found {len(cache_results):,} manufacturable profitable items")
        if quick_mode:
            print(f"  QUICK MODE: Using cached prices (no live validation)")
        else:
            print(f"  Selected top {len(candidates)} candidates for live validation")

    # Quick mode: skip live validation, use cache results directly
    if quick_mode:
        validated_results = []
        for candidate in candidates:
            validated_results.append({
                "type_id": candidate["type_id"],
                "name": candidate["name"],
                "group_name": candidate.get("group_name", "Unknown"),
                "category_name": candidate.get("category_name", "Unknown"),
                "material_cost": candidate.get("material_cost", 0),
                "sell_price": candidate.get("sell_price", 0),
                "profit": candidate.get("profit", 0),
                "margin_percent": candidate.get("margin_percent", 0),
                "investment": candidate.get("material_cost", 0),
                "me": me,
                "difficulty": candidate.get("difficulty", 0),
                "material_sources": candidate.get("material_sources", {}),
                "material_warnings": candidate.get("warnings", [])
            })
        api_abort = False
    else:
        # Step 3: Live validation with real Jita prices
        if verbose:
            print()
            print("Step 3: Live-validating candidates with Jita prices...")

        live_simulator = ProductionSimulator(source='live')
        validated_results = []
        api_abort = False

        for i, candidate in enumerate(candidates):
            # Safety check: abort if rate limits are critical
            if not esi_client.is_safe_to_continue():
                rate_status = esi_client.get_rate_limit_status()
                error_msg = f"ESI rate limit critical! Errors remaining: {rate_status['error_limit_remain']}"
                if verbose:
                    print(f"\n  ABORT: {error_msg}")

                # Send emergency notification
                notification_service.send_discord_webhook(
                    embeds=[{
                        "title": "Market Hunter ABORTED",
                        "description": error_msg,
                        "color": 0xFF0000,
                        "fields": [
                            {"name": "Candidates Processed", "value": str(i), "inline": True},
                            {"name": "Error Limit", "value": str(rate_status['error_limit_remain']), "inline": True}
                        ]
                    }]
                )
                api_abort = True
                break

            if verbose:
                print(f"  Validating {i+1}/{len(candidates)}: {candidate['name'][:40]}", end='\r')

            try:
                # Full simulation with live prices
                result = live_simulator.simulate_build(
                    type_id=candidate["type_id"],
                    runs=1,
                    me=me
                )

                if "error" not in result:
                    validated_results.append({
                        "type_id": candidate["type_id"],
                        "name": candidate["name"],
                        "group_name": candidate.get("group_name", "Unknown"),
                        "category_name": candidate.get("category_name", "Unknown"),
                        "material_cost": result["financials"]["total_build_cost"],
                        "sell_price": result["product"]["unit_sell_price"],
                        "profit": result["financials"]["profit"],
                        "margin_percent": result["financials"]["margin_percent"],
                        "investment": result["financials"]["cash_to_invest"],
                        "me": me,
                        "difficulty": candidate.get("difficulty", 0),
                        "material_sources": candidate.get("material_sources", {}),
                        "material_warnings": candidate.get("warnings", [])
                    })
            except Exception as e:
                if verbose:
                    print(f"  Error validating {candidate['name']}: {e}")

        if verbose:
            if api_abort:
                print(f"  Validation aborted early due to rate limits")
            else:
                print(f"  Validated {len(validated_results)} candidates                    ")

            # Show rate limit status
            rate_status = esi_client.get_rate_limit_status()
            print(f"  Rate limits - Errors: {rate_status['error_limit_remain']}/100, "
                  f"Requests: {rate_status['total_requests']}")

    # Step 4: Filter by ROI and profit thresholds
    if verbose:
        print()
        print(f"Step 4: Filtering (ROI >= {min_roi}%, Profit >= {min_profit:,.0f} ISK)...")

    opportunities = [
        r for r in validated_results
        if r["margin_percent"] >= min_roi and r["profit"] >= min_profit
    ]

    # Sort by profit descending
    opportunities.sort(key=lambda x: x["profit"], reverse=True)

    if verbose:
        print(f"  Found {len(opportunities)} opportunities matching criteria")

    elapsed = time.time() - start_time

    # Build result summary
    result = {
        "timestamp": datetime.now().isoformat(),
        "parameters": {
            "min_roi": min_roi,
            "min_profit": min_profit,
            "me": me,
            "top_candidates": top_candidates
        },
        "statistics": {
            "total_scanned": len(blueprints),
            "cache_profitable": len(cache_results),
            "live_validated": len(validated_results),
            "opportunities_found": len(opportunities),
            "scan_time": round(elapsed, 2),
            "api_calls": api_calls,
            "api_abort": api_abort,
            "rate_limit_status": esi_client.get_rate_limit_status()
        },
        "opportunities": opportunities
    }

    # Step 5: Send Discord notification
    if opportunities:
        if verbose:
            print()
            print("Step 5: Sending Discord notification...")
            print()
            print("-" * 70)
            print(f"{'#':>3} {'Name':<30} {'Profit':>15} {'ROI':>8}")
            print("-" * 70)

            for i, opp in enumerate(opportunities[:10], 1):
                print(f"{i:>3} {opp['name'][:30]:<30} {opp['profit']:>15,.0f} {opp['margin_percent']:>7.1f}%")

            print("-" * 70)

        if not dry_run:
            notify_result = notification_service.send_bulk_profit_alert(
                opportunities=opportunities,
                scan_stats={
                    "total_scanned": len(blueprints),
                    "scan_time": elapsed,
                    "api_calls": api_calls
                }
            )

            if "error" in notify_result:
                if verbose:
                    print(f"  Discord notification failed: {notify_result['error']}")
                result["notification"] = {"error": notify_result["error"]}
            else:
                if verbose:
                    print(f"  Discord notification sent successfully!")
                result["notification"] = {"success": True}
        else:
            if verbose:
                print("  [DRY RUN] Skipping Discord notification")
            result["notification"] = {"dry_run": True}
    else:
        if verbose:
            print()
            print("No opportunities found matching criteria.")
        result["notification"] = {"skipped": "No opportunities to report"}

    if verbose:
        print()
        print("=" * 60)
        print(f"Scan completed in {elapsed:.2f} seconds")
        print(f"API calls made: {api_calls}")
        print("=" * 60)

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Market Hunter - Automated profitable blueprint scanner'
    )
    parser.add_argument(
        '--min-roi',
        type=float,
        default=HUNTER_MIN_ROI,
        help=f'Minimum ROI percentage (default: {HUNTER_MIN_ROI}%)'
    )
    parser.add_argument(
        '--min-profit',
        type=float,
        default=HUNTER_MIN_PROFIT,
        help=f'Minimum profit in ISK (default: {HUNTER_MIN_PROFIT:,.0f})'
    )
    parser.add_argument(
        '--top',
        type=int,
        default=HUNTER_TOP_CANDIDATES,
        help=f'Number of candidates for live validation (default: {HUNTER_TOP_CANDIDATES})'
    )
    parser.add_argument(
        '--me',
        type=int,
        default=HUNTER_DEFAULT_ME,
        help=f'Material Efficiency level (default: {HUNTER_DEFAULT_ME})'
    )
    parser.add_argument(
        '--max-difficulty',
        type=int,
        default=2,
        choices=[1, 2, 3, 4],
        help='Max material difficulty: 1=minerals, 2=+PI/salvage, 3=+moon, 4=+exploration (default: 2)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without sending Discord notifications'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Quiet mode (minimal output)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Save results to JSON file'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON to stdout (for API usage)'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick mode: skip live validation, use cached prices only (much faster)'
    )

    args = parser.parse_args()

    # If JSON mode, run quietly and output JSON
    if args.json:
        result = run_market_hunter(
            min_roi=args.min_roi,
            min_profit=args.min_profit,
            top_candidates=args.top,
            me=args.me,
            max_difficulty=args.max_difficulty,
            dry_run=True,  # Don't send Discord in JSON mode
            verbose=False,
            quick_mode=args.quick
        )

        # Format for frontend
        api_result = {
            "scan_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "results": [
                {
                    "blueprint_id": opp["type_id"],
                    "product_id": opp["type_id"],
                    "product_name": opp["name"],
                    "category": opp.get("category_name", "Unknown"),
                    "difficulty": opp.get("difficulty", 1),
                    "material_cost": opp["material_cost"],
                    "sell_price": opp["sell_price"],
                    "profit": opp["profit"],
                    "roi": opp["margin_percent"],
                    "volume_available": 0  # Would need additional API call
                }
                for opp in result.get("opportunities", [])
            ],
            "summary": {
                "total_scanned": result["statistics"]["total_scanned"],
                "profitable": result["statistics"]["opportunities_found"],
                "avg_roi": sum(o["margin_percent"] for o in result.get("opportunities", [])) / len(result.get("opportunities", [1])) if result.get("opportunities") else 0
            }
        }

        print(json.dumps(api_result))
        sys.exit(0)

    result = run_market_hunter(
        min_roi=args.min_roi,
        min_profit=args.min_profit,
        top_candidates=args.top,
        me=args.me,
        max_difficulty=args.max_difficulty,
        dry_run=args.dry_run,
        verbose=not args.quiet
    )

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Results saved to: {args.output}")

    # Exit with error code if scan failed
    if "error" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()
