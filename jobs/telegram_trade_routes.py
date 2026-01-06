#!/usr/bin/env python3
"""
Telegram Trade Route Danger Map - Cron Job

Analyzes danger levels along major trade routes between hubs.
Runs daily via cron (suggested: 08:00 UTC).
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
    Format trade route danger map for Telegram (Markdown).

    Args:
        report: Trade route report dict from zkill_live_service

    Returns:
        Formatted Markdown string
    """
    routes = report['routes']
    danger_scale = report['danger_scale']

    # Build message
    msg = "🛣️ **TRADE ROUTE DANGER MAP**\n\n"
    msg += "🚨 _Hauler Alert: HighSec Route Safety Analysis_\n\n"

    # Summary stats
    extreme_routes = sum(1 for r in routes if r['danger_level'] == 'EXTREME')
    high_routes = sum(1 for r in routes if r['danger_level'] == 'HIGH')
    safe_routes = sum(1 for r in routes if r['danger_level'] == 'SAFE')

    msg += f"📊 **Route Safety Summary**\n"
    msg += f"• 🔴 Extreme Danger: `{extreme_routes}` routes\n"
    msg += f"• 🟠 High Danger: `{high_routes}` routes\n"
    msg += f"• 🟢 Safe: `{safe_routes}` routes\n"
    msg += f"• Period: Last 24h\n\n"

    # Routes by danger level
    msg += "🗺️ **Trade Hub Routes**\n\n"
    for route in routes:
        from_hub = route['from_hub']
        to_hub = route['to_hub']
        danger_level = route['danger_level']
        avg_danger = route['avg_danger_score']
        total_jumps = route['total_jumps']
        max_danger = route['max_danger_system']

        # Danger level emoji
        if danger_level == "EXTREME":
            emoji = "🔴"
        elif danger_level == "HIGH":
            emoji = "🟠"
        elif danger_level == "MODERATE":
            emoji = "🟡"
        elif danger_level == "LOW":
            emoji = "🟢"
        else:
            emoji = "✅"

        msg += f"{emoji} **{from_hub} → {to_hub}**\n"
        msg += f"• Danger: *{danger_level}* ({avg_danger:.1f} avg)\n"
        msg += f"• Jumps: `{total_jumps}`\n"

        if max_danger and max_danger['danger_score'] > 10:
            msg += f"• ⚠️ Hotspot: *{max_danger['system_name']}* (danger: {max_danger['danger_score']})\n"

        msg += "\n"

    # Danger scale legend
    msg += "📈 **Danger Scale**\n"
    msg += f"• ✅ SAFE: {danger_scale['SAFE']}\n"
    msg += f"• 🟢 LOW: {danger_scale['LOW']}\n"
    msg += f"• 🟡 MODERATE: {danger_scale['MODERATE']}\n"
    msg += f"• 🟠 HIGH: {danger_scale['HIGH']}\n"
    msg += f"• 🔴 EXTREME: {danger_scale['EXTREME']}\n\n"

    msg += "💡 _Use scout alts on EXTREME/HIGH routes!_\n"
    msg += "⏱️ _Report updates daily at 08:00 UTC_"

    return msg


async def main():
    """Generate and send trade route danger map to Telegram"""
    try:
        print("Generating trade route danger map...")

        # Get report
        report = zkill_live_service.get_trade_route_danger_map()

        if not report or not report.get('routes'):
            print("No route data available")
            return

        # Format for Telegram
        message = format_report_for_telegram(report)

        # Send to Telegram
        print("Sending report to Telegram...")
        success = await telegram_service.send_report(message)

        if success:
            print("✅ Trade route danger map sent successfully")
        else:
            print("❌ Failed to send report")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
