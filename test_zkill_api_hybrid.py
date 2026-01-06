#!/usr/bin/env python3
"""
Test zKillboard API + ESI hybrid approach
"""

import asyncio
import sys
from zkillboard_live_service import zkill_live_service


async def test_hybrid():
    """Test the hybrid zkillboard API + ESI approach"""
    print("=" * 60)
    print("zKillboard API + ESI Hybrid Test")
    print("=" * 60)

    # Test 1: Fetch recent kills from zkillboard
    print("\n[1/4] Fetching recent kills from zkillboard API...")
    try:
        zkb_kills = await zkill_live_service.fetch_recent_kills()
        print(f"✓ Fetched {len(zkb_kills)} kill entries")

        if zkb_kills:
            first_kill = zkb_kills[0]
            print(f"  Sample: killmail_id={first_kill.get('killmail_id')}")
            print(f"  Hash: {first_kill.get('zkb', {}).get('hash', 'N/A')[:20]}...")
        else:
            print("⚠ No kills available")
            return False

    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 2: Fetch full killmail from ESI
    print("\n[2/4] Fetching full killmail from ESI...")
    try:
        if zkb_kills:
            killmail_id = zkb_kills[0].get('killmail_id')
            hash_str = zkb_kills[0].get('zkb', {}).get('hash')

            full_km = await zkill_live_service.fetch_killmail_from_esi(killmail_id, hash_str)
            if full_km:
                print(f"✓ Fetched full killmail from ESI")
                print(f"  System: {full_km.get('solar_system_id')}")
                print(f"  Ship: {full_km.get('victim', {}).get('ship_type_id')}")
                print(f"  Attackers: {len(full_km.get('attackers', []))}")
            else:
                print("⚠ Failed to fetch from ESI")
                return False
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 3: Parse killmail
    print("\n[3/4] Parsing killmail...")
    try:
        kill = zkill_live_service.parse_killmail(full_km, zkb_kills[0].get('zkb', {}))
        if kill:
            print(f"✓ Parsed killmail")
            print(f"  Killmail ID: {kill.killmail_id}")
            print(f"  System: {kill.solar_system_id}")
            print(f"  Region: {kill.region_id}")
            print(f"  Ship: {kill.ship_type_id}")
            print(f"  Value: {kill.ship_value:,.0f} ISK")
            print(f"  Destroyed items: {len(kill.destroyed_items)}")
            print(f"  Dropped items: {len(kill.dropped_items)}")
        else:
            print("⚠ Failed to parse (might be wormhole)")
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Store in Redis
    print("\n[4/4] Testing Redis storage...")
    try:
        if kill:
            zkill_live_service.store_live_kill(kill)
            print("✓ Stored in Redis")

            # Query it back
            recent = zkill_live_service.get_recent_kills(region_id=kill.region_id, limit=5)
            print(f"✓ Query works: Found {len(recent)} kills in region {kill.region_id}")
        else:
            print("⚠ Skipping (no valid kill)")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("Hybrid approach works! ✅")
    print("=" * 60)
    print("\nReady for production:")
    print("  python3 -m jobs.zkill_live_listener --verbose")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = asyncio.run(test_hybrid())
    sys.exit(0 if success else 1)
