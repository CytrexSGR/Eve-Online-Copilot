"""
Battle Tracking Module.

Provides battle creation, participant tracking, and finalization logic.
"""

import asyncio
from typing import Dict, Optional, TYPE_CHECKING

from src.database import get_db_connection
from .ship_classifier import safe_int_value

if TYPE_CHECKING:
    from .models import LiveKillmail


class BattleTrackerMixin:
    """Mixin providing battle tracking methods for ZKillboardLiveService."""

    def create_battle_for_hotspot(self, kill: 'LiveKillmail') -> Optional[int]:
        """
        Create a new battle when a hotspot is detected (5+ kills in 5 minutes).

        NOTE: Battle stats are NO LONGER updated here. Stats are computed from
        battle_stats_computed view and refreshed in store_persistent_kill().

        This method ONLY creates new battles - it does NOT update existing battles.
        Kill-to-battle association happens atomically in store_persistent_kill().

        Args:
            kill: LiveKillmail that triggered the hotspot detection

        Returns:
            battle_id if battle was created, None if battle already exists
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Check if there's already an active battle in this system
                    cur.execute("""
                        SELECT battle_id
                        FROM battles
                        WHERE solar_system_id = %s
                          AND status = 'active'
                          AND last_kill_at > NOW() - INTERVAL '30 minutes'
                        LIMIT 1
                    """, (kill.solar_system_id,))

                    if cur.fetchone():
                        # Battle already exists - don't create duplicate
                        # The kill will be associated via store_persistent_kill()
                        return None

                    # Create new battle with initial stats = 0
                    # Stats will be populated by refresh_battle_stats() after first kill
                    print(f"[BATTLE] Creating new battle in system {kill.solar_system_id}")

                    cur.execute("""
                        INSERT INTO battles (
                            solar_system_id,
                            region_id,
                            started_at,
                            last_kill_at,
                            total_kills,
                            total_isk_destroyed,
                            capital_kills,
                            status
                        ) VALUES (
                            %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, 0, 0, 'active'
                        )
                        RETURNING battle_id
                    """, (
                        kill.solar_system_id,
                        kill.region_id
                    ))

                    battle_id = cur.fetchone()[0]
                    conn.commit()
                    print(f"[BATTLE] Battle {battle_id} created in system {kill.solar_system_id}")

                    # Send initial battle alert after a few more kills
                    asyncio.create_task(self.send_initial_battle_alert(battle_id, kill.solar_system_id))

                    return battle_id

        except Exception as e:
            print(f"Error creating battle: {e}")
            return None

    def update_battle_participants(self, battle_id: int, kill: 'LiveKillmail'):
        """
        Update battle participants (alliances and corps involved).

        Tracks kills and losses for each alliance/corp in a battle.

        Args:
            battle_id: Battle ID to update
            kill: LiveKillmail with victim and attacker data
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Update victim alliance/corp (losses)
                    if kill.victim_alliance_id:
                        cur.execute("""
                            INSERT INTO battle_participants (
                                battle_id, alliance_id, corporation_id,
                                kills, losses, isk_destroyed, isk_lost
                            ) VALUES (
                                %s, %s, %s, 0, 1, 0, %s
                            )
                            ON CONFLICT (battle_id, alliance_id, corporation_id)
                            DO UPDATE SET
                                losses = battle_participants.losses + 1,
                                isk_lost = battle_participants.isk_lost + %s
                        """, (
                            battle_id,
                            kill.victim_alliance_id,
                            kill.victim_corporation_id,
                            safe_int_value(kill.ship_value),
                            safe_int_value(kill.ship_value)
                        ))

                    # Update attacker alliances/corps (kills)
                    attacker_alliances = set(kill.attacker_alliances)
                    for alliance_id in attacker_alliances:
                        if alliance_id:
                            cur.execute("""
                                INSERT INTO battle_participants (
                                    battle_id, alliance_id, corporation_id,
                                    kills, losses, isk_destroyed, isk_lost
                                ) VALUES (
                                    %s, %s, NULL, 1, 0, %s, 0
                                )
                                ON CONFLICT (battle_id, alliance_id, corporation_id)
                                DO UPDATE SET
                                    kills = battle_participants.kills + 1,
                                    isk_destroyed = battle_participants.isk_destroyed + %s
                            """, (
                                battle_id,
                                alliance_id,
                                safe_int_value(kill.ship_value),
                                safe_int_value(kill.ship_value)
                            ))

                    conn.commit()

        except Exception as e:
            print(f"Error updating battle participants: {e}")

    def track_alliance_war(self, kill: 'LiveKillmail'):
        """
        Track alliance wars based on kill data.

        Creates or updates alliance_wars records when alliances fight each other.
        Also updates daily statistics for trend analysis.

        Args:
            kill: LiveKillmail with victim and attacker alliance data
        """
        if not kill.victim_alliance_id:
            return  # No alliance war if victim has no alliance

        victim_alliance = kill.victim_alliance_id
        attacker_alliances = set(kill.attacker_alliances)

        # Remove None values and victim alliance from attackers
        attacker_alliances.discard(None)
        attacker_alliances.discard(victim_alliance)

        if not attacker_alliances:
            return  # No opposing alliances

        # Safely convert ship_value to int
        isk_value = safe_int_value(kill.ship_value)

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    for attacker_alliance in attacker_alliances:
                        # Ensure consistent ordering (smaller ID first)
                        alliance_a = min(victim_alliance, attacker_alliance)
                        alliance_b = max(victim_alliance, attacker_alliance)

                        # Determine who killed whom
                        if victim_alliance == alliance_a:
                            # Alliance A was victim, B killed
                            kills_by_a = 0
                            kills_by_b = 1
                        else:
                            # Alliance B was victim, A killed
                            kills_by_a = 1
                            kills_by_b = 0

                        # Create or update war record
                        cur.execute("""
                            INSERT INTO alliance_wars (
                                alliance_a_id,
                                alliance_b_id,
                                first_kill_at,
                                last_kill_at,
                                total_kills,
                                total_isk_destroyed,
                                status
                            ) VALUES (
                                %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, %s, 'active'
                            )
                            ON CONFLICT (alliance_a_id, alliance_b_id)
                            DO UPDATE SET
                                last_kill_at = CURRENT_TIMESTAMP,
                                total_kills = alliance_wars.total_kills + 1,
                                total_isk_destroyed = alliance_wars.total_isk_destroyed + %s,
                                status = 'active'
                            RETURNING war_id
                        """, (
                            alliance_a,
                            alliance_b,
                            isk_value,
                            isk_value
                        ))

                        war_id = cur.fetchone()[0]

                        # Update daily stats
                        cur.execute("""
                            INSERT INTO war_daily_stats (
                                war_id,
                                date,
                                kills_by_a,
                                isk_destroyed_by_a,
                                kills_by_b,
                                isk_destroyed_by_b,
                                active_systems
                            ) VALUES (
                                %s, CURRENT_DATE, %s, %s, %s, %s, 1
                            )
                            ON CONFLICT (war_id, date)
                            DO UPDATE SET
                                kills_by_a = war_daily_stats.kills_by_a + %s,
                                isk_destroyed_by_a = war_daily_stats.isk_destroyed_by_a + %s,
                                kills_by_b = war_daily_stats.kills_by_b + %s,
                                isk_destroyed_by_b = war_daily_stats.isk_destroyed_by_b + %s
                        """, (
                            war_id,
                            kills_by_a,
                            isk_value if kills_by_a > 0 else 0,
                            kills_by_b,
                            isk_value if kills_by_b > 0 else 0,
                            kills_by_a,
                            isk_value if kills_by_a > 0 else 0,
                            kills_by_b,
                            isk_value if kills_by_b > 0 else 0
                        ))

                    conn.commit()

        except Exception as e:
            import traceback
            print(f"Error tracking alliance war: {e}")
            traceback.print_exc()

    def finalize_dormant_wars(self):
        """
        Mark wars as dormant if no activity for 7+ days.
        Mark wars as ended if no activity for 30+ days.
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Mark as dormant: no kills in 7 days
                    cur.execute("""
                        UPDATE alliance_wars
                        SET status = 'dormant'
                        WHERE status = 'active'
                          AND last_kill_at < NOW() - INTERVAL '7 days'
                        RETURNING war_id, alliance_a_id, alliance_b_id
                    """)

                    dormant = cur.fetchall()
                    if dormant:
                        for war_id, alliance_a, alliance_b in dormant:
                            print(f"[WAR] War {war_id} ({alliance_a} vs {alliance_b}) marked dormant")

                    # Mark as ended: no kills in 30 days
                    cur.execute("""
                        UPDATE alliance_wars
                        SET status = 'ended'
                        WHERE status = 'dormant'
                          AND last_kill_at < NOW() - INTERVAL '30 days'
                        RETURNING war_id, alliance_a_id, alliance_b_id
                    """)

                    ended = cur.fetchall()
                    if ended:
                        for war_id, alliance_a, alliance_b in ended:
                            print(f"[WAR] War {war_id} ({alliance_a} vs {alliance_b}) ended")

                    conn.commit()

        except Exception as e:
            print(f"Error finalizing wars: {e}")

    def finalize_inactive_battles(self):
        """
        Mark battles as ended if they've been inactive for 30+ minutes.

        A battle is considered inactive if no kills have occurred in the system
        for 30 minutes.
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Find active battles with no recent kills
                    cur.execute("""
                        UPDATE battles
                        SET status = 'ended',
                            ended_at = last_kill_at + INTERVAL '30 minutes',
                            duration_minutes = EXTRACT(EPOCH FROM (last_kill_at - started_at)) / 60
                        WHERE status = 'active'
                          AND last_kill_at < NOW() - INTERVAL '30 minutes'
                        RETURNING battle_id, solar_system_id, total_kills, total_isk_destroyed, duration_minutes
                    """)

                    finalized = cur.fetchall()
                    conn.commit()

                    if finalized:
                        for battle_id, system_id, kills, isk, duration in finalized:
                            print(f"[BATTLE] Battle {battle_id} in system {system_id} ended: {kills} kills, {isk/1_000_000:.1f}M ISK, {duration:.0f} min")

                            # Send final battle alert
                            final_stats = {
                                'total_kills': kills,
                                'total_isk': isk,
                                'duration_minutes': int(duration or 0)
                            }
                            asyncio.create_task(self.send_battle_ended_alert(battle_id, system_id, final_stats))

        except Exception as e:
            print(f"Error finalizing battles: {e}")
