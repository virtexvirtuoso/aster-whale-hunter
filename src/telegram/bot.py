"""
Telegram Bot implementation for whale detection alerting system.
Provides complete integration with Telegram Bot API for real-time notifications.
"""
import asyncio
import logging
import os
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import aiohttp
import json
from urllib.parse import quote

from ..core.interfaces.reporting import (
    TelegramNotificationInterface,
    NotificationData,
    AlertSeverity,
    AlertType
)


class TelegramBot(TelegramNotificationInterface):
    """
    Complete Telegram Bot implementation for whale detection alerts.
    Supports rich formatting, inline keyboards, file sending, and user management.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token = config.get('bot_token') or os.getenv('TELEGRAM_BOT_TOKEN')
        self.api_base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_manager = None  # Will be injected
        self.logger = logging.getLogger(__name__)

        # Bot configuration
        self.max_message_length = 4096
        self.parse_mode = config.get('parse_mode', 'HTML')
        self.disable_web_page_preview = config.get('disable_web_page_preview', True)

        # Command handlers
        self.command_handlers: Dict[str, Callable] = {
            'start': self._handle_start,
            'help': self._handle_help,
            'subscribe': self._handle_subscribe,
            'unsubscribe': self._handle_unsubscribe,
            'status': self._handle_status,
            'alerts': self._handle_alerts,
            'settings': self._handle_settings
        }

    async def initialize(self):
        """Initialize the bot session and set up webhook if needed."""
        if not self.bot_token:
            raise ValueError("Telegram bot token is required")

        self.session = aiohttp.ClientSession()

        # Test connection and get bot info
        bot_info = await self._make_request('getMe')
        if bot_info:
            self.logger.info(f"Telegram bot initialized: @{bot_info.get('username')}")
        else:
            raise ConnectionError("Failed to connect to Telegram API")

    async def shutdown(self):
        """Clean shutdown of bot resources."""
        if self.session:
            await self.session.close()

    async def _make_request(self, method: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP request to Telegram Bot API."""
        if not self.session:
            await self.initialize()

        url = f"{self.api_base_url}/{method}"

        try:
            async with self.session.post(url, json=params) as response:
                data = await response.json()

                if data.get('ok'):
                    return data.get('result')
                else:
                    self.logger.error(f"Telegram API error: {data.get('description')}")
                    return None

        except Exception as e:
            self.logger.error(f"Request to {method} failed: {str(e)}")
            return None

    def format_message(self, notification: NotificationData) -> str:
        """Format notification message with rich HTML formatting."""
        severity_emoji = notification.severity.value

        # Base message structure
        message_parts = [
            f"{severity_emoji} <b>WHALE ALERT</b> {severity_emoji}",
            "",
            f"🎯 <b>Symbol:</b> {notification.symbol}",
            f"📊 <b>Type:</b> {notification.alert_type.value.replace('_', ' ').title()}",
            f"⚠️ <b>Severity:</b> {notification.severity.name}",
            ""
        ]

        # Add specific data based on alert type
        data = notification.data

        if notification.alert_type == AlertType.WHALE_TRADE:
            message_parts.extend([
                f"💰 <b>Volume:</b> ${data.get('volume', 'N/A'):,.2f}" if isinstance(data.get('volume'), (int, float)) else f"💰 <b>Volume:</b> {data.get('volume', 'N/A')}",
                f"💵 <b>Value:</b> ${data.get('trade_value', 'N/A'):,.2f}" if isinstance(data.get('trade_value'), (int, float)) else f"💵 <b>Value:</b> {data.get('trade_value', 'N/A')}",
                f"📈 <b>Price:</b> ${data.get('price', 'N/A')}" if data.get('price') else "",
                f"🔄 <b>Side:</b> {data.get('side', 'N/A').upper()}" if data.get('side') else ""
            ])
        elif notification.alert_type == AlertType.ACCUMULATION:
            message_parts.extend([
                f"📈 <b>Accumulation Period:</b> {data.get('period', 'N/A')}",
                f"💎 <b>Total Volume:</b> ${data.get('total_volume', 'N/A'):,.2f}" if isinstance(data.get('total_volume'), (int, float)) else f"💎 <b>Total Volume:</b> {data.get('total_volume', 'N/A')}",
                f"🎯 <b>Confidence:</b> {data.get('confidence', 0)*100:.1f}%" if data.get('confidence') else ""
            ])
        elif notification.alert_type == AlertType.MANIPULATION:
            message_parts.extend([
                f"🎭 <b>Pattern:</b> {data.get('pattern', 'N/A')}",
                f"📊 <b>Anomaly Score:</b> {data.get('anomaly_score', 'N/A')}",
                f"⏱️ <b>Duration:</b> {data.get('duration', 'N/A')}"
            ])

        # Add exchange information if available
        if data.get('exchange'):
            message_parts.append(f"🏪 <b>Exchange:</b> {data.get('exchange')}")

        # Add timestamp
        message_parts.extend([
            "",
            f"🕐 <b>Time:</b> {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            notification.message
        ])

        # Add trading links if available
        trading_links = self._generate_trading_links(notification.symbol)
        if trading_links:
            message_parts.extend(["", "🔗 <b>Quick Trade:</b>"] + trading_links)

        return "\n".join(filter(None, message_parts))

    def _generate_trading_links(self, symbol: str) -> List[str]:
        """Generate clickable trading platform links."""
        base_symbol = symbol.replace('USDT', '').replace('USD', '')

        links = [
            f'<a href="https://www.binance.com/en/trade/{symbol}">Binance</a>',
            f'<a href="https://pro.coinbase.com/trade/{base_symbol}-USD">Coinbase</a>',
            f'<a href="https://www.okx.com/trade-spot/{symbol.lower()}">OKX</a>'
        ]

        return [" | ".join(links)]

    async def send_notification(self, notification: NotificationData) -> bool:
        """Send notification to all subscribed users and channels."""
        if not self.enabled:
            return False

        try:
            formatted_message = self.format_message(notification)

            # Send to all subscribed users
            success_count = 0
            total_recipients = 0

            if self.user_manager:
                # Get subscribed users for this alert type
                subscribers = await self.user_manager.get_subscribers(
                    alert_type=notification.alert_type,
                    severity=notification.severity
                )

                for user_id in subscribers:
                    if await self.send_to_user(user_id, notification):
                        success_count += 1
                    total_recipients += 1

                # Send to configured channels
                channels = self.config.get('channels', [])
                for channel in channels:
                    if await self.send_to_channel(channel, notification):
                        success_count += 1
                    total_recipients += 1

            self.logger.info(f"Sent notification to {success_count}/{total_recipients} recipients")
            return success_count > 0

        except Exception as e:
            self.logger.error(f"Failed to send notification: {str(e)}")
            return False

    async def send_to_channel(self, channel_id: str, notification: NotificationData) -> bool:
        """Send notification to a specific Telegram channel."""
        message = self.format_message(notification)
        return await self._send_message(channel_id, message)

    async def send_to_user(self, user_id: int, notification: NotificationData) -> bool:
        """Send notification to a specific user."""
        message = self.format_message(notification)
        return await self._send_message(str(user_id), message)

    async def send_with_keyboard(self, chat_id: str, notification: NotificationData,
                               keyboard: Optional[List[List[str]]] = None) -> bool:
        """Send notification with inline keyboard."""
        message = self.format_message(notification)

        params = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': self.parse_mode,
            'disable_web_page_preview': self.disable_web_page_preview
        }

        if keyboard:
            inline_keyboard = []
            for row in keyboard:
                keyboard_row = []
                for button_text in row:
                    keyboard_row.append({
                        'text': button_text,
                        'callback_data': f"action_{button_text.lower().replace(' ', '_')}"
                    })
                inline_keyboard.append(keyboard_row)

            params['reply_markup'] = {
                'inline_keyboard': inline_keyboard
            }

        result = await self._make_request('sendMessage', params)
        return result is not None

    async def _send_message(self, chat_id: str, message: str) -> bool:
        """Send a formatted message to a chat."""
        # Split message if too long
        if len(message) > self.max_message_length:
            parts = self._split_message(message)
            for part in parts:
                result = await self._make_request('sendMessage', {
                    'chat_id': chat_id,
                    'text': part,
                    'parse_mode': self.parse_mode,
                    'disable_web_page_preview': self.disable_web_page_preview
                })
                if not result:
                    return False
            return True
        else:
            result = await self._make_request('sendMessage', {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': self.parse_mode,
                'disable_web_page_preview': self.disable_web_page_preview
            })
            return result is not None

    def _split_message(self, message: str) -> List[str]:
        """Split long messages into chunks."""
        parts = []
        current_part = ""

        for line in message.split('\n'):
            if len(current_part + line + '\n') > self.max_message_length:
                if current_part:
                    parts.append(current_part.strip())
                current_part = line + '\n'
            else:
                current_part += line + '\n'

        if current_part:
            parts.append(current_part.strip())

        return parts or [message]

    async def send_photo(self, chat_id: str, photo_path: str, caption: str = "") -> bool:
        """Send a photo with optional caption."""
        try:
            with open(photo_path, 'rb') as photo:
                data = aiohttp.FormData()
                data.add_field('chat_id', chat_id)
                data.add_field('photo', photo, filename='chart.png')
                if caption:
                    data.add_field('caption', caption)
                    data.add_field('parse_mode', self.parse_mode)

                url = f"{self.api_base_url}/sendPhoto"
                async with self.session.post(url, data=data) as response:
                    result = await response.json()
                    return result.get('ok', False)

        except Exception as e:
            self.logger.error(f"Failed to send photo: {str(e)}")
            return False

    async def test_connection(self) -> bool:
        """Test connection to Telegram Bot API."""
        try:
            result = await self._make_request('getMe')
            return result is not None
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False

    # Command Handlers
    async def _handle_start(self, message: Dict) -> None:
        """Handle /start command."""
        chat_id = str(message['chat']['id'])
        user_id = message['from']['id']

        welcome_message = """
🤖 <b>Welcome to Whale Alert Bot!</b>

This bot provides real-time whale detection alerts for cryptocurrency markets.

<b>Available Commands:</b>
/help - Show this help message
/subscribe - Subscribe to whale alerts
/unsubscribe - Unsubscribe from alerts
/status - Check your subscription status
/alerts - View recent alerts
/settings - Manage notification preferences

Get started by using /subscribe to receive whale alerts!
        """

        await self._send_message(chat_id, welcome_message)

        # Register user if user manager is available
        if self.user_manager:
            await self.user_manager.register_user(user_id, chat_id, message['from'])

    async def _handle_help(self, message: Dict) -> None:
        """Handle /help command."""
        await self._handle_start(message)

    async def _handle_subscribe(self, message: Dict) -> None:
        """Handle /subscribe command."""
        chat_id = str(message['chat']['id'])
        user_id = message['from']['id']

        if self.user_manager:
            success = await self.user_manager.subscribe_user(user_id)
            if success:
                response = "✅ You have been subscribed to whale alerts!"
            else:
                response = "❌ Subscription failed. You may already be subscribed."
        else:
            response = "❌ User management not available."

        await self._send_message(chat_id, response)

    async def _handle_unsubscribe(self, message: Dict) -> None:
        """Handle /unsubscribe command."""
        chat_id = str(message['chat']['id'])
        user_id = message['from']['id']

        if self.user_manager:
            success = await self.user_manager.unsubscribe_user(user_id)
            if success:
                response = "❌ You have been unsubscribed from whale alerts."
            else:
                response = "❌ Unsubscribe failed. You may not be subscribed."
        else:
            response = "❌ User management not available."

        await self._send_message(chat_id, response)

    async def _handle_status(self, message: Dict) -> None:
        """Handle /status command."""
        chat_id = str(message['chat']['id'])
        user_id = message['from']['id']

        if self.user_manager:
            status = await self.user_manager.get_user_status(user_id)
            response = f"📊 <b>Your Status:</b>\n\n{status}"
        else:
            response = "❌ User management not available."

        await self._send_message(chat_id, response)

    async def _handle_alerts(self, message: Dict) -> None:
        """Handle /alerts command to show recent alerts."""
        chat_id = str(message['chat']['id'])
        response = "📈 Recent whale alerts feature coming soon!"
        await self._send_message(chat_id, response)

    async def _handle_settings(self, message: Dict) -> None:
        """Handle /settings command."""
        chat_id = str(message['chat']['id'])

        keyboard = [
            ["🔴 Critical Alerts", "🟡 High Priority"],
            ["🟢 Medium Priority", "⚪ Low Priority"],
            ["📊 All Alert Types", "❌ Unsubscribe"]
        ]

        notification = NotificationData(
            alert_type=AlertType.WHALE_TRADE,
            severity=AlertSeverity.MEDIUM,
            symbol="SETTINGS",
            message="⚙️ <b>Notification Settings</b>\n\nChoose your alert preferences:"
        )

        await self.send_with_keyboard(chat_id, notification, keyboard)

    async def handle_message(self, message: Dict) -> None:
        """Handle incoming messages and route to appropriate handlers."""
        try:
            text = message.get('text', '')

            if text.startswith('/'):
                command = text[1:].split()[0].lower()
                handler = self.command_handlers.get(command)

                if handler:
                    await handler(message)
                else:
                    chat_id = str(message['chat']['id'])
                    await self._send_message(chat_id, "Unknown command. Use /help for available commands.")

        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")

    def set_user_manager(self, user_manager):
        """Inject user manager dependency."""
        self.user_manager = user_manager