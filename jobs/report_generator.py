#!/usr/bin/env python3
"""
Report Pre-Generator
Runs every 6 hours to pre-generate all intelligence reports.
Reports are stored in PostgreSQL for instant retrieval.

Reports generated:
- Pilot Intelligence (24h battle report)
- War Economy Report
- Alliance Wars / Coalitions
- War Profiteering
- Trade Routes
- Strategic Briefing (LLM)
- Alliance Wars Analysis (LLM)
- War Economy Analysis (LLM)
"""

import sys
import os
import time
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from services.stored_reports_service import save_report, get_report_status


def log(msg: str):
    print(f"[{datetime.utcnow().isoformat()}] {msg}")


def generate_pilot_intelligence():
    """Generate pilot intelligence battle report"""
    from services.zkillboard import zkill_live_service

    log("Generating Pilot Intelligence Report...")
    start = time.time()

    try:
        # Force fresh generation (bypass cache)
        result = zkill_live_service._reports_service.build_pilot_intelligence_report_fresh()
        elapsed = time.time() - start

        if result.get("error"):
            log(f"  [WARN] Generated with error: {result['error']} ({elapsed:.1f}s)")
        else:
            kills = result.get("global", {}).get("total_kills", 0)
            log(f"  [OK] Pilot Intelligence ({kills} kills, {elapsed:.1f}s)")

        # Save to database
        save_report('pilot_intelligence', result, elapsed)
        return True
    except Exception as e:
        log(f"  [FAIL] Pilot Intelligence: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_war_economy_report():
    """Generate war economy data report"""
    from services.zkillboard import zkill_live_service

    log("Generating War Economy Report...")
    start = time.time()

    try:
        result = zkill_live_service.get_war_economy_report()
        elapsed = time.time() - start

        if result.get("error"):
            log(f"  [WARN] Generated with error: {result['error']} ({elapsed:.1f}s)")
        else:
            regions = result.get("global_summary", {}).get("total_regions_active", 0)
            log(f"  [OK] War Economy Report ({regions} regions, {elapsed:.1f}s)")

        save_report('war_economy', result, elapsed)
        return True
    except Exception as e:
        log(f"  [FAIL] War Economy Report: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_alliance_wars():
    """Generate alliance wars tracker with coalitions"""
    from services.zkillboard import zkill_live_service

    log("Generating Alliance Wars...")
    start = time.time()

    try:
        # Get wars and coalitions
        wars_data = asyncio.run(zkill_live_service.get_alliance_war_tracker(limit=5))
        coalition_data = asyncio.run(zkill_live_service.detect_coalitions(days=7))
        elapsed = time.time() - start

        # Calculate global summary
        total_conflicts = len(wars_data.get("wars", []))
        all_alliances = set()
        total_kills = 0
        total_isk = 0

        for war in wars_data.get("wars", []):
            all_alliances.add(war["alliance_a_id"])
            all_alliances.add(war["alliance_b_id"])
            total_kills += war["total_kills"]
            total_isk += war["isk_by_a"] + war["isk_by_b"]

        # Transform wars to conflicts
        conflicts = []
        for war in wars_data.get("wars", []):
            winner_name = None
            if war.get("overall_winner") == "a":
                winner_name = war["alliance_a_name"]
            elif war.get("overall_winner") == "b":
                winner_name = war["alliance_b_name"]
            elif war.get("overall_winner") == "contested":
                winner_name = "Contested"

            conflicts.append({
                "alliance_1_id": war["alliance_a_id"],
                "alliance_1_name": war["alliance_a_name"],
                "alliance_2_id": war["alliance_b_id"],
                "alliance_2_name": war["alliance_b_name"],
                "alliance_1_kills": war["kills_by_a"],
                "alliance_1_losses": war["kills_by_b"],
                "alliance_1_isk_destroyed": war["isk_by_a"],
                "alliance_1_isk_lost": war["isk_by_b"],
                "alliance_1_efficiency": float(war["isk_efficiency_a"]),
                "alliance_2_kills": war["kills_by_b"],
                "alliance_2_losses": war["kills_by_a"],
                "alliance_2_isk_destroyed": war["isk_by_b"],
                "alliance_2_isk_lost": war["isk_by_a"],
                "alliance_2_efficiency": float(war["isk_efficiency_b"]),
                "duration_days": war.get("duration_days", 1),
                "primary_regions": [war["system_hotspots"][0]["region_name"]] if war.get("system_hotspots") else ["Unknown"],
                "active_systems": war.get("system_hotspots", []),
                "winner": winner_name,
                "alliance_1_ship_classes": war.get("ship_classes_a", {}),
                "alliance_2_ship_classes": war.get("ship_classes_b", {}),
                "hourly_activity": {},
                "peak_hours": [],
                "avg_kill_value": war["total_isk"] / war["total_kills"] if war["total_kills"] > 0 else 0,
                "alliance_1_biggest_loss": war.get("biggest_loss_a", {"ship_type_id": None, "value": 0}),
                "alliance_2_biggest_loss": war.get("biggest_loss_b", {"ship_type_id": None, "value": 0})
            })

        result = {
            "period": wars_data.get("period", "24h"),
            "global": {
                "active_conflicts": total_conflicts,
                "total_alliances_involved": len(all_alliances),
                "total_kills": total_kills,
                "total_isk_destroyed": total_isk
            },
            "coalitions": coalition_data.get("coalitions", []),
            "unaffiliated_alliances": coalition_data.get("unaffiliated", []),
            "conflicts": conflicts
        }

        wars = len(result.get("conflicts", []))
        log(f"  [OK] Alliance Wars ({wars} conflicts, {elapsed:.1f}s)")

        save_report('alliance_wars', result, elapsed)
        return True
    except Exception as e:
        log(f"  [FAIL] Alliance Wars: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_war_profiteering():
    """Generate war profiteering report"""
    from services.zkillboard import zkill_live_service

    log("Generating War Profiteering...")
    start = time.time()

    try:
        profit_data = zkill_live_service.get_war_profiteering_report(limit=20)
        elapsed = time.time() - start

        # Transform for API response
        items = []
        total_items_destroyed = 0
        max_value_item = None
        max_value = 0

        for item in profit_data.get("items", []):
            market_price = float(item["market_price"])
            opportunity_value = float(item["opportunity_value"])
            qty = item["quantity_destroyed"]

            total_items_destroyed += qty

            if opportunity_value > max_value:
                max_value = opportunity_value
                max_value_item = item["item_name"]

            items.append({
                "item_type_id": item["item_type_id"],
                "item_name": item["item_name"],
                "quantity_destroyed": qty,
                "market_price": market_price,
                "opportunity_value": opportunity_value
            })

        result = {
            "period": profit_data.get("period", "24h"),
            "global": {
                "total_opportunity_value": float(profit_data.get("total_opportunity_value", 0)),
                "total_items_destroyed": total_items_destroyed,
                "unique_item_types": len(items),
                "most_valuable_item": max_value_item or "N/A"
            },
            "items": items
        }

        log(f"  [OK] War Profiteering ({len(items)} items, {elapsed:.1f}s)")
        save_report('war_profiteering', result, elapsed)
        return True
    except Exception as e:
        log(f"  [FAIL] War Profiteering: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_trade_routes():
    """Generate trade route danger map"""
    from services.zkillboard import zkill_live_service

    log("Generating Trade Routes...")
    start = time.time()

    try:
        routes_data = zkill_live_service.get_trade_route_danger_map()
        elapsed = time.time() - start

        # Calculate global summary
        total_routes = len(routes_data.get("routes", []))
        dangerous_count = 0
        total_danger = 0
        gate_camps = 0

        transformed_routes = []
        for route in routes_data.get("routes", []):
            avg_danger = route.get("avg_danger_score", 0)
            total_danger += avg_danger

            if avg_danger >= 5:
                dangerous_count += 1

            transformed_systems = []
            total_kills = 0
            total_isk = 0

            for system in route.get("systems", []):
                kills = system.get("kills_24h", 0)
                isk = system.get("isk_destroyed_24h", 0)
                is_camp = system.get("gate_camp_detected", False)

                total_kills += kills
                total_isk += isk
                if is_camp:
                    gate_camps += 1

                transformed_systems.append({
                    "system_id": system["system_id"],
                    "system_name": system["system_name"],
                    "security_status": system.get("security", 0),
                    "danger_score": system.get("danger_score", 0),
                    "kills_24h": kills,
                    "isk_destroyed_24h": isk,
                    "is_gate_camp": is_camp
                })

            transformed_routes.append({
                "origin_system": route["from_hub"],
                "destination_system": route["to_hub"],
                "jumps": route.get("total_jumps", 0),
                "danger_score": avg_danger,
                "total_kills": total_kills,
                "total_isk_destroyed": total_isk,
                "systems": transformed_systems
            })

        avg_danger_score = total_danger / total_routes if total_routes > 0 else 0

        result = {
            "period": routes_data.get("period", "24h"),
            "global": {
                "total_routes": total_routes,
                "dangerous_routes": dangerous_count,
                "avg_danger_score": avg_danger_score,
                "gate_camps_detected": gate_camps
            },
            "routes": transformed_routes
        }

        log(f"  [OK] Trade Routes ({total_routes} routes, {elapsed:.1f}s)")
        save_report('trade_routes', result, elapsed)
        return True
    except Exception as e:
        log(f"  [FAIL] Trade Routes: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_strategic_briefing():
    """Generate strategic intelligence briefing (LLM)"""
    from services.llm_analysis_service import generate_strategic_briefing as gen_briefing

    log("Generating Strategic Briefing...")
    start = time.time()

    try:
        result = gen_briefing(force_fresh=True)
        elapsed = time.time() - start

        if result.get("error"):
            log(f"  [WARN] Generated with error: {result['error']} ({elapsed:.1f}s)")
        else:
            log(f"  [OK] Strategic Briefing ({elapsed:.1f}s)")

        save_report('strategic_briefing', result, elapsed)
        return True
    except Exception as e:
        log(f"  [FAIL] Strategic Briefing: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_alliance_wars_analysis():
    """Generate alliance wars LLM analysis"""
    from services.llm_analysis_service import generate_alliance_wars_analysis
    from services.stored_reports_service import get_report

    log("Generating Alliance Wars Analysis...")
    start = time.time()

    try:
        # Get the alliance wars data from stored report
        wars_data = get_report('alliance_wars')
        if not wars_data:
            log("  [SKIP] Alliance Wars data not available yet")
            return False

        result = generate_alliance_wars_analysis(wars_data, force_fresh=True)
        elapsed = time.time() - start

        if result.get("error"):
            log(f"  [WARN] Generated with error: {result['error']} ({elapsed:.1f}s)")
        else:
            log(f"  [OK] Alliance Wars Analysis ({elapsed:.1f}s)")

        save_report('alliance_wars_analysis', result, elapsed)
        return True
    except Exception as e:
        log(f"  [FAIL] Alliance Wars Analysis: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_war_economy_analysis():
    """Generate war economy LLM analysis"""
    from services.llm_analysis_service import generate_war_economy_analysis
    from services.stored_reports_service import get_report

    log("Generating War Economy Analysis...")
    start = time.time()

    try:
        # Get the war economy data from stored report
        economy_data = get_report('war_economy')
        if not economy_data:
            log("  [SKIP] War Economy data not available yet")
            return False

        result = generate_war_economy_analysis(economy_data, force_fresh=True)
        elapsed = time.time() - start

        if result.get("error"):
            log(f"  [WARN] Generated with error: {result['error']} ({elapsed:.1f}s)")
        else:
            log(f"  [OK] War Economy Analysis ({elapsed:.1f}s)")

        save_report('war_economy_analysis', result, elapsed)
        return True
    except Exception as e:
        log(f"  [FAIL] War Economy Analysis: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    log("=" * 60)
    log("Starting Report Pre-Generation (6-hour cycle)")
    log("=" * 60)

    # Show current status
    status = get_report_status()
    log("\nCurrent Report Status:")
    for rt, info in status.items():
        age = f"{info['age_hours']}h ago" if info['age_hours'] else "never"
        stale = " [STALE]" if info['stale'] else ""
        log(f"  - {rt}: {age}{stale}")

    total_start = time.time()
    results = []

    # Generate data reports first (they're needed for LLM analysis)
    log("\n--- Data Reports ---")
    results.append(("Pilot Intelligence", generate_pilot_intelligence()))
    results.append(("War Economy Report", generate_war_economy_report()))
    results.append(("War Profiteering", generate_war_profiteering()))
    results.append(("Alliance Wars", generate_alliance_wars()))
    results.append(("Trade Routes", generate_trade_routes()))

    # Generate LLM analyses (depend on data reports)
    log("\n--- LLM Analyses ---")
    results.append(("Strategic Briefing", generate_strategic_briefing()))
    results.append(("Alliance Wars Analysis", generate_alliance_wars_analysis()))
    results.append(("War Economy Analysis", generate_war_economy_analysis()))

    # Summary
    total_time = time.time() - total_start
    success = sum(1 for _, ok in results if ok)
    total = len(results)

    log("\n" + "=" * 60)
    log(f"Report Pre-Generation Complete: {success}/{total} successful ({total_time:.1f}s)")

    for name, ok in results:
        status = "OK" if ok else "FAILED"
        log(f"  - {name}: {status}")

    log("=" * 60)

    if success < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
