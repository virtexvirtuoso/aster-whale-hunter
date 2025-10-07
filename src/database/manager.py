"""
Database manager for Telegram bot with SQLAlchemy ORM.
Handles all database operations for users, subscriptions, and alerts.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
import json
from sqlalchemy import create_engine, and_, or_, func, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    Base, TelegramUser, UserSubscription, UserPreference,
    AlertLog, WhaleAlert, BotStats, SystemConfig
)


class DatabaseManager:
    """
    Complete database management system for Telegram bot.
    Provides async-like interface for all database operations.
    """

    def __init__(self, database_url: str = "sqlite:///data/whale_bot.db"):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self.logger = logging.getLogger(__name__)

    def initialize(self):
        """Initialize database connection and create tables."""
        try:
            self.engine = create_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True,
                connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {}
            )

            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            self.logger.info("Database initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize database: {str(e)}")
            raise

    def get_session(self) -> Session:
        """Get a new database session."""
        if not self.SessionLocal:
            self.initialize()
        return self.SessionLocal()

    # User Management Methods

    async def get_or_create_user(self, user_id: int, chat_id: str, username: str = "",
                               first_name: str = "", last_name: str = "",
                               language_code: str = "en", permission: str = "user") -> TelegramUser:
        """Get existing user or create a new one."""
        with self.get_session() as session:
            try:
                # Try to get existing user
                user = session.query(TelegramUser).filter_by(user_id=user_id).first()

                if user:
                    # Update existing user information
                    user.chat_id = chat_id
                    user.username = username
                    user.first_name = first_name
                    user.last_name = last_name
                    user.language_code = language_code
                    user.last_interaction = datetime.utcnow()
                    user.is_active = True
                else:
                    # Create new user
                    user = TelegramUser(
                        user_id=user_id,
                        chat_id=chat_id,
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        language_code=language_code,
                        permission=permission
                    )
                    session.add(user)

                session.commit()
                return user

            except SQLAlchemyError as e:
                session.rollback()
                self.logger.error(f"Database error in get_or_create_user: {str(e)}")
                raise

    async def get_user(self, user_id: int) -> Optional[TelegramUser]:
        """Get user by user ID."""
        with self.get_session() as session:
            try:
                return session.query(TelegramUser).filter_by(user_id=user_id).first()
            except SQLAlchemyError as e:
                self.logger.error(f"Error getting user {user_id}: {str(e)}")
                return None

    async def update_user_activity(self, user_id: int):
        """Update user's last interaction timestamp."""
        with self.get_session() as session:
            try:
                user = session.query(TelegramUser).filter_by(user_id=user_id).first()
                if user:
                    user.last_interaction = datetime.utcnow()
                    session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Error updating user activity: {str(e)}")

    # Subscription Management Methods

    async def create_subscription(self, user_id: int, alert_types: List[str],
                                min_severity: str = "MEDIUM", symbols: List[str] = None,
                                exchanges: List[str] = None, is_active: bool = True) -> bool:
        """Create or update user subscription."""
        with self.get_session() as session:
            try:
                # Check if subscription already exists
                subscription = session.query(UserSubscription).filter_by(user_id=user_id).first()

                if subscription:
                    # Update existing subscription
                    subscription.alert_types = alert_types
                    subscription.min_severity = min_severity
                    subscription.symbols = symbols or []
                    subscription.exchanges = exchanges or []
                    subscription.is_active = is_active
                    subscription.updated_at = datetime.utcnow()
                else:
                    # Create new subscription
                    subscription = UserSubscription(
                        user_id=user_id,
                        alert_types=alert_types,
                        min_severity=min_severity,
                        symbols=symbols or [],
                        exchanges=exchanges or [],
                        is_active=is_active
                    )
                    session.add(subscription)

                session.commit()
                return True

            except SQLAlchemyError as e:
                session.rollback()
                self.logger.error(f"Error creating subscription: {str(e)}")
                return False

    async def deactivate_subscription(self, user_id: int) -> bool:
        """Deactivate user subscription."""
        with self.get_session() as session:
            try:
                subscription = session.query(UserSubscription).filter_by(user_id=user_id).first()
                if subscription:
                    subscription.is_active = False
                    subscription.updated_at = datetime.utcnow()
                    session.commit()
                    return True
                return False

            except SQLAlchemyError as e:
                session.rollback()
                self.logger.error(f"Error deactivating subscription: {str(e)}")
                return False

    async def get_user_subscription(self, user_id: int) -> Optional[UserSubscription]:
        """Get user subscription details."""
        with self.get_session() as session:
            try:
                return session.query(UserSubscription).filter_by(user_id=user_id).first()
            except SQLAlchemyError as e:
                self.logger.error(f"Error getting subscription: {str(e)}")
                return None

    async def get_active_subscribers(self, alert_type: str, severity: str,
                                   symbol: str = None) -> List[int]:
        """Get list of users who should receive this alert."""
        with self.get_session() as session:
            try:
                # Build query for active subscriptions
                query = session.query(UserSubscription).join(TelegramUser).filter(
                    UserSubscription.is_active == True,
                    TelegramUser.is_active == True,
                    TelegramUser.is_blocked == False
                )

                subscriptions = query.all()
                eligible_users = []

                for sub in subscriptions:
                    if sub.should_receive_alert(alert_type, severity, symbol):
                        eligible_users.append(sub.user_id)

                return eligible_users

            except SQLAlchemyError as e:
                self.logger.error(f"Error getting subscribers: {str(e)}")
                return []

    # Preference Management Methods

    async def update_user_preferences(self, user_id: int, preferences: Dict[str, Any]) -> bool:
        """Update user preferences."""
        with self.get_session() as session:
            try:
                for key, value in preferences.items():
                    # Check if preference exists
                    pref = session.query(UserPreference).filter_by(
                        user_id=user_id, preference_key=key
                    ).first()

                    if pref:
                        pref.preference_value = json.dumps(value) if not isinstance(value, str) else value
                        pref.updated_at = datetime.utcnow()
                    else:
                        pref = UserPreference(
                            user_id=user_id,
                            preference_key=key,
                            preference_value=json.dumps(value) if not isinstance(value, str) else value
                        )
                        session.add(pref)

                session.commit()
                return True

            except SQLAlchemyError as e:
                session.rollback()
                self.logger.error(f"Error updating preferences: {str(e)}")
                return False

    async def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get all user preferences."""
        with self.get_session() as session:
            try:
                preferences = session.query(UserPreference).filter_by(user_id=user_id).all()
                result = {}

                for pref in preferences:
                    try:
                        value = json.loads(pref.preference_value)
                    except (json.JSONDecodeError, TypeError):
                        value = pref.preference_value
                    result[pref.preference_key] = value

                return result

            except SQLAlchemyError as e:
                self.logger.error(f"Error getting preferences: {str(e)}")
                return {}

    # Alert Logging Methods

    async def log_alert(self, user_id: int, alert_type: str, severity: str,
                       symbol: str, exchange: str, message_id: str,
                       alert_data: Dict[str, Any], delivery_status: str = "sent",
                       error_message: str = None) -> bool:
        """Log sent alert for tracking purposes."""
        with self.get_session() as session:
            try:
                log = AlertLog(
                    user_id=user_id,
                    alert_type=alert_type,
                    severity=severity,
                    symbol=symbol,
                    exchange=exchange,
                    message_id=message_id,
                    alert_data=alert_data,
                    delivery_status=delivery_status,
                    error_message=error_message
                )
                session.add(log)
                session.commit()
                return True

            except SQLAlchemyError as e:
                session.rollback()
                self.logger.error(f"Error logging alert: {str(e)}")
                return False

    async def get_user_alert_count(self, user_id: int, days: int = 30) -> int:
        """Get count of alerts sent to user in last N days."""
        with self.get_session() as session:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                count = session.query(AlertLog).filter(
                    AlertLog.user_id == user_id,
                    AlertLog.sent_at >= cutoff_date,
                    AlertLog.delivery_status == 'sent'
                ).count()
                return count

            except SQLAlchemyError as e:
                self.logger.error(f"Error getting alert count: {str(e)}")
                return 0

    # Statistics and Analytics Methods

    async def get_user_statistics(self) -> Dict[str, Any]:
        """Get comprehensive user statistics."""
        with self.get_session() as session:
            try:
                stats = {}

                # Basic user counts
                stats['total_users'] = session.query(TelegramUser).count()
                stats['active_subscribers'] = session.query(UserSubscription).filter_by(is_active=True).count()
                stats['inactive_users'] = session.query(TelegramUser).filter_by(is_active=False).count()

                # Alert type distribution
                alert_types = session.query(
                    UserSubscription.alert_types,
                    func.count(UserSubscription.id).label('count')
                ).filter_by(is_active=True).group_by(UserSubscription.alert_types).all()

                # Severity preferences
                severity_prefs = session.query(
                    UserSubscription.min_severity,
                    func.count(UserSubscription.id).label('count')
                ).filter_by(is_active=True).group_by(UserSubscription.min_severity).all()

                stats['severity_prefs'] = {pref[0]: pref[1] for pref in severity_prefs}

                return stats

            except SQLAlchemyError as e:
                self.logger.error(f"Error getting user statistics: {str(e)}")
                return {}

    async def get_alert_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get alert delivery statistics."""
        with self.get_session() as session:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days)

                stats = {}
                stats['total_alerts'] = session.query(AlertLog).filter(
                    AlertLog.sent_at >= cutoff_date
                ).count()

                stats['successful_alerts'] = session.query(AlertLog).filter(
                    AlertLog.sent_at >= cutoff_date,
                    AlertLog.delivery_status == 'sent'
                ).count()

                stats['failed_alerts'] = session.query(AlertLog).filter(
                    AlertLog.sent_at >= cutoff_date,
                    AlertLog.delivery_status == 'failed'
                ).count()

                # Most active symbols
                symbol_stats = session.query(
                    AlertLog.symbol,
                    func.count(AlertLog.id).label('count')
                ).filter(
                    AlertLog.sent_at >= cutoff_date,
                    AlertLog.delivery_status == 'sent'
                ).group_by(AlertLog.symbol).order_by(desc('count')).limit(10).all()

                stats['top_symbols'] = {symbol[0]: symbol[1] for symbol in symbol_stats}

                return stats

            except SQLAlchemyError as e:
                self.logger.error(f"Error getting alert statistics: {str(e)}")
                return {}

    # Maintenance and Cleanup Methods

    async def cleanup_inactive_users(self, cutoff_date: datetime) -> int:
        """Remove inactive users and their data."""
        with self.get_session() as session:
            try:
                # Get users to delete
                users_to_delete = session.query(TelegramUser).filter(
                    TelegramUser.last_interaction < cutoff_date,
                    TelegramUser.is_active == False
                ).all()

                count = len(users_to_delete)

                # Delete users (cascading will handle related records)
                for user in users_to_delete:
                    session.delete(user)

                session.commit()
                return count

            except SQLAlchemyError as e:
                session.rollback()
                self.logger.error(f"Error cleaning up users: {str(e)}")
                return 0

    async def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """Remove old alert logs."""
        with self.get_session() as session:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
                count = session.query(AlertLog).filter(AlertLog.sent_at < cutoff_date).count()

                session.query(AlertLog).filter(AlertLog.sent_at < cutoff_date).delete()
                session.commit()

                return count

            except SQLAlchemyError as e:
                session.rollback()
                self.logger.error(f"Error cleaning up logs: {str(e)}")
                return 0

    # Admin and Management Methods

    async def get_all_active_users(self) -> List[int]:
        """Get all active user IDs."""
        with self.get_session() as session:
            try:
                users = session.query(TelegramUser.user_id).filter_by(
                    is_active=True, is_blocked=False
                ).all()
                return [user[0] for user in users]

            except SQLAlchemyError as e:
                self.logger.error(f"Error getting active users: {str(e)}")
                return []

    async def get_admin_users(self) -> List[int]:
        """Get all admin user IDs."""
        with self.get_session() as session:
            try:
                users = session.query(TelegramUser.user_id).filter(
                    TelegramUser.permission.in_(['admin', 'super_admin'])
                ).all()
                return [user[0] for user in users]

            except SQLAlchemyError as e:
                self.logger.error(f"Error getting admin users: {str(e)}")
                return []

    async def export_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Export all user data for GDPR compliance."""
        with self.get_session() as session:
            try:
                user = session.query(TelegramUser).filter_by(user_id=user_id).first()
                if not user:
                    return None

                # Get all related data
                subscription = session.query(UserSubscription).filter_by(user_id=user_id).first()
                preferences = session.query(UserPreference).filter_by(user_id=user_id).all()
                alert_logs = session.query(AlertLog).filter_by(user_id=user_id).all()

                return {
                    'user': {
                        'user_id': user.user_id,
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'language_code': user.language_code,
                        'created_at': user.created_at.isoformat(),
                        'last_interaction': user.last_interaction.isoformat()
                    },
                    'subscription': {
                        'alert_types': subscription.alert_types if subscription else None,
                        'min_severity': subscription.min_severity if subscription else None,
                        'symbols': subscription.symbols if subscription else None,
                        'is_active': subscription.is_active if subscription else False
                    } if subscription else None,
                    'preferences': {pref.preference_key: pref.preference_value for pref in preferences},
                    'alert_history_count': len(alert_logs)
                }

            except SQLAlchemyError as e:
                self.logger.error(f"Error exporting user data: {str(e)}")
                return None

    async def delete_user_completely(self, user_id: int) -> bool:
        """Permanently delete all user data."""
        with self.get_session() as session:
            try:
                user = session.query(TelegramUser).filter_by(user_id=user_id).first()
                if user:
                    session.delete(user)  # Cascading will handle related records
                    session.commit()
                    return True
                return False

            except SQLAlchemyError as e:
                session.rollback()
                self.logger.error(f"Error deleting user: {str(e)}")
                return False