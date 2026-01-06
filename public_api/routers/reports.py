"""
Reports API Router
Serves cached combat intelligence reports from Redis
"""

from fastapi import APIRouter, HTTPException
from typing import Dict
import redis
from services.zkillboard import zkill_live_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/battle-24h")
async def get_battle_report() -> Dict:
    """
    24-Hour Battle Report by Region

    Returns comprehensive combat statistics for the last 24 hours,
    organized by region with top systems, ships, and destroyed items.

    Cache: 10 minutes
    """
    try:
        report = zkill_live_service.get_24h_battle_report()
        return report
    except redis.RedisError as e:
        raise HTTPException(
            status_code=503,
            detail="Redis connection error. Reports temporarily unavailable."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate battle report"
        )


@router.get("/war-profiteering")
async def get_war_profiteering() -> Dict:
    """
    War Profiteering Daily Digest

    Identifies market opportunities based on destroyed items in combat.
    Shows items with highest market value destroyed in last 24 hours.

    Cache: 1 hour (refreshed daily at 06:00 UTC)
    """
    try:
        # Get original profiteering data
        profit_data = zkill_live_service.get_war_profiteering_report(limit=20)

        # Convert Decimal to float for JSON serialization
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

        return {
            "period": profit_data.get("period", "24h"),
            "global": {
                "total_opportunity_value": float(profit_data.get("total_opportunity_value", 0)),
                "total_items_destroyed": total_items_destroyed,
                "unique_item_types": len(items),
                "most_valuable_item": max_value_item or "N/A"
            },
            "items": items
        }
    except redis.RedisError as e:
        raise HTTPException(
            status_code=503,
            detail="Redis connection error. Reports temporarily unavailable."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate war profiteering report"
        )


@router.get("/alliance-wars")
async def get_alliance_wars() -> Dict:
    """
    Alliance War Tracker

    Tracks active alliance conflicts with kill/death ratios and ISK efficiency.
    Shows top 5 most active alliance wars in last 24 hours.

    Cache: 30 minutes
    """
    try:
        # Get original wars data
        wars_data = await zkill_live_service.get_alliance_war_tracker(limit=5)

        # Calculate global summary
        total_conflicts = len(wars_data.get("wars", []))
        all_alliances = set()
        total_kills = 0
        total_isk = 0

        for war in wars_data.get("wars", []):
            all_alliances.add(war["alliance_a_id"])
            all_alliances.add(war["alliance_b_id"])
            total_kills += war["total_kills"]
            total_isk += war["isk_destroyed_by_a"] + war["isk_destroyed_by_b"]

        # Transform wars to conflicts with correct field names
        conflicts = []
        for war in wars_data.get("wars", []):
            conflicts.append({
                "alliance_1_id": war["alliance_a_id"],
                "alliance_1_name": war["alliance_a_name"],
                "alliance_2_id": war["alliance_b_id"],
                "alliance_2_name": war["alliance_b_name"],
                "alliance_1_kills": war["kills_by_a"],
                "alliance_1_losses": war["kills_by_b"],
                "alliance_1_isk_destroyed": war["isk_destroyed_by_a"],
                "alliance_1_isk_lost": war["isk_destroyed_by_b"],
                "alliance_1_efficiency": war["isk_efficiency_a"],
                "alliance_2_kills": war["kills_by_b"],
                "alliance_2_losses": war["kills_by_a"],
                "alliance_2_isk_destroyed": war["isk_destroyed_by_b"],
                "alliance_2_isk_lost": war["isk_destroyed_by_a"],
                "alliance_2_efficiency": 100 - war["isk_efficiency_a"] if war["isk_efficiency_a"] <= 100 else 0,
                "duration_days": 1,  # TODO: Calculate from killmail timestamps
                "primary_regions": ["Unknown"],  # TODO: Get from system data
                "active_systems": [],  # TODO: Get top systems from killmails
                "winner": war["alliance_a_name"] if war["winner"] == "a" else war["alliance_b_name"] if war["winner"] == "b" else None
            })

        return {
            "period": wars_data.get("period", "24h"),
            "global": {
                "active_conflicts": total_conflicts,
                "total_alliances_involved": len(all_alliances),
                "total_kills": total_kills,
                "total_isk_destroyed": total_isk
            },
            "conflicts": conflicts
        }
    except redis.RedisError as e:
        raise HTTPException(
            status_code=503,
            detail="Redis connection error. Reports temporarily unavailable."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate alliance wars report"
        )


@router.get("/trade-routes")
async def get_trade_routes() -> Dict:
    """
    Trade Route Danger Map

    Analyzes danger levels along major HighSec trade routes between hubs.
    Shows danger scores per system based on recent kills and gate camps.

    Cache: 1 hour (refreshed daily at 08:00 UTC)
    """
    try:
        # Get original routes data
        routes_data = zkill_live_service.get_trade_route_danger_map()

        # Calculate global summary
        total_routes = len(routes_data.get("routes", []))
        dangerous_count = 0
        total_danger = 0
        gate_camps = 0

        # Transform routes
        transformed_routes = []
        for route in routes_data.get("routes", []):
            avg_danger = route.get("avg_danger_score", 0)
            total_danger += avg_danger

            if avg_danger >= 5:
                dangerous_count += 1

            # Transform systems
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

        return {
            "period": routes_data.get("period", "24h"),
            "global": {
                "total_routes": total_routes,
                "dangerous_routes": dangerous_count,
                "avg_danger_score": avg_danger_score,
                "gate_camps_detected": gate_camps
            },
            "routes": transformed_routes
        }
    except redis.RedisError as e:
        raise HTTPException(
            status_code=503,
            detail="Redis connection error. Reports temporarily unavailable."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate trade routes report"
        )
