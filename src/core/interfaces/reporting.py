"""
Core notification interfaces for whale detection alerting system.
Provides base interfaces for different notification channels including Telegram.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class AlertSeverity(Enum):
    """Alert severity levels with corresponding emoji indicators."""
    CRITICAL = "🔴"
    HIGH = "🟡"
    MEDIUM = "🟢"
    LOW = "⚪"


class AlertType(Enum):
    """Types of whale detection alerts."""
    WHALE_TRADE = "whale_trade"
    ACCUMULATION = "accumulation"
    MANIPULATION = "manipulation"
    VOLUME_SPIKE = "volume_spike"
    PRICE_IMPACT = "price_impact"


class NotificationData:
    """Data structure for notification payloads."""

    def __init__(self,
                 alert_type: AlertType,
                 severity: AlertSeverity,
                 symbol: str,
                 message: str,
                 data: Optional[Dict[str, Any]] = None,
                 timestamp: Optional[datetime] = None):
        self.alert_type = alert_type
        self.severity = severity
        self.symbol = symbol
        self.message = message
        self.data = data or {}
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert notification data to dictionary."""
        return {
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'symbol': self.symbol,
            'message': self.message,
            'data': self.data,
            'timestamp': self.timestamp.isoformat()
        }


class NotificationInterface(ABC):
    """Base interface for all notification channels."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', False)

    @abstractmethod
    async def send_notification(self, notification: NotificationData) -> bool:
        """Send a notification through this channel."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the connection to the notification service."""
        pass

    @abstractmethod
    def format_message(self, notification: NotificationData) -> str:
        """Format the notification message for this channel."""
        pass


class TelegramNotificationInterface(NotificationInterface):
    """Interface for Telegram notifications - to be implemented by TelegramBot."""

    @abstractmethod
    async def send_to_channel(self, channel_id: str, notification: NotificationData) -> bool:
        """Send notification to a specific Telegram channel."""
        pass

    @abstractmethod
    async def send_to_user(self, user_id: int, notification: NotificationData) -> bool:
        """Send notification to a specific user."""
        pass

    @abstractmethod
    async def send_with_keyboard(self, chat_id: str, notification: NotificationData,
                               keyboard: Optional[List[List[str]]] = None) -> bool:
        """Send notification with inline keyboard."""
        pass


class DiscordNotificationInterface(NotificationInterface):
    """Interface for Discord webhook notifications."""

    @abstractmethod
    async def send_webhook(self, webhook_url: str, notification: NotificationData) -> bool:
        """Send notification via Discord webhook."""
        pass


class EmailNotificationInterface(NotificationInterface):
    """Interface for email notifications."""

    @abstractmethod
    async def send_email(self, to_addresses: List[str], notification: NotificationData) -> bool:
        """Send email notification."""
        pass