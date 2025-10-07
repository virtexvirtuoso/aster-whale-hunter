"""
Database models for Telegram bot user management and alert system.
Uses SQLAlchemy ORM with SQLite backend for persistence.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List, Optional, Dict, Any

Base = declarative_base()


class TelegramUser(Base):
    """Model for Telegram users registered with the bot."""

    __tablename__ = 'telegram_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)  # Telegram user ID
    chat_id = Column(String(50), nullable=False)  # Telegram chat ID
    username = Column(String(100))  # Telegram username (without @)
    first_name = Column(String(100))
    last_name = Column(String(100))
    language_code = Column(String(10), default='en')
    permission = Column(String(20), default='user')  # user, admin, super_admin
    is_active = Column(Boolean, default=True)
    is_blocked = Column(Boolean, default=False)  # If user blocked the bot
    created_at = Column(DateTime, default=datetime.utcnow)
    last_interaction = Column(DateTime, default=datetime.utcnow)

    # Relationships
    subscriptions = relationship("UserSubscription", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")
    alert_logs = relationship("AlertLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TelegramUser(user_id={self.user_id}, username={self.username})>"

    @property
    def display_name(self) -> str:
        """Get user's display name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return f"@{self.username}"
        else:
            return f"User {self.user_id}"

    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.permission in ['admin', 'super_admin']

    def is_super_admin(self) -> bool:
        """Check if user has super admin privileges."""
        return self.permission == 'super_admin'


class UserSubscription(Base):
    """Model for user alert subscriptions."""

    __tablename__ = 'user_subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('telegram_users.user_id'), nullable=False)
    alert_types = Column(JSON)  # List of alert types: ['whale_trade', 'accumulation', etc.]
    min_severity = Column(String(20), default='MEDIUM')  # CRITICAL, HIGH, MEDIUM, LOW
    symbols = Column(JSON)  # Optional: specific symbols to watch, empty = all
    exchanges = Column(JSON)  # Optional: specific exchanges to watch, empty = all
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("TelegramUser", back_populates="subscriptions")

    def __repr__(self):
        return f"<UserSubscription(user_id={self.user_id}, types={self.alert_types})>"

    def should_receive_alert(self, alert_type: str, severity: str, symbol: str = None, exchange: str = None) -> bool:
        """Check if user should receive this alert based on preferences."""
        if not self.is_active:
            return False

        # Check alert type
        if self.alert_types and alert_type not in self.alert_types:
            return False

        # Check severity (convert to numeric for comparison)
        severity_levels = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        min_level = severity_levels.get(self.min_severity, 2)
        alert_level = severity_levels.get(severity, 1)

        if alert_level < min_level:
            return False

        # Check symbol filter
        if self.symbols and symbol and symbol not in self.symbols:
            return False

        # Check exchange filter
        if self.exchanges and exchange and exchange not in self.exchanges:
            return False

        return True


class UserPreference(Base):
    """Model for detailed user preferences and settings."""

    __tablename__ = 'user_preferences'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('telegram_users.user_id'), nullable=False)
    preference_key = Column(String(100), nullable=False)  # e.g., 'timezone', 'format', 'quiet_hours'
    preference_value = Column(Text)  # JSON string for complex values
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("TelegramUser", back_populates="preferences")

    def __repr__(self):
        return f"<UserPreference(user_id={self.user_id}, key={self.preference_key})>"


class AlertLog(Base):
    """Model for tracking sent alerts to users."""

    __tablename__ = 'alert_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('telegram_users.user_id'), nullable=False)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    symbol = Column(String(20))
    exchange = Column(String(50))
    message_id = Column(String(50))  # Telegram message ID
    alert_data = Column(JSON)  # Full alert payload
    sent_at = Column(DateTime, default=datetime.utcnow)
    delivery_status = Column(String(20), default='sent')  # sent, failed, blocked
    error_message = Column(Text)

    # Relationships
    user = relationship("TelegramUser", back_populates="alert_logs")

    def __repr__(self):
        return f"<AlertLog(user_id={self.user_id}, type={self.alert_type}, sent_at={self.sent_at})>"


