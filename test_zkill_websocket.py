#!/usr/bin/env python3
"""
Test zKillboard WebSocket Connection

Tests the WebSocket endpoint to see if it works and what format it uses.
"""

import asyncio
import json
import aiohttp


async def test_websocket():
    """Test zKillboard WebSocket"""
    print("=" * 60)
    print("zKillboard WebSocket Test")
    print("=" * 60)

    url = "wss://zkillboard.com/websocket/"

    print(f"\nConnecting to: {url}")
    print("Waiting for killmails (max 60 seconds)...\n")

    try:
        headers = {
            "User-Agent": "EVE-CoPilot/1.0 (Live Combat Intelligence)",
            "Origin": "https://zkillboard.com"
        }

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url, headers=headers) as ws:
                print("✓ WebSocket connected!")

                # Try to subscribe to public channel
                # Common formats: {"action":"sub","channel":"public"}
                subscribe_msg = {
                    "action": "sub",
                    "channel": "public"
                }

                print(f"Sending subscription: {subscribe_msg}")
                await ws.send_json(subscribe_msg)

                # Listen for messages
                kill_count = 0
                status_count = 0
                timeout_seconds = 120  # Wait 2 minutes

                try:
                    async with asyncio.timeout(timeout_seconds):
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                kill_count += 1

                                # Parse message
                                try:
                                    data = json.loads(msg.data)

                                    # Skip status messages
                                    if data.get("action") == "tqStatus":
                                        status_count += 1
                                        if status_count % 10 == 1:
                                            print(f"[Status] TQ: {data.get('tqStatus')}, Players: {data.get('tqCount')}, Kills/min: {data.get('kills')}")
                                        continue

                                    # Real killmail
                                    print(f"\n[Kill #{kill_count}]")
                                    print(f"Raw message preview:")
                                    print(json.dumps(data, indent=2)[:800])

                                    # Try to extract key info
                                    if isinstance(data, dict):
                                        if "killmail_id" in data:
                                            print(f"\n✓ Found killmail_id: {data['killmail_id']}")
                                        if "killmail" in data:
                                            km = data["killmail"]
                                            print(f"\n✓ Found killmail structure")
                                            print(f"  - Killmail ID: {km.get('killmail_id')}")
                                            print(f"  - System: {km.get('solar_system_id')}")
                                        if "zkb" in data:
                                            zkb = data["zkb"]
                                            print(f"✓ Found zkb data")
                                            print(f"  - Value: {zkb.get('totalValue', 0):,.0f} ISK")

                                    # Stop after 5 real kills to see the pattern
                                    if kill_count >= 5:
                                        print("\n✓ Received 5 kills, pattern identified!")
                                        break

                                except json.JSONDecodeError:
                                    print(f"Non-JSON message: {msg.data[:200]}")

                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                print(f"WebSocket error: {ws.exception()}")
                                break

                except asyncio.TimeoutError:
                    print(f"\n⏱ Timeout after {timeout_seconds}s")
                    if kill_count == 0:
                        print("⚠ No killmails received (WebSocket might not be active)")

                print(f"\nTotal kills received: {kill_count}")

    except aiohttp.ClientConnectorError as e:
        print(f"✗ Connection failed: {e}")
        print("WebSocket endpoint might not exist or be unavailable")
        return False

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)

    return True


if __name__ == "__main__":
    asyncio.run(test_websocket())
