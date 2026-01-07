#!/usr/bin/env python3
"""
EVE Co-Pilot Batch Calculator

Berechnet alle Manufacturing-Opportunities und speichert sie in der Datenbank.
Läuft als Cronjob alle 5 Minuten.

Workflow:
1. Marktpreise von ESI abrufen und in market_prices speichern
2. Alle T1 Blueprints durchrechnen
3. Ergebnisse in manufacturing_opportunities speichern
4. Frontend liest nur aus DB (schnell!)

Usage:
    python3 -m jobs.batch_calculator
    python3 -m jobs.batch_calculator --verbose
"""

import sys
import os
import time
import argparse
from datetime import datetime
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db_connection
from src.market_service import market_service
from src.production_simulator import ProductionSimulator
from src.material_classifier import material_classifier
from src.esi_client import esi_client
from config import REGIONS

# Region mapping für DB
REGION_MAP = {
    10000002: ('the_forge', 'jita'),
    10000043: ('domain', 'amarr'),
    10000030: ('heimatar', 'rens'),
    10000032: ('sinq_laison', 'dodixie'),
    10000042: ('metropolis', 'hek'),
}


def get_all_t1_blueprints() -> List[Dict]:
    """Holt alle T1 Blueprints aus der SDE"""
    EXCLUDED_TYPE_IDS = {47466, 3756, 42685, 30842, 33513, 33515}

    with get_db_connection() as conn:
        with conn.cursor() as cur:
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
            ''')

            results = []
            for row in cur.fetchall():
                if row[1] not in EXCLUDED_TYPE_IDS:
                    results.append({
                        "blueprint_id": row[0],
                        "product_id": row[1],
                        "product_name": row[2],
                        "group_name": row[3],
                        "category_name": row[4]
                    })
            return results


def fetch_and_store_prices(verbose: bool = False) -> int:
    """
    Holt Marktpreise von ESI und speichert sie in der DB.
    Nutzt den bestehenden market_service für globale Preise.
    """
    if verbose:
        print("  Fetching market prices from ESI...")

    # Update global prices (1 API call)
    result = market_service.update_global_prices()
    if "error" in result:
        print(f"  ERROR: {result['error']}")
        return 0

    # Load to memory - WICHTIG für ProductionSimulator
    loaded = market_service.load_prices_to_memory()
    if verbose:
        print(f"  Loaded {loaded:,} prices to memory")

    updated = result.get('items_updated', 0)
    if verbose:
        print(f"  Updated {updated:,} global prices")

    return updated


def get_material_prices_all_regions(type_ids: List[int]) -> Dict[int, Dict[str, float]]:
    """
    Holt Preise für alle Materials in allen Regionen.
    Returns: {type_id: {'jita': price, 'amarr': price, ...}}
    """
    prices = {}

    for type_id in type_ids:
        prices[type_id] = {}
        for region_name, region_id in REGIONS.items():
            # Nutze cached prices wo möglich
            cached = market_service.get_price_from_memory(type_id, region_name)
            if cached and cached.get('sell'):
                prices[type_id][region_name] = cached['sell']
            else:
                prices[type_id][region_name] = None

    return prices


def calculate_opportunity(bp: Dict, simulator: ProductionSimulator, me: int = 10) -> Optional[Dict]:
    """Berechnet eine einzelne Manufacturing Opportunity"""
    try:
        # Quick profit check using cached adjusted_price
        result = simulator.quick_profit_check(
            type_id=bp["product_id"],
            runs=1,
            me=me
        )

        if not result:
            return None

        margin = result.get("margin_percent", 0)
        if margin <= 0:
            return None

        # Get BOM and difficulty
        bom = simulator.get_bom(bp["product_id"], runs=1, me=me)
        if not bom:
            return None

        manufacturability = material_classifier.get_manufacturability_score(bom)

        # Use the values from quick_profit_check (based on adjusted_price)
        material_cost = result.get("material_cost", 0)
        sell_price = result.get("product_price", 0) * result.get("output_quantity", 1)  # revenue
        profit = result.get("profit", 0)
        roi = margin

        if material_cost <= 0:
            return None

        return {
            "product_id": bp["product_id"],
            "blueprint_id": bp["blueprint_id"],
            "product_name": bp["product_name"],
            "category": bp["category_name"],
            "group_name": bp["group_name"],
            "difficulty": manufacturability["score"],

            # For now, use same price for all regions (adjusted_price is global)
            "material_cost_jita": material_cost,
            "material_cost_amarr": material_cost,
            "material_cost_rens": material_cost,
            "material_cost_dodixie": material_cost,
            "material_cost_hek": material_cost,
            "cheapest_material_cost": material_cost,
            "cheapest_material_region": "the_forge",

            "sell_price_jita": sell_price,
            "sell_price_amarr": sell_price,
            "sell_price_rens": sell_price,
            "sell_price_dodixie": sell_price,
            "sell_price_hek": sell_price,
            "best_sell_price": sell_price,
            "best_sell_region": "the_forge",

            # Calculated
            "profit": profit,
            "roi": roi,
            "me_level": me
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


def save_opportunities_to_db(opportunities: List[Dict], verbose: bool = False) -> int:
    """Speichert alle Opportunities in der DB"""
    if not opportunities:
        return 0

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Truncate and insert fresh (simpler than upsert for batch)
            cur.execute("TRUNCATE TABLE manufacturing_opportunities")

            insert_sql = """
                INSERT INTO manufacturing_opportunities (
                    product_id, blueprint_id, product_name, category, group_name, difficulty,
                    material_cost_jita, material_cost_amarr, material_cost_rens,
                    material_cost_dodixie, material_cost_hek,
                    cheapest_material_cost, cheapest_material_region,
                    sell_price_jita, sell_price_amarr, sell_price_rens,
                    sell_price_dodixie, sell_price_hek,
                    best_sell_price, best_sell_region,
                    profit, roi, me_level, updated_at
                ) VALUES (
                    %(product_id)s, %(blueprint_id)s, %(product_name)s, %(category)s,
                    %(group_name)s, %(difficulty)s,
                    %(material_cost_jita)s, %(material_cost_amarr)s, %(material_cost_rens)s,
                    %(material_cost_dodixie)s, %(material_cost_hek)s,
                    %(cheapest_material_cost)s, %(cheapest_material_region)s,
                    %(sell_price_jita)s, %(sell_price_amarr)s, %(sell_price_rens)s,
                    %(sell_price_dodixie)s, %(sell_price_hek)s,
                    %(best_sell_price)s, %(best_sell_region)s,
                    %(profit)s, %(roi)s, %(me_level)s, NOW()
                )
            """

            for opp in opportunities:
                cur.execute(insert_sql, opp)

            conn.commit()

    return len(opportunities)


def run_batch_calculation(me: int = 10, verbose: bool = False) -> Dict:
    """
    Führt die komplette Batch-Berechnung durch.
    """
    start_time = time.time()

    if verbose:
        print("=" * 60)
        print("EVE Co-Pilot Batch Calculator")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()

    # Step 1: Fetch prices
    if verbose:
        print("Step 1: Updating market prices...")
    prices_updated = fetch_and_store_prices(verbose)

    # Step 2: Get all blueprints
    if verbose:
        print()
        print("Step 2: Loading blueprints...")
    blueprints = get_all_t1_blueprints()
    if verbose:
        print(f"  Found {len(blueprints):,} T1 blueprints")

    # Step 3: Calculate all opportunities
    if verbose:
        print()
        print("Step 3: Calculating opportunities...")

    simulator = ProductionSimulator(source='cache')
    opportunities = []
    errors = 0

    for i, bp in enumerate(blueprints):
        if verbose and i % 100 == 0:
            print(f"  Processing {i}/{len(blueprints)}...", end='\r')

        opp = calculate_opportunity(bp, simulator, me)
        if opp:
            opportunities.append(opp)
        else:
            errors += 1

    if verbose:
        print(f"  Calculated {len(opportunities):,} profitable opportunities")
        print(f"  Skipped {errors:,} (no profit or missing data)")

    # Step 4: Save to DB
    if verbose:
        print()
        print("Step 4: Saving to database...")

    saved = save_opportunities_to_db(opportunities, verbose)

    elapsed = time.time() - start_time

    if verbose:
        print(f"  Saved {saved:,} opportunities")
        print()
        print("=" * 60)
        print(f"Completed in {elapsed:.2f} seconds")
        print("=" * 60)

    return {
        "timestamp": datetime.now().isoformat(),
        "blueprints_scanned": len(blueprints),
        "opportunities_found": len(opportunities),
        "saved_to_db": saved,
        "elapsed_seconds": round(elapsed, 2)
    }


def main():
    parser = argparse.ArgumentParser(
        description='Batch Calculator - Updates manufacturing opportunities in DB'
    )
    parser.add_argument(
        '--me',
        type=int,
        default=10,
        help='Material Efficiency level (default: 10)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    result = run_batch_calculation(
        me=args.me,
        verbose=args.verbose
    )

    if not args.verbose:
        print(f"Batch complete: {result['opportunities_found']} opportunities in {result['elapsed_seconds']}s")


if __name__ == "__main__":
    main()
