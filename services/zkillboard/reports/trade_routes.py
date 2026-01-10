"""
Trade Route Danger Map - Safety analysis of trade routes.

Analyzes danger levels along major trade routes between hubs.
Provides danger scores based on:
- Kill frequency in last 24h
- Average ship value destroyed
- Gate camp indicators (multi-attacker kills)
"""

import json
from datetime import datetime
from typing import Dict, List

from src.route_service import RouteService, TRADE_HUB_SYSTEMS
from .base import REPORT_CACHE_TTL


class TradeRoutesMixin:
    """Mixin providing trade route danger analysis methods."""

    def get_trade_route_danger_map(self) -> Dict:
        """
        Analyze danger levels along major trade routes between hubs.

        Returns routes with danger scores per system based on:
        - Kill frequency in last 24h
        - Average ship value destroyed
        - Gate camp indicators (multi-attacker kills)

        Returns:
            Dict with routes and danger analysis
        """
        # Check cache first
        cache_key = "report:trade_routes:danger_map"
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                print(f"[CACHE HIT] Returning cached trade routes report")
                return json.loads(cached)
        except Exception:
            pass

        route_service = RouteService()

        # Major trade routes (hub pairs)
        trade_routes = [
            ('jita', 'amarr'),
            ('jita', 'dodixie'),
            ('jita', 'rens'),
            ('amarr', 'dodixie'),
            ('amarr', 'rens'),
        ]

        # Build system danger scores from Redis data
        system_danger = {}
        system_kill_count = {}
        system_total_isk = {}
        system_gate_camps = set()

        # Get all system timelines
        system_keys = list(self.redis_client.scan_iter("kill:system:*:timeline"))

        for system_key in system_keys:
            # Extract system_id from key
            parts = system_key.split(":")
            if len(parts) < 3:
                continue
            system_id = int(parts[2])

            # Get kills for this system
            kill_ids = self.redis_client.zrevrange(system_key, 0, -1)
            if not kill_ids:
                continue

            kills = []
            for kill_id in kill_ids:
                kill_data = self.redis_client.get(f"kill:id:{kill_id}")
                if kill_data:
                    kills.append(json.loads(kill_data))

            if not kills:
                continue

            # Calculate danger metrics
            kill_count = len(kills)
            total_isk = sum(k['ship_value'] for k in kills)
            avg_isk = total_isk / kill_count if kill_count > 0 else 0

            # Detect gate camps (kills with 4+ attackers)
            gate_camp_kills = sum(1 for k in kills if k.get('attacker_count', 0) >= 4)
            gate_camp_ratio = gate_camp_kills / kill_count if kill_count > 0 else 0

            # Danger score calculation (0-100)
            # - Kill frequency: 0-40 points (1 point per kill, capped at 40)
            # - Average value: 0-30 points (1 point per 100M ISK, capped at 30)
            # - Gate camps: 0-30 points (30 points if >20% gate camps)
            danger_score = min(40, kill_count) + \
                          min(30, int(avg_isk / 100_000_000)) + \
                          (30 if gate_camp_ratio > 0.2 else 0)

            system_danger[system_id] = danger_score
            system_kill_count[system_id] = kill_count
            system_total_isk[system_id] = total_isk

            if gate_camp_ratio > 0.2:
                system_gate_camps.add(system_id)

        # Calculate routes with danger analysis
        routes_data = []

        for from_hub, to_hub in trade_routes:
            from_system_id = TRADE_HUB_SYSTEMS[from_hub]
            to_system_id = TRADE_HUB_SYSTEMS[to_hub]

            # Calculate route (HighSec only)
            route = route_service.find_route(
                from_system_id,
                to_system_id,
                avoid_lowsec=True,
                avoid_nullsec=True
            )

            if not route:
                continue

            # Analyze danger along route
            route_systems = []
            total_danger = 0
            max_danger_system = None
            max_danger_score = 0

            for system in route:
                system_id = system['system_id']
                danger = system_danger.get(system_id, 0)
                kill_count = system_kill_count.get(system_id, 0)
                total_isk = system_total_isk.get(system_id, 0)
                is_gate_camp = system_id in system_gate_camps

                total_danger += danger

                if danger > max_danger_score:
                    max_danger_score = danger
                    max_danger_system = system

                route_systems.append({
                    "system_id": system_id,
                    "system_name": system['system_name'],
                    "security": system['security'],
                    "danger_score": danger,
                    "kills_24h": kill_count,
                    "isk_destroyed_24h": total_isk,
                    "gate_camp_detected": is_gate_camp
                })

            # Classify route danger level
            avg_danger = total_danger / len(route_systems) if route_systems else 0
            if avg_danger >= 50:
                danger_level = "EXTREME"
            elif avg_danger >= 30:
                danger_level = "HIGH"
            elif avg_danger >= 15:
                danger_level = "MODERATE"
            elif avg_danger >= 5:
                danger_level = "LOW"
            else:
                danger_level = "SAFE"

            routes_data.append({
                "from_hub": from_hub.upper(),
                "to_hub": to_hub.upper(),
                "from_system_id": from_system_id,
                "to_system_id": to_system_id,
                "total_jumps": len(route_systems),
                "danger_level": danger_level,
                "avg_danger_score": round(avg_danger, 1),
                "total_danger_score": total_danger,
                "max_danger_system": {
                    "system_id": max_danger_system['system_id'],
                    "system_name": max_danger_system['system_name'],
                    "danger_score": max_danger_score
                } if max_danger_system else None,
                "systems": route_systems
            })

        # Sort by danger level
        routes_data.sort(key=lambda x: x['avg_danger_score'], reverse=True)

        result = {
            "timestamp": datetime.now().isoformat(),
            "routes": routes_data,
            "total_routes": len(routes_data),
            "period": "24h",
            "danger_scale": {
                "SAFE": "0-5 avg danger",
                "LOW": "5-15 avg danger",
                "MODERATE": "15-30 avg danger",
                "HIGH": "30-50 avg danger",
                "EXTREME": "50+ avg danger"
            }
        }

        # Cache for 7 hours
        try:
            self.redis_client.setex(cache_key, REPORT_CACHE_TTL, json.dumps(result))
            print(f"[CACHE] Cached trade routes report for {REPORT_CACHE_TTL}s")
        except Exception:
            pass

        return result
