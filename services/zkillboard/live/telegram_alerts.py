"""
Telegram Alert Methods.

Provides notification functionality for battle events via Telegram.
"""

import asyncio
from typing import Dict, Optional, TYPE_CHECKING

from src.database import get_db_connection
from src.telegram_service import telegram_service
from .ship_classifier import safe_int_value

if TYPE_CHECKING:
    from .models import LiveKillmail


class TelegramAlertsMixin:
    """Mixin providing Telegram alert methods for ZKillboardLiveService."""

    async def send_initial_battle_alert(self, battle_id: int, system_id: int):
        """
        Send initial "New Battle" alert when battle reaches threshold.

        Alert sent when:
        - Battle has >=5 kills (sustained combat) OR
        - Battle total ISK >=500M (high-value engagement)

        Args:
            battle_id: Battle ID
            system_id: Solar system ID
        """
        try:
            # Get battle and system info
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT
                            b.total_kills,
                            b.total_isk_destroyed,
                            ms."solarSystemName",
                            mr."regionName",
                            ms.security,
                            b.initial_alert_sent
                        FROM battles b
                        JOIN "mapSolarSystems" ms ON ms."solarSystemID" = b.solar_system_id
                        JOIN "mapRegions" mr ON mr."regionID" = ms."regionID"
                        WHERE b.battle_id = %s
                    """, (battle_id,))

                    row = cur.fetchone()
                    if not row:
                        return

                    kills, isk_destroyed, system_name, region_name, security, initial_alert_sent = row

                    # SMART THRESHOLD: Only alert if significant activity
                    # - >=5 kills (sustained combat) OR
                    # - >=500M ISK destroyed (high-value target)
                    if kills < 5 and isk_destroyed < 500_000_000:
                        return  # Below threshold, wait for more activity

                    # ATOMIC: Try to claim the initial alert (prevent duplicates)
                    cur.execute("""
                        UPDATE battles
                        SET initial_alert_sent = TRUE
                        WHERE battle_id = %s
                          AND initial_alert_sent = FALSE
                        RETURNING telegram_message_id
                    """, (battle_id,))

                    result = cur.fetchone()
                    if not result:
                        return  # Alert already claimed by another task

                    conn.commit()

                    # Create initial alert message
                    isk_b = isk_destroyed / 1_000_000_000
                    alert_msg = f"""⚠️ **NEW BATTLE DETECTED**

📍 **Location:** {system_name} ({security:.1f}) - {region_name}
🆕 **Status:** Battle just started
💀 **Current:** {kills} kills, {isk_b:.1f}B ISK

