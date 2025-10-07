"""
Configuration management system for whale detection Telegram bot.
Handles YAML configuration loading, validation, and environment variable integration.
"""
import os
import yaml
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field
import json


@dataclass
class TelegramConfig:
    """Telegram bot configuration."""
    enabled: bool = False
    bot_token: str = ""
    parse_mode: str = "HTML"
    disable_web_page_preview: bool = True
    max_message_length: int = 4096
    channels: List[str] = field(default_factory=list)
    super_admins: List[int] = field(default_factory=list)
    admins: List[int] = field(default_factory=list)

    user_management: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Load bot token from environment if not provided
        if not self.bot_token:
            self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return self.enabled and bool(self.bot_token)


@dataclass
class DiscordConfig:
    """Discord webhook configuration."""
    enabled: bool = False
    webhook_url: str = ""
    username: str = "Whale Alert Bot"
    avatar_url: str = ""

    def __post_init__(self):
        if not self.webhook_url:
            self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL', '')

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return self.enabled and bool(self.webhook_url)


@dataclass
class EmailConfig:
    """Email notification configuration."""
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True
    from_email: str = ""
    recipients: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.username:
            self.username = os.getenv('EMAIL_USERNAME', '')
        if not self.password:
            self.password = os.getenv('EMAIL_PASSWORD', '')

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return (self.enabled and bool(self.smtp_host) and
                bool(self.username) and bool(self.password))


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str = "sqlite:///data/whale_bot.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10

    def __post_init__(self):
        # Allow database URL override from environment
        env_url = os.getenv('DATABASE_URL')
        if env_url:
            self.url = env_url


@dataclass
class WhaleDetectionConfig:
    """Whale detection algorithm configuration."""
    enabled: bool = True
    min_trade_value: float = 100000.0  # Minimum USD value for whale trade
    volume_threshold_multiplier: float = 3.0  # Volume must be X times average
    price_impact_threshold: float = 0.02  # 2% price impact threshold
    confidence_threshold: float = 0.7  # Minimum confidence score

    # Alert filtering
    min_severity_level: str = "MEDIUM"
    max_alerts_per_hour: int = 50
    cooldown_period_minutes: int = 15

    # Symbol and exchange filters
    enabled_symbols: List[str] = field(default_factory=list)  # Empty = all symbols
    enabled_exchanges: List[str] = field(default_factory=list)  # Empty = all exchanges
    excluded_symbols: List[str] = field(default_factory=list)
    excluded_exchanges: List[str] = field(default_factory=list)


@dataclass
class ProcessingConfig:
    """Alert processing configuration."""
    workers: int = 3
    queue_max_size: int = 1000
    batch_size: int = 10
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "logs/whale_bot.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True


