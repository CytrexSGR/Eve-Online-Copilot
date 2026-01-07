#!/usr/bin/env python3
"""Populate system_region_map from SDE data"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db_connection

def populate_system_region_map():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE system_region_map")
            cur.execute('''
                INSERT INTO system_region_map
                    (solar_system_id, solar_system_name, region_id, region_name,
                     constellation_id, security_status)
                SELECT
                    s."solarSystemID",
                    s."solarSystemName",
                    s."regionID",
                    r."regionName",
                    s."constellationID",
                    s."security"
                FROM "mapSolarSystems" s
                JOIN "mapRegions" r ON s."regionID" = r."regionID"
            ''')
            count = cur.rowcount
            conn.commit()
            print(f"Inserted {count} systems into system_region_map")
            return count

if __name__ == "__main__":
    populate_system_region_map()
