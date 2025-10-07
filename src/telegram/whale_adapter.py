"""
Adapter to integrate advanced TelegramCommandHandler with WhaleHunterApplication.
Bridges the gap between the telegram command system and whale hunter components.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class WhaleCommandAdapter:
    """
    Adapter that makes TelegramAlertChannel compatible with TelegramCommandHandler.
    Provides the interface expected by the advanced command handler.
    """

    def __init__(self, telegram_channel, whale_app):
        """
        Initialize the adapter.

        Args:
            telegram_channel: TelegramAlertChannel instance
            whale_app: WhaleHunterApplication instance
        """
        self.channel = telegram_channel
        self.whale_app = whale_app
        self.logger = logging.getLogger(__name__)

    async def _send_message(self, chat_id: str, message: str, **kwargs):
        """Send message through telegram channel."""
        return await self.channel._send_message(int(chat_id), message, **kwargs)

    async def send_with_keyboard(self, chat_id: str, notification, keyboard: list = None):
        """Send message with inline keyboard."""
        message = notification.message if hasattr(notification, 'message') else str(notification)
        return await self.channel._send_message(int(chat_id), message, inline_keyboard=keyboard)


class SimpleUserManager:
    """
    Simple user manager for whale hunter mode.
    Provides basic permission checks without database.
    """

    def __init__(self, admin_users=None, telegram_channel=None):
        """
        Initialize user manager.

        Args:
            admin_users: List of admin user IDs
            telegram_channel: TelegramAlertChannel instance to sync subscribers
        """
        self.admin_users = set(admin_users or [])
        self.subscribed_users = set()  # Track subscriptions
        self.telegram_channel = telegram_channel  # Reference to telegram channel for syncing
        self.logger = logging.getLogger(__name__)

    async def is_super_admin(self, user_id: int) -> bool:
        """Check if user is super admin."""
        return user_id in self.admin_users

    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id in self.admin_users

    def add_admin(self, user_id: int):
        """Add admin user."""
        self.admin_users.add(user_id)

    def remove_admin(self, user_id: int):
        """Remove admin user."""
        self.admin_users.discard(user_id)

    async def register_user(self, user_id: int, chat_id: str, user_data: Dict[str, Any]):
        """Register a new user."""
        self.logger.info(f"User {user_id} registered")
        return True

    async def subscribe_user(self, user_id: int, alert_types=None, min_severity=None):
        """Subscribe user to alerts."""
        self.subscribed_users.add(user_id)

        # Also add to telegram channel's subscriber list
        if self.telegram_channel:
            self.telegram_channel.add_subscriber(user_id)

        self.logger.info(f"User {user_id} subscribed to whale alerts")
        return True

    async def unsubscribe_user(self, user_id: int):
        """Unsubscribe user from alerts."""
        self.subscribed_users.discard(user_id)

        # Also remove from telegram channel's subscriber list
        if self.telegram_channel:
            self.telegram_channel.remove_subscriber(user_id)

        self.logger.info(f"User {user_id} unsubscribed from whale alerts")
        return True

    async def get_user_status(self, user_id: int) -> str:
        """Get user subscription status."""
        is_subscribed = user_id in self.subscribed_users
        is_admin = user_id in self.admin_users

        status = "✅ <b>Subscribed</b>" if is_subscribed else "❌ <b>Not Subscribed</b>"
        role = "👑 <b>Admin</b>" if is_admin else "👤 <b>User</b>"

        return f"""
📊 <b>Your Status:</b>

<b>Subscription:</b> {status}
<b>Role:</b> {role}
<b>User ID:</b> {user_id}

<b>Alert Settings:</b>
• Alert Types: All
• Minimum Severity: Medium
• Symbols: All monitored symbols

Use /subscribe to enable alerts or /unsubscribe to disable.
        """.strip()

    async def get_subscribers(self, alert_type=None, severity=None):
        """Get list of subscribed user IDs."""
        return list(self.subscribed_users)

    async def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics."""
        return {
            'total_users': len(self.subscribed_users) + len(self.admin_users),
            'active_subscribers': len(self.subscribed_users),
            'inactive_users': 0,
            'admin_count': len(self.admin_users),
            'severity_preferences': {}
        }