class ConfigManager:
    """
    Complete configuration management system for whale detection bot.
    Handles YAML loading, validation, environment variable integration.
    """

    def __init__(self, config_file: str = "config/whale_bot.yaml"):
        self.config_file = Path(config_file)
        self.logger = logging.getLogger(__name__)

        # Configuration sections
        self.telegram = TelegramConfig()
        self.discord = DiscordConfig()
        self.email = EmailConfig()
        self.database = DatabaseConfig()
        self.whale_detection = WhaleDetectionConfig()
        self.processing = ProcessingConfig()
        self.logging = LoggingConfig()

        # Additional settings
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'

    def load_config(self) -> bool:
        """Load configuration from YAML file and environment variables."""
        try:
            # Load YAML configuration if file exists
            if self.config_file.exists():
                self.logger.info(f"Loading configuration from {self.config_file}")
                with open(self.config_file, 'r') as file:
                    yaml_config = yaml.safe_load(file)
                    self._apply_yaml_config(yaml_config)
            else:
                self.logger.warning(f"Configuration file {self.config_file} not found, using defaults")

            # Override with environment variables
            self._apply_environment_overrides()

            # Validate configuration
            validation_errors = self._validate_config()
            if validation_errors:
                self.logger.error("Configuration validation errors:")
                for error in validation_errors:
                    self.logger.error(f"  - {error}")
                return False

            self.logger.info("Configuration loaded and validated successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            return False

    def _apply_yaml_config(self, yaml_config: Dict[str, Any]):
        """Apply configuration from YAML dictionary."""
        # Telegram configuration
        telegram_config = yaml_config.get('telegram', {})
        self.telegram.enabled = telegram_config.get('enabled', self.telegram.enabled)
        self.telegram.bot_token = telegram_config.get('bot_token', self.telegram.bot_token)
        self.telegram.parse_mode = telegram_config.get('parse_mode', self.telegram.parse_mode)
        self.telegram.disable_web_page_preview = telegram_config.get(
            'disable_web_page_preview', self.telegram.disable_web_page_preview
        )
        self.telegram.channels = telegram_config.get('channels', self.telegram.channels)
        self.telegram.super_admins = telegram_config.get('super_admins', self.telegram.super_admins)
        self.telegram.admins = telegram_config.get('admins', self.telegram.admins)
        self.telegram.user_management = telegram_config.get(
            'user_management', self.telegram.user_management
        )

        # Discord configuration
        discord_config = yaml_config.get('discord', {})
        self.discord.enabled = discord_config.get('enabled', self.discord.enabled)
        self.discord.webhook_url = discord_config.get('webhook_url', self.discord.webhook_url)
        self.discord.username = discord_config.get('username', self.discord.username)
        self.discord.avatar_url = discord_config.get('avatar_url', self.discord.avatar_url)

        # Email configuration
        email_config = yaml_config.get('email', {})
        self.email.enabled = email_config.get('enabled', self.email.enabled)
        self.email.smtp_host = email_config.get('smtp_host', self.email.smtp_host)
        self.email.smtp_port = email_config.get('smtp_port', self.email.smtp_port)
        self.email.username = email_config.get('username', self.email.username)
        self.email.password = email_config.get('password', self.email.password)
        self.email.use_tls = email_config.get('use_tls', self.email.use_tls)
        self.email.from_email = email_config.get('from_email', self.email.from_email)
        self.email.recipients = email_config.get('recipients', self.email.recipients)

        # Database configuration
        database_config = yaml_config.get('database', {})
        self.database.url = database_config.get('url', self.database.url)
        self.database.echo = database_config.get('echo', self.database.echo)
        self.database.pool_size = database_config.get('pool_size', self.database.pool_size)
        self.database.max_overflow = database_config.get('max_overflow', self.database.max_overflow)

        # Whale detection configuration
        whale_config = yaml_config.get('whale_detection', {})
        self.whale_detection.enabled = whale_config.get('enabled', self.whale_detection.enabled)
        self.whale_detection.min_trade_value = whale_config.get(
            'min_trade_value', self.whale_detection.min_trade_value
        )
        self.whale_detection.volume_threshold_multiplier = whale_config.get(
            'volume_threshold_multiplier', self.whale_detection.volume_threshold_multiplier
        )
        self.whale_detection.price_impact_threshold = whale_config.get(
            'price_impact_threshold', self.whale_detection.price_impact_threshold
        )
        self.whale_detection.confidence_threshold = whale_config.get(
            'confidence_threshold', self.whale_detection.confidence_threshold
        )
        self.whale_detection.min_severity_level = whale_config.get(
            'min_severity_level', self.whale_detection.min_severity_level
        )
        self.whale_detection.max_alerts_per_hour = whale_config.get(
            'max_alerts_per_hour', self.whale_detection.max_alerts_per_hour
        )
        self.whale_detection.cooldown_period_minutes = whale_config.get(
            'cooldown_period_minutes', self.whale_detection.cooldown_period_minutes
        )
        self.whale_detection.enabled_symbols = whale_config.get(
            'enabled_symbols', self.whale_detection.enabled_symbols
        )
        self.whale_detection.enabled_exchanges = whale_config.get(
            'enabled_exchanges', self.whale_detection.enabled_exchanges
        )
        self.whale_detection.excluded_symbols = whale_config.get(
            'excluded_symbols', self.whale_detection.excluded_symbols
        )
        self.whale_detection.excluded_exchanges = whale_config.get(
            'excluded_exchanges', self.whale_detection.excluded_exchanges
        )

        # Processing configuration
        processing_config = yaml_config.get('processing', {})
        self.processing.workers = processing_config.get('workers', self.processing.workers)
        self.processing.queue_max_size = processing_config.get(
            'queue_max_size', self.processing.queue_max_size
        )
        self.processing.batch_size = processing_config.get('batch_size', self.processing.batch_size)
        self.processing.retry_attempts = processing_config.get(
            'retry_attempts', self.processing.retry_attempts
        )
        self.processing.retry_delay_seconds = processing_config.get(
            'retry_delay_seconds', self.processing.retry_delay_seconds
        )

        # Logging configuration
        logging_config = yaml_config.get('logging', {})
        self.logging.level = logging_config.get('level', self.logging.level)
        self.logging.format = logging_config.get('format', self.logging.format)
        self.logging.file = logging_config.get('file', self.logging.file)
        self.logging.max_file_size = logging_config.get(
            'max_file_size', self.logging.max_file_size
        )
        self.logging.backup_count = logging_config.get('backup_count', self.logging.backup_count)
        self.logging.console_output = logging_config.get(
            'console_output', self.logging.console_output
        )

    def _apply_environment_overrides(self):
        """Apply environment variable overrides."""
        # Environment variables take precedence over YAML config

        # Telegram overrides
        if os.getenv('TELEGRAM_ENABLED'):
            self.telegram.enabled = os.getenv('TELEGRAM_ENABLED').lower() == 'true'

        # Discord overrides
        if os.getenv('DISCORD_ENABLED'):
            self.discord.enabled = os.getenv('DISCORD_ENABLED').lower() == 'true'

        # Database overrides
        if os.getenv('DATABASE_ECHO'):
            self.database.echo = os.getenv('DATABASE_ECHO').lower() == 'true'

        # Logging overrides
        if os.getenv('LOG_LEVEL'):
            self.logging.level = os.getenv('LOG_LEVEL').upper()

        # Whale detection overrides
        if os.getenv('MIN_TRADE_VALUE'):
            try:
                self.whale_detection.min_trade_value = float(os.getenv('MIN_TRADE_VALUE'))
            except ValueError:
                self.logger.warning("Invalid MIN_TRADE_VALUE environment variable")

    def _validate_config(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Check if at least one notification channel is enabled
        channels_enabled = [
            self.telegram.is_valid(),
            self.discord.is_valid(),
            self.email.is_valid()
        ]

        if not any(channels_enabled):
            errors.append("At least one notification channel must be enabled and configured")

        # Validate specific configurations
        if self.telegram.enabled and not self.telegram.is_valid():
            errors.append("Telegram is enabled but bot token is not provided")

        if self.discord.enabled and not self.discord.is_valid():
            errors.append("Discord is enabled but webhook URL is not provided")

        if self.email.enabled and not self.email.is_valid():
            errors.append("Email is enabled but SMTP configuration is incomplete")

        # Validate whale detection parameters
        if self.whale_detection.min_trade_value <= 0:
            errors.append("Minimum trade value must be greater than 0")

        if self.whale_detection.volume_threshold_multiplier <= 0:
            errors.append("Volume threshold multiplier must be greater than 0")

        if not (0 < self.whale_detection.confidence_threshold <= 1):
            errors.append("Confidence threshold must be between 0 and 1")

        # Validate processing configuration
        if self.processing.workers <= 0:
            errors.append("Number of workers must be greater than 0")

        if self.processing.queue_max_size <= 0:
            errors.append("Queue max size must be greater than 0")

        return errors

    def save_config(self, output_file: Optional[str] = None) -> bool:
        """Save current configuration to YAML file."""
        try:
            if output_file is None:
                output_file = self.config_file

            config_dict = self.to_dict()

            # Ensure directory exists
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w') as file:
                yaml.dump(config_dict, file, default_flow_style=False, indent=2)

            self.logger.info(f"Configuration saved to {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save configuration: {str(e)}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            'telegram': {
                'enabled': self.telegram.enabled,
                'bot_token': self.telegram.bot_token if not os.getenv('TELEGRAM_BOT_TOKEN') else '',
                'parse_mode': self.telegram.parse_mode,
                'disable_web_page_preview': self.telegram.disable_web_page_preview,
                'channels': self.telegram.channels,
                'super_admins': self.telegram.super_admins,
                'admins': self.telegram.admins,
                'user_management': self.telegram.user_management
            },
            'discord': {
                'enabled': self.discord.enabled,
                'webhook_url': self.discord.webhook_url if not os.getenv('DISCORD_WEBHOOK_URL') else '',
                'username': self.discord.username,
                'avatar_url': self.discord.avatar_url
            },
            'email': {
                'enabled': self.email.enabled,
                'smtp_host': self.email.smtp_host,
                'smtp_port': self.email.smtp_port,
                'username': self.email.username if not os.getenv('EMAIL_USERNAME') else '',
                'password': self.email.password if not os.getenv('EMAIL_PASSWORD') else '',
                'use_tls': self.email.use_tls,
                'from_email': self.email.from_email,
                'recipients': self.email.recipients
            },
            'database': {
                'url': self.database.url if not os.getenv('DATABASE_URL') else '',
                'echo': self.database.echo,
                'pool_size': self.database.pool_size,
                'max_overflow': self.database.max_overflow
            },
            'whale_detection': {
                'enabled': self.whale_detection.enabled,
                'min_trade_value': self.whale_detection.min_trade_value,
                'volume_threshold_multiplier': self.whale_detection.volume_threshold_multiplier,
                'price_impact_threshold': self.whale_detection.price_impact_threshold,
                'confidence_threshold': self.whale_detection.confidence_threshold,
                'min_severity_level': self.whale_detection.min_severity_level,
                'max_alerts_per_hour': self.whale_detection.max_alerts_per_hour,
                'cooldown_period_minutes': self.whale_detection.cooldown_period_minutes,
                'enabled_symbols': self.whale_detection.enabled_symbols,
                'enabled_exchanges': self.whale_detection.enabled_exchanges,
                'excluded_symbols': self.whale_detection.excluded_symbols,
                'excluded_exchanges': self.whale_detection.excluded_exchanges
            },
            'processing': {
                'workers': self.processing.workers,
                'queue_max_size': self.processing.queue_max_size,
                'batch_size': self.processing.batch_size,
                'retry_attempts': self.processing.retry_attempts,
                'retry_delay_seconds': self.processing.retry_delay_seconds
            },
            'logging': {
                'level': self.logging.level,
                'format': self.logging.format,
                'file': self.logging.file,
                'max_file_size': self.logging.max_file_size,
                'backup_count': self.logging.backup_count,
                'console_output': self.logging.console_output
            }
        }

    def get_summary(self) -> str:
        """Get configuration summary for logging/debugging."""
        channels = []
        if self.telegram.is_valid():
            channels.append("Telegram")
        if self.discord.is_valid():
            channels.append("Discord")
        if self.email.is_valid():
            channels.append("Email")

        return (
            f"Configuration Summary:\n"
            f"  Environment: {self.environment}\n"
            f"  Debug: {self.debug}\n"
            f"  Enabled Channels: {', '.join(channels) if channels else 'None'}\n"
            f"  Database: {self.database.url}\n"
            f"  Min Trade Value: ${self.whale_detection.min_trade_value:,.2f}\n"
            f"  Processing Workers: {self.processing.workers}\n"
            f"  Log Level: {self.logging.level}"
        )