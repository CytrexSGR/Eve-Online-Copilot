#!/usr/bin/env python3
"""
Telegram 24h Battle Report - Cron Job

Fetches the 24h battle report and posts it to Telegram reports channel.
Runs every 10 minutes via cron.
"""

import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zkillboard_live_service import zkill_live_service
from telegram_service import telegram_service


def format_report_for_telegram(report: dict) -> str:
    """
    Format 24h battle report for Telegram (Markdown).

    Args:
        report: Battle report dict from zkill_live_service

    Returns:
        Formatted Markdown string
    """
    global_data = report['global']
    regions = report['regions'][:5]  # Top 5 regions

    # Build message
    msg = "⚔️ **24H BATTLE REPORT**\n\n"

    # Global summary
    msg += f"🌌 **Galactic Summary**\n"
    msg += f"• Total Kills: `{global_data['total_kills']:,}`\n"
    msg += f"• ISK Destroyed: `{global_data['total_isk_destroyed']/1_000_000_000:.1f}B` ISK\n"
    msg += f"• Hottest Region: *{global_data['most_active_region']}*\n"
    msg += f"• Most Expensive: *{global_data['most_expensive_region']}*\n"
    msg += "\n"

    # Top 5 regions
    msg += "📍 **Top 5 Regions**\n\n"
    for i, region in enumerate(regions, 1):
        msg += f"**{i}. {region['region_name']}**\n"
        msg += f"• Kills: `{region['kills']}`\n"
        msg += f"• ISK: `{region['total_isk_destroyed']/1_000_000:.0f}M`\n"

        # Top system
        if region.get('top_systems'):
            top_sys = region['top_systems'][0]
            msg += f"• Top System: *{top_sys['system_name']}* ({top_sys['kills']} kills)\n"

        # Top ship
        if region.get('top_ships'):
            top_ship = region['top_ships'][0]
            msg += f"• Most Lost: *{top_ship['ship_name']}* ({top_ship['losses']}x)\n"

        # Top destroyed items
        if region.get('top_destroyed_items'):
            top_items = region['top_destroyed_items'][:2]
            msg += f"• Hot Items:\n"
            for item in top_items:
                msg += f"  - {item['item_name']}: `{item['quantity_destroyed']:,}x`\n"

        msg += "\n"

    msg += "⏱️ _Report updates every 10 minutes_"

    return msg


async def main():
    """Generate and send 24h battle report to Telegram"""
    try:
        print("Generating 24h battle report...")

        # Get report
        report = zkill_live_service.get_24h_battle_report()

        if not report:
            print("No report data available")
            return

        # Format for Telegram
        message = format_report_for_telegram(report)

        # Send to Telegram
        print("Sending report to Telegram...")
        success = await telegram_service.send_report(message)

        if success:
            print("✅ Report sent successfully")
        else:
            print("❌ Failed to send report")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