class WhaleAlert(Base):
    """Model for storing whale detection alerts."""

    __tablename__ = 'whale_alerts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), index=True)

    # Alert-specific data
    price = Column(Float)
    volume = Column(Float)
    trade_value = Column(Float)
    confidence_score = Column(Float)

    # Raw data and metadata
    raw_data = Column(JSON)  # Original detection data
    message = Column(Text)  # Formatted message

    # Timestamps
    detected_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Processing status
    is_processed = Column(Boolean, default=False)
    notification_sent = Column(Boolean, default=False)
    recipient_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<WhaleAlert(id={self.id}, type={self.alert_type}, symbol={self.symbol})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'symbol': self.symbol,
            'exchange': self.exchange,
            'price': self.price,
            'volume': self.volume,
            'trade_value': self.trade_value,
            'confidence_score': self.confidence_score,
            'raw_data': self.raw_data,
            'message': self.message,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'created_at': self.created_at.isoformat(),
            'is_processed': self.is_processed,
            'notification_sent': self.notification_sent,
            'recipient_count': self.recipient_count
        }


class BotStats(Base):
    """Model for tracking bot usage statistics."""

    __tablename__ = 'bot_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)  # Daily stats

    # User metrics
    total_users = Column(Integer, default=0)
    active_users = Column(Integer, default=0)  # Users who interacted today
    new_users = Column(Integer, default=0)
    blocked_users = Column(Integer, default=0)

    # Alert metrics
    alerts_sent = Column(Integer, default=0)
    alerts_failed = Column(Integer, default=0)
    unique_symbols = Column(Integer, default=0)

    # Command metrics
    commands_processed = Column(Integer, default=0)
    most_used_command = Column(String(50))

    # Performance metrics
    avg_response_time = Column(Float)
    error_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BotStats(date={self.date}, users={self.total_users}, alerts={self.alerts_sent})>"


class SystemConfig(Base):
    """Model for storing system configuration values."""

    __tablename__ = 'system_config'

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(Text)  # JSON string for complex values
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SystemConfig(key={self.config_key})>"


class OpenInterestHistory(Base):
    """Model for storing historical open interest data."""

    __tablename__ = 'open_interest_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    open_interest = Column(Float, nullable=False)
    oi_cap = Column(Float)
    oi_utilization = Column(Float)  # OI / Cap ratio
    funding_rate = Column(Float)
    exchange = Column(String(50), nullable=False, default='hyperliquid')
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_oi_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_oi_timestamp_desc', 'timestamp'),
        Index('idx_oi_symbol_exchange', 'symbol', 'exchange'),
    )

    def __repr__(self):
        return f"<OpenInterestHistory(symbol={self.symbol}, oi={self.open_interest}, timestamp={self.timestamp})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'open_interest': self.open_interest,
            'oi_cap': self.oi_cap,
            'oi_utilization': self.oi_utilization,
            'funding_rate': self.funding_rate,
            'exchange': self.exchange,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat()
        }


