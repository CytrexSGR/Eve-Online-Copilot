#!/usr/bin/env python3
"""
Battle Cleanup Job

Automatically ends battles that are:
1. Older than 2 hours (no recent activity)
2. Have 0 kills (no real data)

Should run every 30 minutes via cron.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db_connection
from datetime import datetime

def cleanup_old_battles():
    """Mark old battles as ended"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # End battles that are >2 hours old OR have 0 kills
                cur.execute("""
                    UPDATE battles
                    SET
                        status = 'ended',
                        ended_at = last_kill_at,
                        duration_minutes = EXTRACT(EPOCH FROM (last_kill_at - started_at)) / 60
                    WHERE status = 'active'
                      AND (
                        last_kill_at < NOW() - INTERVAL '2 hours'
                        OR total_kills = 0
                      )
                    RETURNING battle_id, solar_system_id, total_kills,
                        EXTRACT(EPOCH FROM (NOW() - last_kill_at)) / 3600 as hours_since_last_kill
                """)

                ended_battles = cur.fetchall()
                conn.commit()

                if ended_battles:
                    print(f"[{datetime.now()}] Ended {len(ended_battles)} old battles:")
                    for battle_id, system_id, kills, hours in ended_battles:
                        print(f"  Battle {battle_id} in system {system_id}: {kills} kills, {hours:.1f}h old")
                else:
                    print(f"[{datetime.now()}] No old battles to clean up")

                # Get current active battles count
                cur.execute("SELECT COUNT(*) FROM battles WHERE status = 'active'")
                active_count = cur.fetchone()[0]
                print(f"[{datetime.now()}] {active_count} battles still active")

                return len(ended_battles)

    except Exception as e:
        print(f"[{datetime.now()}] ERROR cleaning up battles: {e}")
        return 0

if __name__ == "__main__":
    ended_count = cleanup_old_battles()
    print(f"[{datetime.now()}] Battle cleanup complete: {ended_count} battles ended")
