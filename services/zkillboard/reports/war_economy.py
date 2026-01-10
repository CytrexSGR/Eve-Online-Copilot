"""
War Economy Report - Fleet doctrines and regional demand.

Combines combat data with market intelligence:
- Regional Demand: Where combat is happening → where market demand rises
- Hot Items: Top destroyed items with market prices
- Fleet Compositions: Ship class breakdown by region (doctrine detection)
- Market Opportunities: Items with highest demand from combat
"""

import json
from datetime import datetime
from typing import Dict, List

from src.database import get_db_connection
from .base import REPORT_CACHE_TTL


class WarEconomyMixin:
    """Mixin providing war economy report methods."""

    def get_24h_battle_report(self) -> Dict:
        """
        Generate comprehensive 24h battle report by region.

        Cached for 7 hours to reduce computation load.

        Returns:
            Dict with regional stats and global summary
        """
        # Check cache first
        cache_key = "battle_report:24h:cache"
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        # Generate fresh report
        # Get all region timelines
        region_keys = list(self.redis_client.scan_iter("kill:region:*:timeline"))

        regional_stats = []
        total_kills_global = 0
        total_isk_global = 0.0

        for region_key in region_keys:
            # Extract region_id from key
            parts = region_key.split(":")
            if len(parts) < 3:
                continue
            region_id = int(parts[2])

            # Get all kills for this region
            kill_ids = self.redis_client.zrevrange(region_key, 0, -1)

            if not kill_ids:
                continue

            kills = []
            for kill_id in kill_ids:
                kill_data = self.redis_client.get(f"kill:id:{kill_id}")
                if kill_data:
                    kills.append(json.loads(kill_data))

            if not kills:
                continue

            # Calculate region stats
            kill_count = len(kills)
            total_isk = sum(k['ship_value'] for k in kills)
            avg_isk = total_isk / kill_count if kill_count > 0 else 0

            # Get top 3 systems
            system_counts = {}
            for kill in kills:
                system_id = kill['solar_system_id']
                system_counts[system_id] = system_counts.get(system_id, 0) + 1
            top_systems = sorted(system_counts.items(), key=lambda x: x[1], reverse=True)[:3]

            # Get top 3 ship types
            ship_counts = {}
            for kill in kills:
                ship_id = kill['ship_type_id']
                ship_counts[ship_id] = ship_counts.get(ship_id, 0) + 1
            top_ships = sorted(ship_counts.items(), key=lambda x: x[1], reverse=True)[:3]

            # Get top 5 destroyed items/modules
            item_counts = {}
            for kill in kills:
                for item in kill.get('destroyed_items', []):
                    item_id = item['item_type_id']
                    quantity = item['quantity']
                    item_counts[item_id] = item_counts.get(item_id, 0) + quantity
            top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            # Get region name from DB
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT "regionName" FROM "mapRegions" WHERE "regionID" = %s',
                        (region_id,)
                    )
                    row = cur.fetchone()
                    region_name = row[0] if row else f"Region {region_id}"

                    # Get system names
                    top_systems_with_names = []
                    for system_id, count in top_systems:
                        cur.execute(
                            'SELECT "solarSystemName" FROM "mapSolarSystems" WHERE "solarSystemID" = %s',
                            (system_id,)
                        )
                        row = cur.fetchone()
                        system_name = row[0] if row else f"System {system_id}"
                        top_systems_with_names.append({
                            "system_id": system_id,
                            "system_name": system_name,
                            "kills": count
                        })

                    # Get ship names
                    top_ships_with_names = []
                    for ship_id, count in top_ships:
                        cur.execute(
                            'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                            (ship_id,)
                        )
                        row = cur.fetchone()
                        ship_name = row[0] if row else f"Ship {ship_id}"
                        top_ships_with_names.append({
                            "ship_type_id": ship_id,
                            "ship_name": ship_name,
                            "losses": count
                        })

                    # Get item/module names
                    top_items_with_names = []
                    for item_id, quantity in top_items:
                        cur.execute(
                            'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                            (item_id,)
                        )
                        row = cur.fetchone()
                        item_name = row[0] if row else f"Item {item_id}"
                        top_items_with_names.append({
                            "item_type_id": item_id,
                            "item_name": item_name,
                            "quantity_destroyed": quantity
                        })

            regional_stats.append({
                "region_id": region_id,
                "region_name": region_name,
                "kills": kill_count,
                "total_isk_destroyed": total_isk,
                "avg_kill_value": avg_isk,
                "top_systems": top_systems_with_names,
                "top_ships": top_ships_with_names,
                "top_destroyed_items": top_items_with_names
            })

            total_kills_global += kill_count
            total_isk_global += total_isk

        # Sort regions by kills descending
        regional_stats.sort(key=lambda x: x['kills'], reverse=True)

        # Find most active and most expensive regions
        most_active_region = regional_stats[0] if regional_stats else None
        most_expensive_region = max(regional_stats, key=lambda x: x['total_isk_destroyed']) if regional_stats else None

        report = {
            "period": "24h",
            "global": {
                "total_kills": total_kills_global,
                "total_isk_destroyed": total_isk_global,
                "most_active_region": most_active_region['region_name'] if most_active_region else None,
                "most_expensive_region": most_expensive_region['region_name'] if most_expensive_region else None
            },
            "regions": regional_stats
        }

        # Cache report for 7 hours (regenerated every 6h by cron)
        self.redis_client.setex(cache_key, REPORT_CACHE_TTL, json.dumps(report))

        return report

    def _detect_doctrines(self, top_hulls: List[Dict], total_ships: int) -> List[str]:
        """
        Detect fleet doctrines based on hull type patterns.

        Known EVE Online doctrines detected:
        - Ferox Fleet (Shield Battlecruiser)
        - Muninn Fleet (Armor HAC)
        - Eagle Fleet (Shield HAC)
        - Caracal Fleet (Shield Cruiser)
        - Jackdaw Fleet (Tactical Destroyer)
        - Bomber Fleet (Stealth Bombers)
        - Capital Brawl (Dreads/Carriers)
        """
        hints = []
        hull_names = {h["ship_name"].lower(): h for h in top_hulls}

        # Known doctrine ships and their detection thresholds
        doctrine_patterns = {
            # Battlecruiser doctrines
            "ferox": ("Ferox Fleet", "battlecruiser", 15),
            "hurricane": ("Hurricane Fleet", "battlecruiser", 15),
            "brutix": ("Brutix Fleet", "battlecruiser", 10),
            "harbinger": ("Harbinger Fleet", "battlecruiser", 10),
            "drake": ("Drake Fleet", "battlecruiser", 15),

            # HAC doctrines
            "muninn": ("Muninn Fleet (Armor HAC)", "cruiser", 10),
            "eagle": ("Eagle Fleet (Shield HAC)", "cruiser", 10),
            "cerberus": ("Cerberus Fleet (Missile HAC)", "cruiser", 10),
            "sacrilege": ("Sacrilege Fleet (Armor HAC)", "cruiser", 8),
            "zealot": ("Zealot Fleet (Armor HAC)", "cruiser", 8),
            "ishtar": ("Ishtar Fleet (Drone HAC)", "cruiser", 10),
            "deimos": ("Deimos Fleet (Armor HAC)", "cruiser", 8),
            "vagabond": ("Vagabond Gang (Kiting HAC)", "cruiser", 5),

            # Cruiser doctrines
            "caracal": ("Caracal Fleet (Missile Cruiser)", "cruiser", 15),
            "moa": ("Moa Fleet (Shield Cruiser)", "cruiser", 10),
            "vexor": ("Vexor Fleet (Drone Cruiser)", "cruiser", 15),
            "thorax": ("Thorax Fleet (Blaster Cruiser)", "cruiser", 10),
            "omen": ("Omen Fleet (Laser Cruiser)", "cruiser", 10),
            "rupture": ("Rupture Fleet (Projectile Cruiser)", "cruiser", 10),

            # Destroyer doctrines
            "jackdaw": ("Jackdaw Fleet (T3 Destroyer)", "destroyer", 10),
            "hecate": ("Hecate Fleet (T3 Destroyer)", "destroyer", 8),
            "confessor": ("Confessor Fleet (T3 Destroyer)", "destroyer", 8),
            "svipul": ("Svipul Fleet (T3 Destroyer)", "destroyer", 8),
            "cormorant": ("Cormorant Fleet (Rail Destroyer)", "destroyer", 15),
            "catalyst": ("Catalyst Gang (Gankers)", "destroyer", 20),
            "thrasher": ("Thrasher Fleet (Arty Destroyer)", "destroyer", 15),
            "coercer": ("Coercer Fleet (Beam Destroyer)", "destroyer", 15),
            "kikimora": ("Kikimora Fleet (Trig Destroyer)", "destroyer", 10),

            # Stealth Bomber doctrines
            "manticore": ("Bomber Fleet", "frigate", 5),
            "purifier": ("Bomber Fleet", "frigate", 5),
            "hound": ("Bomber Fleet", "frigate", 5),
            "nemesis": ("Bomber Fleet", "frigate", 5),

            # Interdictor presence (indicates fleet fights)
            "sabre": ("Interdictor Support", "destroyer", 8),
            "flycatcher": ("Interdictor Support", "destroyer", 8),

            # Capital presence
            "revelation": ("Capital Brawl (Dreadnoughts)", "dreadnought", 3),
            "naglfar": ("Capital Brawl (Dreadnoughts)", "dreadnought", 3),
            "moros": ("Capital Brawl (Dreadnoughts)", "dreadnought", 3),
            "phoenix": ("Capital Brawl (Dreadnoughts)", "dreadnought", 3),
            "thanatos": ("Carrier Operations", "carrier", 2),
            "nidhoggur": ("Carrier Operations", "carrier", 2),
            "archon": ("Carrier Operations", "carrier", 2),
            "chimera": ("Carrier Operations", "carrier", 2),

            # Logistics (indicates organized fleet)
            "scimitar": ("Logistics Supported", "cruiser", 5),
            "basilisk": ("Logistics Supported", "cruiser", 5),
            "guardian": ("Logistics Supported", "cruiser", 5),
            "oneiros": ("Logistics Supported", "cruiser", 5),
            "exequror navy issue": ("Navy Logi Supported", "cruiser", 8),
        }

        detected = set()
        for ship_key, (doctrine_name, expected_class, min_count) in doctrine_patterns.items():
            # Check for exact match or partial match
            for hull_name, hull_data in hull_names.items():
                if ship_key in hull_name and hull_data["losses"] >= min_count:
                    if doctrine_name not in detected:
                        detected.add(doctrine_name)
                        count = hull_data["losses"]
                        hints.append(f"{doctrine_name} ({count} ships)")

        # Detect mixed doctrines based on ship class dominance
        class_counts = {}
        for h in top_hulls:
            sc = h["ship_class"]
            class_counts[sc] = class_counts.get(sc, 0) + h["losses"]

        if not hints:
            # Fallback to class-based detection if no specific doctrine found
            for ship_class, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
                pct = (count / total_ships) * 100 if total_ships > 0 else 0
                if ship_class == "battlecruiser" and pct > 25:
                    hints.append(f"Battlecruiser Doctrine ({count} ships, {pct:.0f}%)")
                elif ship_class == "cruiser" and pct > 30:
                    hints.append(f"Cruiser Gang ({count} ships, {pct:.0f}%)")
                elif ship_class == "destroyer" and pct > 30:
                    hints.append(f"Destroyer Swarm ({count} ships, {pct:.0f}%)")
                elif ship_class == "frigate" and pct > 35:
                    hints.append(f"Frigate Blob ({count} ships, {pct:.0f}%)")

        return hints[:4]  # Max 4 doctrine hints

    def get_war_economy_report(self, limit: int = 10) -> Dict:
        """
        Generate War Economy report combining combat data with market intelligence.

        Provides:
        - Regional Demand: Where combat is happening → where market demand rises
        - Hot Items: Top destroyed items with market prices
        - Fleet Compositions: Ship class breakdown by region (doctrine detection)
        - Market Opportunities: Items with highest demand from combat

        Args:
            limit: Number of items/regions to return per section

        Returns:
            Dict with war economy intelligence
        """
        cache_key = "war_economy:report:cache"
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        result = {
            "timestamp": datetime.now().isoformat(),
            "period": "24h",
            "regional_demand": [],
            "hot_items": [],
            "fleet_compositions": [],
            "global_summary": {}
        }

        try:
            # Get profiteering data for hot items
            profiteering = self.get_war_profiteering_report(limit=limit * 2)
            result["hot_items"] = profiteering.get("items", [])[:limit]

            # Get regional combat data with destroyed items
            regional_data = {}

            # Scan all region timelines
            for key in self.redis_client.scan_iter("kill:region:*:timeline"):
                parts = key.split(":")
                if len(parts) < 3:
                    continue
                region_id = int(parts[2])

                # Get kills for this region
                kill_ids = self.redis_client.zrevrange(key, 0, -1)
                if not kill_ids:
                    continue

                kills = []
                for kill_id in kill_ids:
                    kill_data = self.redis_client.get(f"kill:id:{kill_id}")
                    if kill_data:
                        kills.append(json.loads(kill_data))

                if not kills:
                    continue

                # Calculate regional stats
                kill_count = len(kills)
                total_isk = sum(k.get('ship_value', 0) for k in kills)

                # Track destroyed items in this region
                region_items = {}
                for kill in kills:
                    for item in kill.get('destroyed_items', []):
                        item_id = item['item_type_id']
                        quantity = item['quantity']
                        region_items[item_id] = region_items.get(item_id, 0) + quantity

                # Track ship classes (for doctrine detection)
                ship_class_counts = {}
                for kill in kills:
                    ship_class = self.get_ship_class(kill.get('ship_type_id', 0))
                    if ship_class:
                        ship_class_counts[ship_class] = ship_class_counts.get(ship_class, 0) + 1

                regional_data[region_id] = {
                    "region_id": region_id,
                    "kills": kill_count,
                    "isk_destroyed": total_isk,
                    "destroyed_items": region_items,
                    "ship_classes": ship_class_counts
                }

            if not regional_data:
                # Return empty result with valid structure
                result["global_summary"] = {
                    "total_regions_active": 0,
                    "total_kills_24h": 0,
                    "total_isk_destroyed": 0,
                    "hottest_region": None
                }
                return result

            # Enrich with region names and calculate top items per region
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get region names
                    region_ids = list(regional_data.keys())
                    cur.execute(
                        '''SELECT "regionID", "regionName" FROM "mapRegions" WHERE "regionID" = ANY(%s)''',
                        (region_ids,)
                    )
                    region_names = {row[0]: row[1] for row in cur.fetchall()}

                    # Get all unique item IDs for price lookup
                    all_item_ids = set()
                    for data in regional_data.values():
                        all_item_ids.update(data["destroyed_items"].keys())

                    # Batch query for item names and prices
                    item_info = {}
                    if all_item_ids:
                        cur.execute(
                            '''SELECT
                                t."typeID",
                                t."typeName",
                                g."categoryID",
                                COALESCE(mp.lowest_sell, mpc.adjusted_price, t."basePrice"::double precision, 0) as price
                            FROM "invTypes" t
                            JOIN "invGroups" g ON t."groupID" = g."groupID"
                            LEFT JOIN market_prices mp ON t."typeID" = mp.type_id AND mp.region_id = 10000002
                            LEFT JOIN market_prices_cache mpc ON t."typeID" = mpc.type_id
                            WHERE t."typeID" = ANY(%s)''',
                            (list(all_item_ids),)
                        )
                        for row in cur.fetchall():
                            # Exclude raw materials (category 4, 25, 43)
                            if row[2] not in (4, 25, 43):
                                item_info[row[0]] = {
                                    "name": row[1],
                                    "price": float(row[3]) if row[3] else 0
                                }

            # Build regional demand list
            regional_demand = []
            for region_id, data in regional_data.items():
                region_name = region_names.get(region_id, f"Region {region_id}")

                # Get top 5 items for this region with market value
                top_items = []
                for item_id, quantity in sorted(
                    data["destroyed_items"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]:
                    if item_id in item_info:
                        info = item_info[item_id]
                        top_items.append({
                            "item_type_id": item_id,
                            "item_name": info["name"],
                            "quantity_destroyed": quantity,
                            "market_price": info["price"],
                            "demand_value": quantity * info["price"]
                        })

                regional_demand.append({
                    "region_id": region_id,
                    "region_name": region_name,
                    "kills": data["kills"],
                    "isk_destroyed": data["isk_destroyed"],
                    "top_demanded_items": top_items,
                    "ship_classes": data["ship_classes"],
                    "demand_score": sum(i["demand_value"] for i in top_items)
                })

            # Sort by demand score (highest opportunity first)
            regional_demand.sort(key=lambda x: x["demand_score"], reverse=True)
            result["regional_demand"] = regional_demand[:limit]

            # Build fleet compositions (doctrine detection) per region
            fleet_compositions = []

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get top 5 combat regions by kills
                    top_region_ids = [rd["region_id"] for rd in result["regional_demand"][:5]]

                    if top_region_ids:
                        # Query specific hull types per region (excluding noise)
                        cur.execute("""
                            SELECT
                                k.region_id,
                                k.ship_type_id,
                                t."typeName" as ship_name,
                                k.ship_class,
                                g."groupName" as ship_group,
                                COUNT(*) as losses
                            FROM killmails k
                            JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                            JOIN "invGroups" g ON t."groupID" = g."groupID"
                            WHERE k.killmail_time > NOW() - INTERVAL '24 hours'
                              AND k.region_id = ANY(%s)
                              AND k.ship_class NOT IN ('capsule', 'shuttle', 'corvette', 'other')
                            GROUP BY k.region_id, k.ship_type_id, t."typeName", k.ship_class, g."groupName"
                            ORDER BY k.region_id, losses DESC
                        """, (top_region_ids,))

                        # Group by region
                        region_hulls = {}
                        for row in cur.fetchall():
                            region_id, ship_type_id, ship_name, ship_class, ship_group, losses = row
                            if region_id not in region_hulls:
                                region_hulls[region_id] = []
                            region_hulls[region_id].append({
                                "ship_type_id": ship_type_id,
                                "ship_name": ship_name,
                                "ship_class": ship_class,
                                "ship_group": ship_group,
                                "losses": losses
                            })

                        # Build composition for each region
                        for rd in result["regional_demand"][:5]:
                            region_id = rd["region_id"]
                            hulls = region_hulls.get(region_id, [])

                            if not hulls:
                                continue

                            total_ships = sum(h["losses"] for h in hulls)
                            top_hulls = hulls[:8]  # Top 8 hull types

                            # Detect doctrines based on hull patterns
                            doctrine_hints = self._detect_doctrines(top_hulls, total_ships)

                            # Group by ship class for summary
                            class_breakdown = {}
                            for h in hulls:
                                sc = h["ship_class"]
                                if sc not in class_breakdown:
                                    class_breakdown[sc] = 0
                                class_breakdown[sc] += h["losses"]

                            composition = {
                                "region_id": region_id,
                                "region_name": rd["region_name"],
                                "total_ships_lost": total_ships,
                                "top_hulls": [
                                    {
                                        "ship_name": h["ship_name"],
                                        "ship_class": h["ship_class"],
                                        "losses": h["losses"],
                                        "percentage": round((h["losses"] / total_ships) * 100, 1)
                                    }
                                    for h in top_hulls
                                ],
                                "class_summary": {
                                    k: {"count": v, "percentage": round((v / total_ships) * 100, 1)}
                                    for k, v in sorted(class_breakdown.items(), key=lambda x: x[1], reverse=True)[:6]
                                },
                                "doctrine_hints": doctrine_hints
                            }
                            fleet_compositions.append(composition)

            result["fleet_compositions"] = fleet_compositions

            # Global summary
            total_kills = sum(rd["kills"] for rd in result["regional_demand"])
            total_isk = sum(rd["isk_destroyed"] for rd in result["regional_demand"])
            hottest = result["regional_demand"][0] if result["regional_demand"] else None

            result["global_summary"] = {
                "total_regions_active": len(regional_data),
                "total_kills_24h": total_kills,
                "total_isk_destroyed": total_isk,
                "hottest_region": {
                    "region_id": hottest["region_id"],
                    "region_name": hottest["region_name"],
                    "kills": hottest["kills"]
                } if hottest else None,
                "total_opportunity_value": sum(i.get("opportunity_value", 0) for i in result["hot_items"])
            }

            # Cache for 7 hours (regenerated every 6h by cron)
            self.redis_client.setex(cache_key, REPORT_CACHE_TTL, json.dumps(result))

            return result

        except Exception as e:
            print(f"Error generating war economy report: {e}")
            import traceback
            traceback.print_exc()
            result["error"] = str(e)
            return result