class OIAlert(Base):
    """Model for storing open interest specific alerts."""

    __tablename__ = 'oi_alerts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(100), unique=True, nullable=False)
    alert_type = Column(String(50), nullable=False, index=True)  # oi_spike, oi_divergence, oi_cap_warning
    severity = Column(String(20), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, default='hyperliquid')

    # OI-specific metrics
    oi_change_abs = Column(Float)  # Absolute OI change
    oi_change_pct = Column(Float)  # Percentage OI change
    oi_current = Column(Float, nullable=False)
    oi_previous = Column(Float)
    oi_cap = Column(Float)
    oi_utilization = Column(Float)

    # Correlation metrics
    price_change_pct = Column(Float)
    volume_change_pct = Column(Float)
    oi_price_correlation = Column(Float)

    # Alert scoring
    confidence_score = Column(Float, nullable=False)
    magnitude_score = Column(Float, nullable=False)
    composite_score = Column(Float, nullable=False)

    # Detection timeframe
    timeframe = Column(String(10))  # 1m, 5m, 15m, 1h, etc.
    detection_window_start = Column(DateTime)
    detection_window_end = Column(DateTime)

    # Metadata
    raw_data = Column(JSON)  # Full detection context
    title = Column(Text, nullable=False)
    message = Column(Text, nullable=False)

    # Timestamps
    detected_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Processing status
    is_processed = Column(Boolean, default=False)
    notification_sent = Column(Boolean, default=False)
    recipient_count = Column(Integer, default=0)

    # Cross-strategy correlation
    related_whale_alert_id = Column(Integer, ForeignKey('whale_alerts.id'))
    cross_strategy_boost = Column(Float, default=0.0)  # Score boost from other strategies

    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_oi_alerts_symbol_timestamp', 'symbol', 'detected_at'),
        Index('idx_oi_alerts_type_severity', 'alert_type', 'severity'),
        Index('idx_oi_alerts_timestamp_desc', 'detected_at'),
        Index('idx_oi_alerts_composite_score', 'composite_score'),
    )

    def __repr__(self):
        return f"<OIAlert(id={self.id}, type={self.alert_type}, symbol={self.symbol})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'symbol': self.symbol,
            'exchange': self.exchange,
            'oi_change_abs': self.oi_change_abs,
            'oi_change_pct': self.oi_change_pct,
            'oi_current': self.oi_current,
            'oi_previous': self.oi_previous,
            'oi_cap': self.oi_cap,
            'oi_utilization': self.oi_utilization,
            'price_change_pct': self.price_change_pct,
            'volume_change_pct': self.volume_change_pct,
            'oi_price_correlation': self.oi_price_correlation,
            'confidence_score': self.confidence_score,
            'magnitude_score': self.magnitude_score,
            'composite_score': self.composite_score,
            'timeframe': self.timeframe,
            'detection_window_start': self.detection_window_start.isoformat() if self.detection_window_start else None,
            'detection_window_end': self.detection_window_end.isoformat() if self.detection_window_end else None,
            'raw_data': self.raw_data,
            'title': self.title,
            'message': self.message,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'created_at': self.created_at.isoformat(),
            'is_processed': self.is_processed,
            'notification_sent': self.notification_sent,
            'recipient_count': self.recipient_count,
            'related_whale_alert_id': self.related_whale_alert_id,
            'cross_strategy_boost': self.cross_strategy_boost
        }


class OICapMonitoring(Base):
    """Model for tracking assets approaching OI caps."""

    __tablename__ = 'oi_cap_monitoring'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    oi_cap = Column(Float, nullable=False)
    current_oi = Column(Float, nullable=False)
    utilization = Column(Float, nullable=False, index=True)  # For finding high utilization assets
    exchange = Column(String(50), nullable=False, default='hyperliquid')

    # Warning levels crossed
    warning_80_triggered = Column(Boolean, default=False)
    warning_90_triggered = Column(Boolean, default=False)
    warning_95_triggered = Column(Boolean, default=False)
    at_cap_triggered = Column(Boolean, default=False)

    # Timestamps for warning triggers
    warning_80_at = Column(DateTime)
    warning_90_at = Column(DateTime)
    warning_95_at = Column(DateTime)
    at_cap_at = Column(DateTime)

    # Metadata
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Index for efficient monitoring queries
    __table_args__ = (
        Index('idx_oi_cap_utilization_desc', 'utilization'),
        Index('idx_oi_cap_symbol_updated', 'symbol', 'last_updated'),
    )

    def __repr__(self):
        return f"<OICapMonitoring(symbol={self.symbol}, utilization={self.utilization:.2%})>"

    def get_warning_level(self) -> str:
        """Get current warning level based on utilization."""
        if self.utilization >= 1.0:
            return 'AT_CAP'
        elif self.utilization >= 0.95:
            return 'CRITICAL'
        elif self.utilization >= 0.90:
            return 'HIGH'
        elif self.utilization >= 0.80:
            return 'WARNING'
        else:
            return 'NORMAL'

    def should_trigger_alert(self) -> bool:
        """Check if current state should trigger an alert."""
        level = self.get_warning_level()

        if level == 'AT_CAP' and not self.at_cap_triggered:
            return True
        elif level == 'CRITICAL' and not self.warning_95_triggered:
            return True
        elif level == 'HIGH' and not self.warning_90_triggered:
            return True
        elif level == 'WARNING' and not self.warning_80_triggered:
            return True

        return False

    def mark_warning_triggered(self, level: str):
        """Mark warning level as triggered."""
        now = datetime.utcnow()

        if level == 'WARNING':
            self.warning_80_triggered = True
            self.warning_80_at = now
        elif level == 'HIGH':
            self.warning_90_triggered = True
            self.warning_90_at = now
        elif level == 'CRITICAL':
            self.warning_95_triggered = True
            self.warning_95_at = now
        elif level == 'AT_CAP':
            self.at_cap_triggered = True
            self.at_cap_at = now