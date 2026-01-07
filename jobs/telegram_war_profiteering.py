#!/usr/bin/env python3
"""
Telegram War Profiteering Report - Cron Job

Identifies market opportunities from destroyed items in combat.
Runs daily via cron (suggested: 06:00 UTC).
"""

import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.zkillboard_live_service import zkill_live_service
from src.telegram_service import telegram_service


def format_report_for_telegram(report: dict) -> str:
    """
    Format war profiteering report for Telegram (Markdown).

    Args:
        report: Profiteering report dict from zkill_live_service

    Returns:
        Formatted Markdown string
    """
    items = report.get('items', [])[:15]  # Top 15
    total_opportunity_value = float(report.get('total_opportunity_value', 0))

    # Build message
    msg = "💰 **WAR PROFITEERING DAILY DIGEST**\n\n"
    msg += "🎯 _Market Opportunities from Combat Losses_\n\n"

    # Summary stats
    msg += f"📊 **Summary**\n"
    msg += f"• Total Opportunity Value: `{total_opportunity_value/1_000_000_000:.1f}B` ISK\n"
    msg += f"• Hot Items Tracked: `{len(items)}`\n"
    msg += f"• Period: Last 24h\n\n"

    # Top opportunities
    msg += "🔥 **Top Market Opportunities**\n\n"
    for i, item in enumerate(items[:10], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."

        item_name = item['item_name']
        quantity = item['quantity_destroyed']
        market_price = float(item['market_price'])
        opportunity_value = float(item['opportunity_value'])

        msg += f"{emoji} **{item_name}**\n"
        msg += f"• Destroyed: `{quantity:,}x`\n"
        msg += f"• Market Price: `{market_price/1_000_000:.1f}M` ISK/unit\n"
        msg += f"• Opportunity: `{opportunity_value/1_000_000_000:.2f}B` ISK\n\n"

    msg += "💡 _Stock these items in combat zones for maximum profit!_\n"
    msg += "⏱️ _Report updates daily at 06:00 UTC_"

    return msg


async def main():
    """Generate and send war profiteering report to Telegram"""
    try:
        print("Generating war profiteering report...")

        # Get report
        report = zkill_live_service.get_war_profiteering_report(limit=20)

        if not report or not report.get('items'):
            print("No profiteering opportunities available")
            return

        # Format for Telegram
        message = format_report_for_telegram(report)

        # Send to Telegram
        print("Sending report to Telegram...")
        success = await telegram_service.send_report(message)

        if success:
            print("✅ War profiteering report sent successfully")
        else:
            print("❌ Failed to send report")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
