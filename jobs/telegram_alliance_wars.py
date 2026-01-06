#!/usr/bin/env python3
"""
Telegram Alliance War Tracker - Cron Job

Tracks active alliance conflicts with kill/death ratios and ISK efficiency.
Runs every 30 minutes via cron.
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
    Format alliance war tracker report for Telegram (Markdown).

    Args:
        report: Alliance war report dict from zkill_live_service

    Returns:
        Formatted Markdown string
    """
    wars = report['wars'][:5]  # Top 5 active wars
    total_wars = report['total_wars']

    # Build message
    msg = "⚔️ **ALLIANCE WAR TRACKER**\n\n"
    msg += f"🌌 _Active Conflicts: {total_wars}_\n\n"

    if not wars:
        msg += "✅ _No major conflicts detected in last 24h_\n"
        msg += "⏱️ _Report updates every 30 minutes_"
        return msg

    # Top 5 conflicts
    msg += "🔥 **Most Active Conflicts**\n\n"
    for i, war in enumerate(wars, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."

        alliance_a = war['alliance_a_name']
        alliance_b = war['alliance_b_name']
        kills_a = war['kills_by_a']
        kills_b = war['kills_by_b']
        total_kills = war['total_kills']
        kill_ratio_a = war['kill_ratio_a']
        isk_efficiency_a = war['isk_efficiency_a']
        winner = war['winner']
        active_systems = war['active_systems']

        # Winner emoji and status
        if winner == "a":
            status_emoji = "🟢"
            status_text = f"{alliance_a} winning"
        elif winner == "b":
            status_emoji = "🔴"
            status_text = f"{alliance_b} winning"
        elif winner == "contested":
            status_emoji = "🟡"
            status_text = "Contested"
        else:
            status_emoji = "⚪"
            status_text = "Balanced"

        msg += f"{emoji} **{alliance_a}** vs **{alliance_b}**\n"
        msg += f"{status_emoji} Status: *{status_text}*\n"
        msg += f"• Total Kills: `{total_kills}` ({kills_a} vs {kills_b})\n"
        msg += f"• Kill Ratio: `{kill_ratio_a:.2f}:1` (A:B)\n"
        msg += f"• ISK Efficiency: `{isk_efficiency_a*100:.1f}%`\n"
        msg += f"• Active Systems: `{active_systems}`\n\n"

    msg += "⏱️ _Report updates every 30 minutes_"

    return msg


async def main():
    """Generate and send alliance war tracker report to Telegram"""
    try:
        print("Generating alliance war tracker report...")

        # Get report
        report = await zkill_live_service.get_alliance_war_tracker(limit=5)

        if not report:
            print("No war data available")
            return

        # Format for Telegram
        message = format_report_for_telegram(report)

        # Send to Telegram
        print("Sending report to Telegram...")
        success = await telegram_service.send_report(message)

        if success:
            print("✅ Alliance war tracker report sent successfully")
        else:
            print("❌ Failed to send report")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
