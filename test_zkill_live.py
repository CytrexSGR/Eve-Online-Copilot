#!/usr/bin/env python3
"""
Test script for zKillboard Live Service

Tests:
1. Service initialization
2. RedisQ connection
3. Single killmail fetch
4. Data storage in Redis
5. Query methods
"""

import asyncio
import sys
from zkillboard_live_service import zkill_live_service


async def test_service():
    """Test the zKillboard live service"""
    print("=" * 60)
    print("zKillboard Live Service Test")
    print("=" * 60)

    # Test 1: Service initialization
    print("\n[1/5] Testing service initialization...")
    try:
        assert zkill_live_service is not None
        print("✓ Service initialized")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 2: Redis connection
    print("\n[2/5] Testing Redis connection...")
    try:
        ping = zkill_live_service.redis_client.ping()
        assert ping
        print("✓ Redis connected")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 3: System-Region mapping
    print("\n[3/5] Testing system-region mapping...")
    try:
        assert len(zkill_live_service.system_region_map) > 0
        print(f"✓ Loaded {len(zkill_live_service.system_region_map)} systems")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 4: Fetch single killmail from RedisQ
    print("\n[4/5] Testing RedisQ fetch (may take 10-30s)...")
    try:
        package = await zkill_live_service.fetch_next_kill()

        if package:
            print(f"✓ Fetched killmail package")

            # Parse it
            kill = zkill_live_service.parse_killmail(package)
            if kill:
                print(f"  - Killmail ID: {kill.killmail_id}")
                print(f"  - System: {kill.solar_system_id}")
                print(f"  - Region: {kill.region_id}")
                print(f"  - Ship: {kill.ship_type_id}")
                print(f"  - Value: {kill.ship_value:,.0f} ISK")
                print(f"  - Destroyed items: {len(kill.destroyed_items)}")
                print(f"  - Dropped items: {len(kill.dropped_items)}")

                # Store it
                zkill_live_service.store_live_kill(kill)
                print("✓ Stored in Redis")

                # Test query
                recent = zkill_live_service.get_recent_kills(
                    region_id=kill.region_id,
                    limit=1
                )
                if recent:
                    print(f"✓ Query works: Found {len(recent)} kills")
                else:
                    print("⚠ Query returned no results (might be timing)")

            else:
                print("⚠ Kill was parsed but not valid (maybe wormhole)")
        else:
            print("⚠ No killmail available (RedisQ queue empty)")
            print("  This is normal if no kills in last few seconds")

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 5: Service statistics
    print("\n[5/5] Testing service statistics...")
    try:
        stats = zkill_live_service.get_stats()
        print(f"✓ Stats retrieved:")
        print(f"  - Kills (24h): {stats['total_kills_24h']}")
        print(f"  - Active hotspots: {stats['active_hotspots']}")
        print(f"  - Redis connected: {stats['redis_connected']}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_service())
    sys.exit(0 if success else 1)
