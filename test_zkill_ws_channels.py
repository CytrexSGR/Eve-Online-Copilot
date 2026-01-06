#!/usr/bin/env python3
"""
Test different zKillboard WebSocket channels
"""

import asyncio
import json
import aiohttp


async def test_channel(channel_name: str, timeout: int = 30):
    """Test a specific channel"""
    url = "wss://zkillboard.com/websocket/"
    headers = {
        "User-Agent": "EVE-CoPilot/1.0",
        "Origin": "https://zkillboard.com"
    }

    print(f"\n{'='*60}")
    print(f"Testing channel: {channel_name}")
    print(f"{'='*60}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url, headers=headers) as ws:
                # Try subscription
                await ws.send_json({"action": "sub", "channel": channel_name})
                print(f"✓ Subscribed to '{channel_name}'")

                msg_count = 0
                kill_count = 0

                try:
                    async with asyncio.timeout(timeout):
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                msg_count += 1
                                data = json.loads(msg.data)

                                # Check if it's a killmail
                                if "killmail_id" in data or "killmail" in data:
                                    kill_count += 1
                                    print(f"\n🎯 KILLMAIL #{kill_count}")
                                    print(json.dumps(data, indent=2)[:500])

                                    if kill_count >= 2:
                                        print(f"\n✓ Found killmails on channel '{channel_name}'!")
                                        return True

                                # Status messages
                                elif data.get("action") == "tqStatus":
                                    if msg_count == 1:
                                        print(f"  Status: {data}")

                except asyncio.TimeoutError:
                    print(f"\n⏱ Timeout - {msg_count} messages, {kill_count} kills")

    except Exception as e:
        print(f"✗ Error: {e}")

    return False


async def main():
    """Test various channel names"""
    channels = [
        "public",           # Standard public channel
        "killstream",       # Possible kill stream
        "kills",            # Simple kills
        "",                 # Empty/default
        "all",              # All kills
        "region:10000002",  # Region-specific (The Forge)
    ]

    print("Testing zKillboard WebSocket Channels")
    print("This will try different channel names to find killmails\n")

    for channel in channels:
        found = await test_channel(channel, timeout=20)
        if found:
            print(f"\n✅ SUCCESS: Channel '{channel}' works!")
            break
        await asyncio.sleep(1)  # Brief pause between tests

    print("\n" + "="*60)
    print("Channel testing complete")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
