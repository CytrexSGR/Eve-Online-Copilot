#!/usr/bin/env python3
"""
Create Telegram Forum Topics for infinimind-eve channel

Creates two topics:
1. Alerts - for hotspot alerts
2. Reports - for 24h battle reports
"""

import asyncio
from telegram_service import telegram_service
from config import TELEGRAM_ALERTS_CHANNEL

async def main():
    print("=" * 60)
    print("Creating Telegram Forum Topics")
    print("=" * 60)
    print()

    channel_id = TELEGRAM_ALERTS_CHANNEL
    print(f"Channel ID: {channel_id}")
    print()

    # Create Alerts topic
    print("1. Creating 'Alerts' topic...")
    result = await telegram_service.create_forum_topic(
        chat_id=channel_id,
        name="⚠️ Alerts",
        icon_color=0xFF0000  # Red
    )

    if result.get("ok"):
        topic_data = result.get("result", {})
        alerts_thread_id = topic_data.get("message_thread_id")
        print(f"   ✅ Created! Thread ID: {alerts_thread_id}")
        print(f"   Name: {topic_data.get('name')}")
        print()
    else:
        print(f"   ❌ Failed: {result.get('error')}")
        print()

    # Create Reports topic
    print("2. Creating 'Reports' topic...")
    result = await telegram_service.create_forum_topic(
        chat_id=channel_id,
        name="📊 Reports",
        icon_color=0x0000FF  # Blue
    )

    if result.get("ok"):
        topic_data = result.get("result", {})
        reports_thread_id = topic_data.get("message_thread_id")
        print(f"   ✅ Created! Thread ID: {reports_thread_id}")
        print(f"   Name: {topic_data.get('name')}")
        print()
    else:
        print(f"   ❌ Failed: {result.get('error')}")
        print()

    print("=" * 60)
    print("Next steps:")
    print("1. Check your Telegram channel - you should see the topics!")
    print("2. Update config.py with the thread IDs")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