⚔️ Combat has begun - monitoring engagement"""

                    # Send to Telegram
                    message_id = await telegram_service.send_alert(alert_msg)
                    if message_id:
                        # Update battle with message_id
                        cur.execute("""
                            UPDATE battles
                            SET telegram_message_id = %s,
                                last_milestone_notified = 0
                            WHERE battle_id = %s
                        """, (message_id, battle_id))
                        conn.commit()
                        print(f"[ALERT] Initial battle alert sent for battle {battle_id} (message_id: {message_id}, {kills} kills, {isk_b:.1f}B ISK)")

        except Exception as e:
            print(f"Error sending initial battle alert: {e}")

    async def send_high_value_kill_alert(self, kill: 'LiveKillmail'):
        """
        Send immediate alert for high-value kills (>=2B ISK).

        Alerts for expensive ships regardless of battle status:
        - Freighters, Jump Freighters
        - Rorquals, Titans, Supercarriers
        - Any ship worth >=2B ISK

        Args:
            kill: LiveKillmail with ship and victim data
        """
        try:
            ship_value = safe_int_value(kill.ship_value)

            # Threshold: 2B ISK
            if ship_value < 2_000_000_000:
                return

            # Get system info
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT
                            ms."solarSystemName",
                            mr."regionName",
                            ms.security,
                            it."typeName"
                        FROM "mapSolarSystems" ms
                        JOIN "mapRegions" mr ON mr."regionID" = ms."regionID"
                        LEFT JOIN "invTypes" it ON it."typeID" = %s
                        WHERE ms."solarSystemID" = %s
                    """, (kill.ship_type_id, kill.solar_system_id))

                    row = cur.fetchone()
                    if not row:
                        return

                    system_name, region_name, security, ship_type_name = row

            isk_b = ship_value / 1_000_000_000

            # Create high-value kill alert
            alert_msg = f"""💰 **HIGH VALUE KILL DETECTED**

📍 **Location:** {system_name} ({security:.1f}) - {region_name}
🚢 **Ship:** {ship_type_name or f"Type {kill.ship_type_id}"}
💀 **Value:** {isk_b:.2f}B ISK

⚠️ High-value target destroyed - opportunity for market profiteering"""

            # Send to Telegram (no message_id tracking needed, one-off alert)
            message_id = await telegram_service.send_alert(alert_msg)
            if message_id:
                print(f"[ALERT] High-value kill alert sent: {ship_type_name} ({isk_b:.2f}B ISK) in {system_name}")

        except Exception as e:
            print(f"Error sending high-value kill alert: {e}")

    async def check_and_send_milestone_alert(self, battle_id: int, current_kills: int, system_id: int):
        """
        Check if battle reached a milestone and send alert if needed.

        Milestones: 10, 25, 50, 100 kills

        Args:
            battle_id: Battle ID
            current_kills: Current total kill count
            system_id: Solar system ID
        """
        try:
            # Define milestones
            MILESTONES = [10, 25, 50, 100, 200, 500]

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # ATOMIC: Try to claim this milestone (prevents race conditions)
                    # Find the next milestone that should be notified
                    next_milestone = None
                    for milestone in MILESTONES:
                        if current_kills >= milestone:
                            next_milestone = milestone
                        else:
                            break  # Stop at first unreached milestone

                    if not next_milestone:
                        return  # No milestone reached

                    # Atomically update last_milestone_notified ONLY if it hasn't been updated yet
                    # This prevents duplicate alerts from concurrent kills
                    cur.execute("""
                        UPDATE battles
                        SET last_milestone_notified = %s
                        WHERE battle_id = %s
                          AND last_milestone_notified < %s
                        RETURNING telegram_message_id, total_isk_destroyed, last_milestone_notified
                    """, (next_milestone, battle_id, next_milestone))

                    row = cur.fetchone()
                    if not row:
                        return  # Milestone already claimed by another task

                    message_id, total_isk, _ = row
                    conn.commit()

                    # Successfully claimed milestone - now send alert

                    # Get system info
                    cur.execute("""
                        SELECT ms."solarSystemName", mr."regionName", ms.security
                        FROM "mapSolarSystems" ms
                        JOIN "mapRegions" mr ON mr."regionID" = ms."regionID"
                        WHERE ms."solarSystemID" = %s
                    """, (system_id,))

                    sys_row = cur.fetchone()
                    if not sys_row:
                        return

                    system_name, region_name, security = sys_row

                    # Get involved parties
                    involved = await self.get_involved_parties(system_id, limit=3)

                    # Create milestone alert message
                    isk_b = total_isk / 1_000_000_000
                    alert_msg = f"""📊 **BATTLE UPDATE - Milestone Reached**

📍 **Location:** {system_name} ({security:.1f}) - {region_name}
🎯 **Milestone:** {next_milestone} KILLS REACHED
💀 **Battle Totals:** {current_kills} kills, {isk_b:.1f}B ISK"""

                    # Add involved parties
                    if involved['attackers']['alliances']:
                        alert_msg += "\n\n**⚔️ Attacking Forces:**"
                        for alliance in involved['attackers']['alliances'][:3]:
                            alert_msg += f"\n   • {alliance['name']} ({alliance['kills']} kills)"

                    if involved['victims']['alliances']:
                        alert_msg += "\n\n**💀 Primary Victims:**"
                        for alliance in involved['victims']['alliances'][:3]:
                            alert_msg += f"\n   • {alliance['name']} ({alliance['kills']} losses)"

                    alert_msg += "\n\n🔥 Battle ongoing - use caution"

                    # Send or update message
                    if message_id:
                        # Edit existing message
                        success = await telegram_service.edit_message(message_id, alert_msg)
                        if success:
                            print(f"[ALERT] Milestone alert updated for battle {battle_id} ({next_milestone} kills)")
                    else:
                        # Send new message (fallback if no previous message)
                        new_message_id = await telegram_service.send_alert(alert_msg)
                        if new_message_id:
                            print(f"[ALERT] Milestone alert sent for battle {battle_id} ({next_milestone} kills)")
                            # Update telegram_message_id for future edits
                            cur.execute("""
                                UPDATE battles
                                SET telegram_message_id = %s
                                WHERE battle_id = %s
                            """, (new_message_id, battle_id))
                            conn.commit()

        except Exception as e:
            print(f"Error checking milestone alert: {e}")

    async def send_battle_ended_alert(self, battle_id: int, system_id: int, final_stats: Dict):
        """
        Send final alert when battle ends.

        Args:
            battle_id: Battle ID
            system_id: Solar system ID
            final_stats: Dict with total_kills, total_isk, duration_minutes
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT
                            telegram_message_id,
                            ms."solarSystemName",
                            mr."regionName",
                            ms.security
                        FROM battles b
                        JOIN "mapSolarSystems" ms ON ms."solarSystemID" = b.solar_system_id
                        JOIN "mapRegions" mr ON mr."regionID" = ms."regionID"
                        WHERE b.battle_id = %s
                    """, (battle_id,))

                    row = cur.fetchone()
                    if not row:
                        return

                    message_id, system_name, region_name, security = row

                    # Create final alert message
                    isk_b = final_stats.get('total_isk', 0) / 1_000_000_000
                    duration = final_stats.get('duration_minutes', 0)
                    alert_msg = f"""✅ **BATTLE ENDED**

📍 **Location:** {system_name} ({security:.1f}) - {region_name}
⏱️ **Duration:** {duration} minutes
💀 **Final Count:** {final_stats.get('total_kills', 0)} kills
💰 **Total Destroyed:** {isk_b:.1f}B ISK

🏁 Combat has ceased"""

                    # Get top alliances involved
                    involved = await self.get_involved_parties(system_id, limit=2)
                    if involved['attackers']['alliances']:
                        alert_msg += "\n\n**Top Attackers:**"
                        for alliance in involved['attackers']['alliances'][:2]:
                            alert_msg += f"\n   • {alliance['name']} ({alliance['kills']} kills)"

                    # Edit existing message or send new
                    if message_id:
                        success = await telegram_service.edit_message(message_id, alert_msg)
                        if success:
                            print(f"[ALERT] Battle ended alert sent for battle {battle_id}")
                    else:
                        # Fallback: send new message
                        message_id = await telegram_service.send_alert(alert_msg)
                        if message_id:
                            print(f"[ALERT] Battle ended alert sent (new) for battle {battle_id}")

        except Exception as e:
            print(f"Error sending battle ended alert: {e}")
