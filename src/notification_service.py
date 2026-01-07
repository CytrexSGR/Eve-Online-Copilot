"""
EVE Co-Pilot Notification Service
Handles Discord webhook notifications for market alerts
"""

import requests
from datetime import datetime
from typing import Dict, List, Optional
from config import DISCORD_WEBHOOK_URL


class NotificationService:
    """Service for sending notifications via Discord webhooks"""

    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or DISCORD_WEBHOOK_URL
        self.session = requests.Session()

    def send_discord_webhook(
        self,
        content: Dict = None,
        embeds: List[Dict] = None,
        username: str = "EVE Co-Pilot",
        avatar_url: str = None
    ) -> Dict:
        """
        Send a message to Discord via webhook.

        Args:
            content: Optional text content
            embeds: List of embed objects
            username: Bot username to display
            avatar_url: Bot avatar URL

        Returns:
            Dict with success status
        """
        if not self.webhook_url:
            return {"error": "DISCORD_WEBHOOK_URL not configured"}

        payload = {
            "username": username,
        }

        if avatar_url:
            payload["avatar_url"] = avatar_url

        if content:
            payload["content"] = content.get("text", "")

        if embeds:
            payload["embeds"] = embeds

        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )

            if response.status_code in (200, 204):
                return {"success": True, "status": response.status_code}
            else:
                return {
                    "error": f"Discord API error: {response.status_code}",
                    "details": response.text
                }

        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    def send_profit_alert(
        self,
        item_name: str,
        type_id: int,
        margin_percent: float,
        profit_per_run: float,
        investment: float,
        material_cost: float = None,
        sell_price: float = None,
        runs: int = 1,
        me: int = 10
    ) -> Dict:
        """
        Send a profit opportunity alert to Discord.

        Args:
            item_name: Name of the item
            type_id: Item type ID
            margin_percent: Profit margin percentage
            profit_per_run: Profit in ISK per run
            investment: Total investment required
            material_cost: Cost of materials
            sell_price: Expected sell price
            runs: Number of runs
            me: Material Efficiency level
        """
        # Color based on margin (green gradient)
        if margin_percent >= 50:
            color = 0x00FF00  # Bright green
        elif margin_percent >= 30:
            color = 0x32CD32  # Lime green
        elif margin_percent >= 20:
            color = 0x7CFC00  # Lawn green
        else:
            color = 0x9ACD32  # Yellow green

        embed = {
            "title": f"Profitable Blueprint Found",
            "description": f"**{item_name}**",
            "color": color,
            "fields": [
                {
                    "name": "Margin",
                    "value": f"**{margin_percent:.1f}%**",
                    "inline": True
                },
                {
                    "name": "Profit/Run",
                    "value": f"**{profit_per_run:,.0f} ISK**",
                    "inline": True
                },
                {
                    "name": "Investment",
                    "value": f"{investment:,.0f} ISK",
                    "inline": True
                }
            ],
            "footer": {
                "text": f"Type ID: {type_id} | ME: {me} | Runs: {runs}"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # Add optional fields
        if material_cost and sell_price:
            embed["fields"].extend([
                {
                    "name": "Material Cost",
                    "value": f"{material_cost:,.0f} ISK",
                    "inline": True
                },
                {
                    "name": "Sell Price",
                    "value": f"{sell_price:,.0f} ISK",
                    "inline": True
                }
            ])

        return self.send_discord_webhook(embeds=[embed])

    def send_bulk_profit_alert(
        self,
        opportunities: List[Dict],
        scan_stats: Dict = None
    ) -> Dict:
        """
        Send multiple profit opportunities in a single message.

        Args:
            opportunities: List of opportunity dicts with keys:
                - name, type_id, margin_percent, profit, investment
            scan_stats: Optional scan statistics
        """
        if not opportunities:
            return {"error": "No opportunities to send"}

        embeds = []

        # Header embed with stats
        if scan_stats:
            header_embed = {
                "title": "Market Hunter Report",
                "description": f"Found **{len(opportunities)}** profitable opportunities",
                "color": 0x00BFFF,  # Deep sky blue
                "fields": [
                    {
                        "name": "Blueprints Scanned",
                        "value": str(scan_stats.get("total_scanned", "N/A")),
                        "inline": True
                    },
                    {
                        "name": "Scan Time",
                        "value": f"{scan_stats.get('scan_time', 0):.1f}s",
                        "inline": True
                    },
                    {
                        "name": "API Calls",
                        "value": str(scan_stats.get("api_calls", "N/A")),
                        "inline": True
                    }
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            embeds.append(header_embed)

        # Create embeds for each opportunity (max 9 per message, header uses 1 slot)
        for i, opp in enumerate(opportunities[:9]):
            margin = opp.get("margin_percent", 0)

            # Color gradient
            if margin >= 50:
                color = 0x00FF00
            elif margin >= 30:
                color = 0x32CD32
            elif margin >= 20:
                color = 0x7CFC00
            else:
                color = 0x9ACD32

            embed = {
                "title": f"#{i+1} {opp.get('name', 'Unknown')}",
                "color": color,
                "fields": [
                    {
                        "name": "ROI",
                        "value": f"**{margin:.1f}%**",
                        "inline": True
                    },
                    {
                        "name": "Profit",
                        "value": f"**{opp.get('profit', 0):,.0f} ISK**",
                        "inline": True
                    },
                    {
                        "name": "Investment",
                        "value": f"{opp.get('investment', opp.get('material_cost', 0)):,.0f} ISK",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": f"Type ID: {opp.get('type_id', 'N/A')}"
                }
            }
            embeds.append(embed)

        return self.send_discord_webhook(embeds=embeds)

    def send_test_message(self) -> Dict:
        """Send a test message to verify webhook configuration."""
        embed = {
            "title": "EVE Co-Pilot Test",
            "description": "Discord webhook is working correctly!",
            "color": 0x00FF00,
            "fields": [
                {
                    "name": "Status",
                    "value": "Connected",
                    "inline": True
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        return self.send_discord_webhook(embeds=[embed])


# Global notification service instance
notification_service = NotificationService()
