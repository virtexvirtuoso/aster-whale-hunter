"""
User management system for Telegram bot.
Handles user registration, subscriptions, preferences, and permissions.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from enum import Enum

from ..core.interfaces.reporting import AlertType, AlertSeverity
from ..database.models import TelegramUser, UserSubscription, UserPreference


class UserPermission(Enum):
    """User permission levels."""
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class TelegramUserManager:
    """
    Complete user management system for Telegram bot.
    Handles subscriptions, preferences, and permission management.
    """

    def __init__(self, database_manager, config: Dict[str, Any]):
        self.db = database_manager
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Admin configuration
        self.super_admins = set(config.get('super_admins', []))
        self.admins = set(config.get('admins', []))

        # Default subscription settings
        self.default_alert_types = {
            AlertType.WHALE_TRADE,
            AlertType.ACCUMULATION,
            AlertType.MANIPULATION
        }
        self.default_min_severity = AlertSeverity.MEDIUM

    async def register_user(self, user_id: int, chat_id: str, user_data: Dict) -> bool:
        """Register a new user or update existing user information."""
        try:
            # Extract user information from Telegram user object
            username = user_data.get('username', '')
            first_name = user_data.get('first_name', '')
            last_name = user_data.get('last_name', '')
            language_code = user_data.get('language_code', 'en')

            # Determine user permission level
            permission = self._get_user_permission(user_id)

            # Create or update user record
            user = await self.db.get_or_create_user(
                user_id=user_id,
                chat_id=chat_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                permission=permission.value
            )

            self.logger.info(f"Registered user {user_id} (@{username}) with {permission.value} permissions")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register user {user_id}: {str(e)}")
            return False

    def _get_user_permission(self, user_id: int) -> UserPermission:
        """Determine user permission level based on configuration."""
        if user_id in self.super_admins:
            return UserPermission.SUPER_ADMIN
        elif user_id in self.admins:
            return UserPermission.ADMIN
        else:
            return UserPermission.USER

    async def subscribe_user(self, user_id: int,
                           alert_types: Optional[Set[AlertType]] = None,
                           min_severity: Optional[AlertSeverity] = None) -> bool:
        """Subscribe a user to whale alerts with specified preferences."""
        try:
            # Use defaults if not specified
            alert_types = alert_types or self.default_alert_types
            min_severity = min_severity or self.default_min_severity

            # Create subscription record
            success = await self.db.create_subscription(
                user_id=user_id,
                alert_types=[at.value for at in alert_types],
                min_severity=min_severity.name,
                is_active=True
            )

            if success:
                self.logger.info(f"User {user_id} subscribed to alerts: {[at.value for at in alert_types]}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to subscribe user {user_id}: {str(e)}")
            return False

    async def unsubscribe_user(self, user_id: int) -> bool:
        """Unsubscribe a user from all alerts."""
        try:
            success = await self.db.deactivate_subscription(user_id)

            if success:
                self.logger.info(f"User {user_id} unsubscribed from alerts")

            return success

        except Exception as e:
            self.logger.error(f"Failed to unsubscribe user {user_id}: {str(e)}")
            return False

    async def update_user_preferences(self, user_id: int,
                                    alert_types: Optional[Set[AlertType]] = None,
                                    min_severity: Optional[AlertSeverity] = None,
                                    symbols: Optional[Set[str]] = None) -> bool:
        """Update user notification preferences."""
        try:
            preferences = {}

            if alert_types is not None:
                preferences['alert_types'] = [at.value for at in alert_types]

            if min_severity is not None:
                preferences['min_severity'] = min_severity.name

            if symbols is not None:
                preferences['symbols'] = list(symbols)

            success = await self.db.update_user_preferences(user_id, preferences)

            if success:
                self.logger.info(f"Updated preferences for user {user_id}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to update preferences for user {user_id}: {str(e)}")
            return False

    async def get_subscribers(self,
                            alert_type: AlertType,
                            severity: AlertSeverity,
                            symbol: Optional[str] = None) -> List[int]:
        """Get list of user IDs who should receive this alert."""
        try:
            subscribers = await self.db.get_active_subscribers(
                alert_type=alert_type.value,
                severity=severity.name,
                symbol=symbol
            )

            return subscribers

        except Exception as e:
            self.logger.error(f"Failed to get subscribers: {str(e)}")
            return []

    async def get_user_status(self, user_id: int) -> str:
        """Get formatted status information for a user."""
        try:
            user = await self.db.get_user(user_id)
            if not user:
                return "❌ User not found. Use /start to register."

            subscription = await self.db.get_user_subscription(user_id)
            if not subscription or not subscription.is_active:
                return "❌ Not subscribed to alerts. Use /subscribe to start receiving notifications."

            # Format status message
            status_parts = [
                "✅ <b>Subscribed to whale alerts</b>",
                "",
                f"👤 <b>User:</b> {user.first_name or 'Unknown'}",
                f"🆔 <b>User ID:</b> {user_id}",
                f"📅 <b>Registered:</b> {user.created_at.strftime('%Y-%m-%d')}",
                ""
            ]

            # Alert type preferences
            alert_types = subscription.alert_types or []
            if alert_types:
                status_parts.extend([
                    "🔔 <b>Alert Types:</b>",
                    "  • " + "\n  • ".join([at.replace('_', ' ').title() for at in alert_types])
                ])

            # Severity preference
            if subscription.min_severity:
                severity_emojis = {
                    'CRITICAL': '🔴',
                    'HIGH': '🟡',
                    'MEDIUM': '🟢',
                    'LOW': '⚪'
                }
                emoji = severity_emojis.get(subscription.min_severity, '❓')
                status_parts.append(f"⚠️ <b>Minimum Severity:</b> {emoji} {subscription.min_severity}")

            # Statistics
            alert_count = await self.db.get_user_alert_count(user_id)
            if alert_count is not None:
                status_parts.extend([
                    "",
                    f"📊 <b>Alerts Received:</b> {alert_count}"
                ])

            return "\n".join(status_parts)

        except Exception as e:
            self.logger.error(f"Failed to get user status for {user_id}: {str(e)}")
            return "❌ Failed to retrieve status information."

    async def is_admin(self, user_id: int) -> bool:
        """Check if user has admin permissions."""
        try:
            user = await self.db.get_user(user_id)
            if not user:
                return False

            return user.permission in ['admin', 'super_admin']

        except Exception as e:
            self.logger.error(f"Failed to check admin status for {user_id}: {str(e)}")
            return False

    async def is_super_admin(self, user_id: int) -> bool:
        """Check if user has super admin permissions."""
        try:
            user = await self.db.get_user(user_id)
            if not user:
                return False

            return user.permission == 'super_admin'

        except Exception as e:
            self.logger.error(f"Failed to check super admin status for {user_id}: {str(e)}")
            return False

    async def get_user_stats(self) -> Dict[str, Any]:
        """Get overall user statistics for admins."""
        try:
            stats = await self.db.get_user_statistics()
            return {
                'total_users': stats.get('total_users', 0),
                'active_subscribers': stats.get('active_subscribers', 0),
                'inactive_users': stats.get('inactive_users', 0),
                'admin_count': len(self.admins) + len(self.super_admins),
                'alert_types_distribution': stats.get('alert_types', {}),
                'severity_preferences': stats.get('severity_prefs', {})
            }

        except Exception as e:
            self.logger.error(f"Failed to get user stats: {str(e)}")
            return {}

    async def broadcast_message(self, message: str,
                              user_ids: Optional[List[int]] = None,
                              admin_only: bool = False) -> Dict[str, int]:
        """Broadcast a message to users (admin feature)."""
        try:
            if user_ids is None:
                if admin_only:
                    user_ids = await self.db.get_admin_users()
                else:
                    user_ids = await self.db.get_all_active_users()

            sent = 0
            failed = 0

            # This would be implemented in conjunction with the bot instance
            # For now, return stats that would be generated
            total = len(user_ids)
            sent = total  # Assume all successful for now

            return {
                'total': total,
                'sent': sent,
                'failed': failed
            }

        except Exception as e:
            self.logger.error(f"Failed to broadcast message: {str(e)}")
            return {'total': 0, 'sent': 0, 'failed': 0}

    async def cleanup_inactive_users(self, days_inactive: int = 30) -> int:
        """Clean up users who haven't been active for specified days."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_inactive)
            cleaned_count = await self.db.cleanup_inactive_users(cutoff_date)

            self.logger.info(f"Cleaned up {cleaned_count} inactive users")
            return cleaned_count

        except Exception as e:
            self.logger.error(f"Failed to cleanup inactive users: {str(e)}")
            return 0

    async def export_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Export all user data (GDPR compliance)."""
        try:
            user_data = await self.db.export_user_data(user_id)
            return user_data

        except Exception as e:
            self.logger.error(f"Failed to export user data for {user_id}: {str(e)}")
            return None

    async def delete_user_data(self, user_id: int) -> bool:
        """Permanently delete all user data (GDPR compliance)."""
        try:
            success = await self.db.delete_user_completely(user_id)

            if success:
                self.logger.info(f"Deleted all data for user {user_id}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to delete user data for {user_id}: {str(e)}")
            return False