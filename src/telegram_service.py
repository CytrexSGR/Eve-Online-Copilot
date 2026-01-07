"""
Telegram Bot Service - Send messages to Telegram channels

Provides async methods to send messages to configured Telegram channels.
"""

import aiohttp
from typing import Optional
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_ALERTS_CHANNEL, TELEGRAM_REPORTS_CHANNEL, TELEGRAM_ENABLED


class TelegramService:
    """Service for sending messages to Telegram channels"""

    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.alerts_channel = TELEGRAM_ALERTS_CHANNEL
        self.reports_channel = TELEGRAM_REPORTS_CHANNEL
        self.enabled = TELEGRAM_ENABLED
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = True
    ) -> bool:
        """
        Send a message to a Telegram chat/channel.

        Args:
            chat_id: Channel ID or username (e.g., "@infinimind_eve_alerts" or "-1001234567890")
            text: Message text (supports Markdown or HTML)
            parse_mode: "Markdown" or "HTML"
            disable_web_page_preview: Don't show link previews

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            print("Telegram is disabled")
            return False

        if not chat_id:
            print("No chat_id provided")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        error_text = await response.text()
                        print(f"Telegram API error ({response.status}): {error_text}")
                        return False

        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False

    async def send_alert(self, message: str) -> Optional[int]:
        """
        Send alert to the alerts channel.

        Args:
            message: Alert message (Markdown formatted)

        Returns:
            Message ID if sent successfully, None otherwise
        """
        if not self.alerts_channel:
            print("Alerts channel not configured")
            return None

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.alerts_channel,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            return result.get("result", {}).get("message_id")
                    else:
                        error_text = await response.text()
                        print(f"Telegram API error ({response.status}): {error_text}")
                        return None

        except Exception as e:
            print(f"Error sending Telegram alert: {e}")
            return None

    async def edit_message(self, message_id: int, new_text: str) -> bool:
        """
        Edit an existing message in the alerts channel.

        Args:
            message_id: ID of the message to edit
            new_text: New text for the message (Markdown formatted)

        Returns:
            True if edited successfully, False otherwise
        """
        if not self.enabled:
            print("Telegram is disabled")
            return False

        if not self.alerts_channel:
            print("Alerts channel not configured")
            return False

        url = f"{self.base_url}/editMessageText"
        payload = {
            "chat_id": self.alerts_channel,
            "message_id": message_id,
            "text": new_text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        error_text = await response.text()
                        print(f"Telegram edit error ({response.status}): {error_text}")
                        return False

        except Exception as e:
            print(f"Error editing Telegram message: {e}")
            return False

    async def send_report(self, message: str) -> bool:
        """
        Send report to the reports channel.

        Args:
            message: Report message (Markdown formatted)

        Returns:
            True if sent successfully
        """
        if not self.reports_channel:
            print("Reports channel not configured")
            return False

        return await self.send_message(self.reports_channel, message)

    async def create_forum_topic(
        self,
        chat_id: str,
        name: str,
        icon_color: Optional[int] = None,
        icon_custom_emoji_id: Optional[str] = None
    ) -> dict:
        """
        Create a new forum topic in a supergroup.

        Args:
            chat_id: Chat ID of the supergroup
            name: Topic name (1-128 characters)
            icon_color: Color of the topic icon (optional)
            icon_custom_emoji_id: Custom emoji ID for topic icon (optional)

        Returns:
            Dict with topic info including message_thread_id
        """
        url = f"{self.base_url}/createForumTopic"
        payload = {
            "chat_id": chat_id,
            "name": name
        }

        if icon_color is not None:
            payload["icon_color"] = icon_color
        if icon_custom_emoji_id:
            payload["icon_custom_emoji_id"] = icon_custom_emoji_id

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    if response.status == 200 and result.get("ok"):
                        return result
                    else:
                        error_msg = result.get("description", await response.text())
                        print(f"Error creating topic: {error_msg}")
                        return {"ok": False, "error": error_msg}

        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_updates(self) -> dict:
        """
        Get bot updates (for testing and getting chat IDs).

        Returns:
            Dict with updates from Telegram API
        """
        url = f"{self.base_url}/getUpdates"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"ok": False, "error": await response.text()}

        except Exception as e:
            return {"ok": False, "error": str(e)}


# Singleton instance
telegram_service = TelegramService()
