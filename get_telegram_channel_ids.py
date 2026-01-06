#!/usr/bin/env python3
"""
Helper Script: Get Telegram Channel IDs

This script helps you find your Telegram channel IDs.

Steps:
1. Add your bot (@infinimind_eve_bot) as admin to your channels
2. Send a test message to each channel (tag the bot with @infinimind_eve_bot)
3. Run this script to see the channel IDs
"""

import asyncio
from telegram_service import telegram_service


async def main():
    print("=" * 60)
    print("Telegram Channel ID Helper")
    print("=" * 60)
    print()
    print("Getting recent updates from Telegram...")
    print()

    updates = await telegram_service.get_updates()

    if not updates.get('ok'):
        print(f"❌ Error: {updates.get('error')}")
        return

    results = updates.get('result', [])

    if not results:
        print("No updates found!")
        print()
        print("Steps to get channel IDs:")
        print("1. Add @infinimind_eve_bot as admin to your channels")
        print("2. Send a test message to each channel")
        print("3. Tag the bot in the message: @infinimind_eve_bot")
        print("4. Run this script again")
        return

    print(f"Found {len(results)} updates:\n")

    for update in results:
        # Channel post
        if 'channel_post' in update:
            post = update['channel_post']
            chat = post['chat']
            print(f"📢 Channel: {chat.get('title', 'Unknown')}")
            print(f"   ID: {chat['id']}")
            print(f"   Username: @{chat.get('username', 'N/A')}")
            print(f"   Message: {post.get('text', 'N/A')[:50]}...")
            print()

        # Group message
        elif 'message' in update:
            msg = update['message']
            chat = msg['chat']
            print(f"💬 Chat: {chat.get('title', chat.get('first_name', 'Unknown'))}")
            print(f"   ID: {chat['id']}")
            print(f"   Type: {chat['type']}")
            print(f"   Message: {msg.get('text', 'N/A')[:50]}...")
            print()

    print("=" * 60)
    print("Copy the channel IDs and add them to config.py:")
    print()
    print('TELEGRAM_ALERTS_CHANNEL = "-1001234567890"  # Replace with your alerts channel ID')
    print('TELEGRAM_REPORTS_CHANNEL = "-1001234567890"  # Replace with your reports channel ID')
    print()
    print("Or use channel username:")
    print('TELEGRAM_ALERTS_CHANNEL = "@infinimind_eve_alerts"')
    print('TELEGRAM_REPORTS_CHANNEL = "@infinimind_eve_reports"')


if __name__ == "__main__":
    asyncio.run(main())
