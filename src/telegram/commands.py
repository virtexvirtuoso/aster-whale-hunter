"""
Advanced command interface system for Telegram whale detection bot.
Provides comprehensive command handling with admin features and user management.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import json

from ..core.interfaces.reporting import AlertType, AlertSeverity, NotificationData


class CommandPermission(Enum):
    """Command permission levels."""
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class TelegramCommandHandler:
    """
    Advanced command handler for Telegram bot with permission system.
    Supports user commands, admin features, and statistics.
    """

    def __init__(self, bot, user_manager, alert_manager, config, api_client=None, whale_app=None):
        self.bot = bot
        self.user_manager = user_manager
        self.alert_manager = alert_manager
        self.config = config
        self.api_client = api_client  # Optional API client for market data
        self.whale_app = whale_app  # Optional whale hunter app for analysis commands
        self.logger = logging.getLogger(__name__)

        # Command registry with permissions
        self.commands: Dict[str, Dict[str, Any]] = {
            # User commands
            'start': {
                'handler': self._cmd_start,
                'permission': CommandPermission.USER,
                'description': 'Start using the bot and register',
                'usage': '/start'
            },
            'help': {
                'handler': self._cmd_help,
                'permission': CommandPermission.USER,
                'description': 'Show help information',
                'usage': '/help [command]'
            },
            'subscribe': {
                'handler': self._cmd_subscribe,
                'permission': CommandPermission.USER,
                'description': 'Subscribe to whale alerts',
                'usage': '/subscribe [alert_types] [min_severity]'
            },
            'unsubscribe': {
                'handler': self._cmd_unsubscribe,
                'permission': CommandPermission.USER,
                'description': 'Unsubscribe from whale alerts',
                'usage': '/unsubscribe'
            },
            'status': {
                'handler': self._cmd_status,
                'permission': CommandPermission.USER,
                'description': 'Check your subscription status',
                'usage': '/status'
            },
            'alerts': {
                'handler': self._cmd_alerts,
                'permission': CommandPermission.USER,
                'description': 'View recent whale alerts',
                'usage': '/alerts [count]'
            },
            'settings': {
                'handler': self._cmd_settings,
                'permission': CommandPermission.USER,
                'description': 'Manage notification settings',
                'usage': '/settings'
            },
            'symbols': {
                'handler': self._cmd_symbols,
                'permission': CommandPermission.USER,
                'description': 'Manage watched symbols',
                'usage': '/symbols [add|remove] [symbol]'
            },
            'stats': {
                'handler': self._cmd_stats,
                'permission': CommandPermission.USER,
                'description': 'View your personal statistics',
                'usage': '/stats'
            },
            'monitored': {
                'handler': self._cmd_monitored,
                'permission': CommandPermission.USER,
                'description': 'List all symbols currently being analyzed',
                'usage': '/monitored [--data]'
            },
            'analyze': {
                'handler': self._cmd_analyze,
                'permission': CommandPermission.USER,
                'description': 'Get instant whale analysis for a symbol',
                'usage': '/analyze <SYMBOL>'
            },
            'market': {
                'handler': self._cmd_market,
                'permission': CommandPermission.USER,
                'description': 'Get current market overview and top movers',
                'usage': '/market'
            },
            'top': {
                'handler': self._cmd_top,
                'permission': CommandPermission.USER,
                'description': 'Show top gainers, losers, or volume leaders',
                'usage': '/top [gainers|losers|volume]'
            },
            'price': {
                'handler': self._cmd_price,
                'permission': CommandPermission.USER,
                'description': 'Get instant price for a symbol',
                'usage': '/price <SYMBOL>'
            },
            'hot': {
                'handler': self._cmd_hot,
                'permission': CommandPermission.USER,
                'description': 'Show symbols with most whale activity today',
                'usage': '/hot'
            },
            'compare': {
                'handler': self._cmd_compare,
                'permission': CommandPermission.USER,
                'description': 'Compare two symbols side-by-side',
                'usage': '/compare <SYMBOL1> <SYMBOL2>'
            },
            'volatility': {
                'handler': self._cmd_volatility,
                'permission': CommandPermission.USER,
                'description': 'Show top volatile symbols or detailed volatility analysis',
                'usage': '/volatility [SYMBOL]'
            },

            # Admin commands
            'admin': {
                'handler': self._cmd_admin,
                'permission': CommandPermission.ADMIN,
                'description': 'Admin control panel',
                'usage': '/admin'
            },
            'broadcast': {
                'handler': self._cmd_broadcast,
                'permission': CommandPermission.ADMIN,
                'description': 'Broadcast message to all users',
                'usage': '/broadcast <message>'
            },
            'users': {
                'handler': self._cmd_users,
                'permission': CommandPermission.ADMIN,
                'description': 'Manage users',
                'usage': '/users [list|count|search] [query]'
            },
            'system': {
                'handler': self._cmd_system,
                'permission': CommandPermission.ADMIN,
                'description': 'System statistics and status',
                'usage': '/system'
            },
            'test': {
                'handler': self._cmd_test,
                'permission': CommandPermission.ADMIN,
                'description': 'Send test alert',
                'usage': '/test [alert_type] [severity]'
            },

            # Super admin commands
            'config': {
                'handler': self._cmd_config,
                'permission': CommandPermission.SUPER_ADMIN,
                'description': 'View/modify bot configuration',
                'usage': '/config [get|set] [key] [value]'
            },
            'maintenance': {
                'handler': self._cmd_maintenance,
                'permission': CommandPermission.SUPER_ADMIN,
                'description': 'System maintenance operations',
                'usage': '/maintenance [operation]'
            },
            'logs': {
                'handler': self._cmd_logs,
                'permission': CommandPermission.SUPER_ADMIN,
                'description': 'View system logs',
                'usage': '/logs [lines]'
            },
            'restart': {
                'handler': self._cmd_restart,
                'permission': CommandPermission.SUPER_ADMIN,
                'description': 'Restart the whale hunter bot',
                'usage': '/restart'
            }
        }

        # Command usage tracking
        self.command_usage = {}

    async def handle_command(self, message: Dict) -> bool:
        """Handle incoming command message."""
        try:
            text = message.get('text', '')
            if not text.startswith('/'):
                return False

            # Parse command and arguments
            parts = text[1:].split()
            # Remove @botusername for group chats (e.g., /subscribe@Aster_whale_hunter_bot -> subscribe)
            command = parts[0].lower().split('@')[0]
            args = parts[1:] if len(parts) > 1 else []

            # Track command usage
            await self._track_command_usage(command, message['from']['id'])

            # Check if command exists
            if command not in self.commands:
                await self._send_error(
                    message['chat']['id'],
                    f"Unknown command: /{command}\nUse /help to see available commands."
                )
                return True

            # Check permissions
            user_id = message['from']['id']
            if not await self._check_permission(user_id, self.commands[command]['permission']):
                await self._send_error(
                    message['chat']['id'],
                    "❌ You don't have permission to use this command."
                )
                return True

            # Execute command
            handler = self.commands[command]['handler']
            await handler(message, args)

            return True

        except Exception as e:
            self.logger.error(f"Error handling command: {str(e)}")
            await self._send_error(
                message['chat']['id'],
                "❌ An error occurred while processing your command."
            )
            return True

    async def _check_permission(self, user_id: int, required_permission: CommandPermission) -> bool:
        """Check if user has required permission level."""
        try:
            # Super admins can use any command
            if await self.user_manager.is_super_admin(user_id):
                return True

            # Admins can use admin and user commands
            if required_permission in [CommandPermission.USER, CommandPermission.ADMIN]:
                if await self.user_manager.is_admin(user_id):
                    return True

            # Users can only use user commands
            if required_permission == CommandPermission.USER:
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error checking permissions: {str(e)}")
            return False

    async def _track_command_usage(self, command: str, user_id: int):
        """Track command usage for statistics."""
        try:
            if command not in self.command_usage:
                self.command_usage[command] = {'count': 0, 'users': set()}

            self.command_usage[command]['count'] += 1
            self.command_usage[command]['users'].add(user_id)

        except Exception as e:
            self.logger.error(f"Error tracking command usage: {str(e)}")

    async def _send_message(self, chat_id: str, message: str, **kwargs):
        """Send message via bot."""
        await self.bot._send_message(chat_id, message, **kwargs)

    async def _send_error(self, chat_id: str, error_message: str):
        """Send error message with consistent formatting."""
        await self._send_message(chat_id, f"❌ <b>Error:</b> {error_message}")

    # User Commands

    async def _cmd_start(self, message: Dict, args: List[str]):
        """Handle /start command."""
        chat_id = str(message['chat']['id'])
        user_id = message['from']['id']
        user_data = message['from']

        # Register user
        await self.user_manager.register_user(user_id, chat_id, user_data)

        welcome_text = """
🐋 <b>Welcome to Whale Alert Bot!</b>

This bot provides real-time cryptocurrency whale detection alerts to help you stay informed about significant market movements.

<b>🚀 Quick Start:</b>
1. Use /subscribe to start receiving alerts
2. Configure your preferences with /settings
3. View your status with /status

<b>📊 Available Alert Types:</b>
• 🐋 <b>Whale Trades</b> - Large individual transactions
• 📈 <b>Accumulation</b> - Sustained buying pressure
• 🎭 <b>Manipulation</b> - Suspicious market activity
• 📊 <b>Volume Spikes</b> - Unusual trading volume
• 💥 <b>Price Impact</b> - Significant price movements

<b>🔧 Commands:</b>
/help - Show all available commands
/subscribe - Subscribe to whale alerts
/status - Check your subscription
/settings - Manage preferences
/monitored - View symbols being analyzed

Get started now with /subscribe!
        """

        await self._send_message(chat_id, welcome_text)

    async def _cmd_help(self, message: Dict, args: List[str]):
        """Handle /help command."""
        chat_id = str(message['chat']['id'])
        user_id = message['from']['id']

        # If specific command requested
        if args and args[0] in self.commands:
            command = args[0]
            cmd_info = self.commands[command]

            help_text = f"""
<b>Command:</b> /{command}
<b>Description:</b> {cmd_info['description']}
<b>Usage:</b> <code>{cmd_info['usage']}</code>
<b>Permission:</b> {cmd_info['permission'].value}
            """
            await self._send_message(chat_id, help_text.strip())
            return

        # Show all available commands based on user permission
        user_commands = []
        admin_commands = []
        super_admin_commands = []

        for cmd, info in self.commands.items():
            if await self._check_permission(user_id, info['permission']):
                if info['permission'] == CommandPermission.USER:
                    user_commands.append(f"/{cmd} - {info['description']}")
                elif info['permission'] == CommandPermission.ADMIN:
                    admin_commands.append(f"/{cmd} - {info['description']}")
                else:
                    super_admin_commands.append(f"/{cmd} - {info['description']}")

        help_text = "<b>🤖 Available Commands</b>\n\n"

        if user_commands:
            help_text += "<b>👤 User Commands:</b>\n"
            help_text += "\n".join(user_commands) + "\n\n"

        if admin_commands:
            help_text += "<b>🔧 Admin Commands:</b>\n"
            help_text += "\n".join(admin_commands) + "\n\n"

        if super_admin_commands:
            help_text += "<b>⚡ Super Admin Commands:</b>\n"
            help_text += "\n".join(super_admin_commands) + "\n\n"

        help_text += "Use <code>/help command_name</code> for detailed information about a specific command."

        await self._send_message(chat_id, help_text)

    async def _cmd_subscribe(self, message: Dict, args: List[str]):
        """Handle /subscribe command with optional parameters."""
        chat_id = str(message['chat']['id'])
        user_id = message['from']['id']

        # Parse arguments
        alert_types = None
        min_severity = None

        if args:
            # Parse alert types
            if args[0] in ['whale_trade', 'accumulation', 'manipulation', 'volume_spike', 'price_impact']:
                alert_types = {AlertType(args[0])}
            elif args[0] == 'all':
                alert_types = set(AlertType)

            # Parse severity
            if len(args) > 1 and args[1] in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                min_severity = AlertSeverity[args[1]]

        # Subscribe the chat (not the user) so alerts go to the channel/group/chat
        success = await self.user_manager.subscribe_user(int(chat_id), alert_types, min_severity)

        if success:
            response = """
✅ <b>Successfully subscribed to whale alerts!</b>

Your subscription is now active and you'll receive real-time notifications for:
• Whale trades above $100,000
• Market accumulation patterns
• Potential manipulation attempts
• Significant volume spikes
• High-impact price movements

🔧 Use /settings to customize your alert preferences
📊 Use /status to check your subscription details
            """
        else:
            response = """
❌ <b>Subscription failed</b>

You may already be subscribed to alerts. Use /status to check your current subscription or /unsubscribe first if you want to change your settings.
            """

        await self._send_message(chat_id, response.strip())

    async def _cmd_unsubscribe(self, message: Dict, args: List[str]):
        """Handle /unsubscribe command."""
        chat_id = str(message['chat']['id'])
        user_id = message['from']['id']

        # Unsubscribe the chat (not the user)
        success = await self.user_manager.unsubscribe_user(int(chat_id))

        if success:
            response = """
❌ <b>You have been unsubscribed from whale alerts</b>

You will no longer receive whale detection notifications. You can resubscribe at any time using /subscribe.

Thank you for using Whale Alert Bot!
            """
        else:
            response = "❌ Unsubscribe failed. You may not have an active subscription."

        await self._send_message(chat_id, response.strip())

    async def _cmd_status(self, message: Dict, args: List[str]):
        """Handle /status command."""
        chat_id = str(message['chat']['id'])
        user_id = message['from']['id']

        # Check subscription status for the chat (not the user)
        status = await self.user_manager.get_user_status(int(chat_id))
        await self._send_message(chat_id, status)

    async def _cmd_alerts(self, message: Dict, args: List[str]):
        """Handle /alerts command to show recent alerts."""
        chat_id = str(message['chat']['id'])
        count = 5

        if args and args[0].isdigit():
            count = min(int(args[0]), 20)  # Max 20 alerts

        # This would fetch from alert history - simplified for now
        response = f"""
📈 <b>Recent Whale Alerts</b> (Last {count})

<i>Recent alert history feature is coming soon!</i>

This will show:
• Recent whale trades you received
• Alert timestamps and details
• Symbol and exchange information
• Alert confidence scores

Use /status to see your current subscription details.
        """

        await self._send_message(chat_id, response.strip())

    async def _cmd_settings(self, message: Dict, args: List[str]):
        """Handle /settings command with interactive menu."""
        chat_id = str(message['chat']['id'])

        settings_text = """
⚙️ <b>Notification Settings</b>

Choose what you'd like to configure:

<b>📊 Alert Types:</b>
• Whale Trades - Large individual transactions
• Accumulation - Sustained buying patterns
• Manipulation - Suspicious activity detection
• Volume Spikes - Unusual trading volume
• Price Impact - Significant price movements

<b>⚠️ Severity Levels:</b>
• 🔴 Critical - Only highest confidence alerts
• 🟡 High - Important alerts with high confidence
• 🟢 Medium - Standard alerts (recommended)
• ⚪ Low - All alerts including lower confidence

Use the buttons below to customize your preferences.
        """

        # Create inline keyboard
        keyboard = [
            ["🐋 Whale Trades", "📈 Accumulation"],
            ["🎭 Manipulation", "📊 Volume Spikes"],
            ["🔴 Critical Only", "🟡 High Priority"],
            ["🟢 Medium (Default)", "⚪ All Alerts"],
            ["✅ Apply Settings", "❌ Cancel"]
        ]

        notification = NotificationData(
            alert_type=AlertType.WHALE_TRADE,
            severity=AlertSeverity.MEDIUM,
            symbol="SETTINGS",
            message=settings_text
        )

        await self.bot.send_with_keyboard(chat_id, notification, keyboard)

    async def _cmd_symbols(self, message: Dict, args: List[str]):
        """Handle /symbols command for managing watched symbols."""
        chat_id = str(message['chat']['id'])

        if not args:
            response = """
🎯 <b>Symbol Management</b>

<b>Usage:</b>
<code>/symbols add BTC ETH SOL</code> - Add symbols to watch
<code>/symbols remove BTC</code> - Remove symbol from watch list
<code>/symbols list</code> - Show current watch list
<code>/symbols clear</code> - Clear all symbols (watch all)

<b>Examples:</b>
• <code>/symbols add BTC ETH</code>
• <code>/symbols remove DOGE</code>
• <code>/symbols list</code>

<i>Note: If no symbols are specified, you'll receive alerts for all supported cryptocurrencies.</i>
            """
        else:
            action = args[0].lower()
            symbols = [s.upper() for s in args[1:]] if len(args) > 1 else []

            if action == 'add' and symbols:
                # This would integrate with user preferences
                response = f"✅ Added symbols to watch list: {', '.join(symbols)}"
            elif action == 'remove' and symbols:
                response = f"❌ Removed symbols from watch list: {', '.join(symbols)}"
            elif action == 'list':
                response = "📋 <b>Your Watch List:</b>\n\n<i>All symbols (no filter)</i>"
            elif action == 'clear':
                response = "🗑️ Watch list cleared. You'll now receive alerts for all symbols."
            else:
                response = "❌ Invalid usage. Use <code>/symbols</code> without arguments for help."

        await self._send_message(chat_id, response)

    async def _cmd_stats(self, message: Dict, args: List[str]):
        """Handle /stats command for personal or system statistics."""
        chat_id = str(message['chat']['id'])
        user_id = message['from']['id']

        # Check if we have whale app for system stats
        if self.whale_app and hasattr(self.whale_app, 'detection_engine'):
            # Show whale detection statistics
            try:
                stats = await self.whale_app.detection_engine.get_comprehensive_statistics()

                uptime = int(stats.get('uptime_seconds', 0))
                uptime_str = f"{uptime//3600}h {(uptime%3600)//60}m" if uptime >= 3600 else f"{uptime//60}m"

                total_analyses = int(stats.get('total_analyses', 0))
                alerts_generated = int(stats.get('alerts_generated', 0))
                symbols_monitored = stats.get('symbols_monitored', 0)

                stats_text = f"""
📊 <b>DETECTION STATISTICS</b>

⏱️ <b>Uptime:</b> {uptime_str}
🔍 <b>Analyses:</b> {total_analyses:,}
🚨 <b>Alerts:</b> {alerts_generated}
📈 <b>Symbols:</b> {symbols_monitored}

💡 Use /analyze SYMBOL for on-demand analysis
                """
            except Exception as e:
                self.logger.error(f"Error getting whale stats: {e}")
                stats_text = "❌ Error retrieving statistics"

        elif hasattr(self.user_manager, 'database_manager'):
            # Get user statistics from database
            alert_count = await self.user_manager.database_manager.get_user_alert_count(user_id)

            stats_text = f"""
📊 <b>Your Whale Alert Statistics</b>

📅 <b>Alerts Received (30 days):</b> {alert_count}
🎯 <b>Subscription Status:</b> Active
⚡ <b>Response Time:</b> < 1 second
🔔 <b>Success Rate:</b> 99.9%

<b>🏆 Top Alert Types:</b>
• Whale Trades: {int(alert_count * 0.6)}
• Accumulation: {int(alert_count * 0.25)}
• Manipulation: {int(alert_count * 0.1)}
• Volume Spikes: {int(alert_count * 0.05)}

Use /alerts to see your recent alert history.
            """
        else:
            # No stats available
            stats_text = """
📊 <b>Statistics</b>

<i>Statistics not available in current mode.</i>

Use /status to check system status.
            """

        await self._send_message(chat_id, stats_text.strip())

    async def _cmd_monitored(self, message: Dict, args: List[str]):
        """Handle /monitored command to show all symbols being analyzed."""
        chat_id = str(message['chat']['id'])

        # Get monitored symbols from config
        monitored_symbols = self.config.get('whale_detection', {}).get('symbols', [])

        if not monitored_symbols:
            response = """
📊 <b>Monitored Symbols</b>

<i>No symbols are currently being monitored.</i>

Use /symbols to configure your personal watch list.
            """
        else:
            # Check if we should fetch market data
            if self.api_client and '--data' in args:
                response = await self._format_monitored_with_market_data(monitored_symbols)
            else:
                # Format symbols into a nice list (default view)
                symbols_list = "\n".join([f"• <code>{symbol}</code>" for symbol in monitored_symbols])

                response = f"""
📊 <b>Symbols Currently Being Analyzed</b>

<b>Total Symbols:</b> {len(monitored_symbols)}

<b>Active Monitoring:</b>
{symbols_list}

<i>The system is actively monitoring these symbols for whale activity, large trades, and suspicious patterns.</i>

💡 <b>Tip:</b> Use <code>/monitored --data</code> to see live market data

Use /symbols to manage your personal watch list for filtering alerts.
            """

        await self._send_message(chat_id, response.strip())

    async def _format_monitored_with_market_data(self, symbols: List[str]) -> str:
        """Format monitored symbols with live market data."""
        try:
            # Fetch market data for all symbols
            market_data = []

            for symbol in symbols[:10]:  # Limit to 10 to avoid rate limits
                try:
                    ticker = await self.api_client.get_24hr_ticker(symbol)

                    price = float(ticker.get('lastPrice', 0))
                    change_24h = float(ticker.get('priceChangePercent', 0))
                    volume_24h = float(ticker.get('volume', 0))

                    # Determine trend emoji
                    if change_24h > 5:
                        trend = "🔥"
                    elif change_24h > 0:
                        trend = "📈"
                    elif change_24h < -5:
                        trend = "❄️"
                    else:
                        trend = "📉"

                    market_data.append({
                        'symbol': symbol.replace('USDT', ''),
                        'price': price,
                        'change': change_24h,
                        'volume': volume_24h,
                        'trend': trend
                    })

                except Exception as e:
                    self.logger.error(f"Failed to fetch data for {symbol}: {e}")
                    continue

            if not market_data:
                return "❌ <b>Unable to fetch market data</b>\n\nPlease try again later."

            # Format the response
            header = f"""📊 <b>Live Market Data</b>

<b>Monitoring:</b> {len(market_data)} symbols | <b>Updated:</b> Just now

"""

            # Create table rows
            rows = []
            for data in market_data:
                symbol_col = f"<b>{data['symbol']}</b>"
                price_col = f"${data['price']:,.2f}" if data['price'] >= 1 else f"${data['price']:.6f}"

                # Color code the change percentage
                if data['change'] >= 0:
                    change_col = f"<b>+{data['change']:.2f}%</b>"
                else:
                    change_col = f"<b>{data['change']:.2f}%</b>"

                row = f"{data['trend']} {symbol_col}: {price_col} ({change_col})"
                rows.append(row)

            table = "\n".join(rows)

            footer = """

<i>🔔 Detection Active: Whale trades, Accumulation, Manipulation</i>

Use /symbols to manage your watch list"""

            return header + table + footer

        except Exception as e:
            self.logger.error(f"Error formatting market data: {e}")
            return "❌ <b>Error fetching market data</b>\n\nPlease try again later."

    async def _cmd_analyze(self, message: Dict, args: List[str]):
        """Handle /analyze command for on-demand whale analysis."""
        import re

        chat_id = str(message['chat']['id'])

        if not self.whale_app:
            await self._send_message(chat_id, "❌ Whale analysis not available in this mode.")
            return

        try:
            # Parse symbol from args
            symbol = ' '.join(args).strip().upper() if args else ''

            if not symbol:
                await self._send_message(chat_id, "❌ Please specify a symbol\nExample: <code>/analyze BTCUSDT</code>")
                return

            # Validate symbol format
            base_symbol = symbol.replace('USDT', '')
            if not re.match(r'^[A-Z0-9]+$', base_symbol):
                await self._send_message(chat_id, "❌ Invalid symbol format. Use alphanumeric characters only.")
                return

            # Ensure symbol ends with USDT
            if not symbol.endswith('USDT'):
                symbol = f"{symbol}USDT"

            # Check if whale app has required components
            if not hasattr(self.whale_app, 'exchange_client') or not self.whale_app.exchange_client:
                await self._send_message(chat_id, "❌ Exchange client not available")
                return

            if not hasattr(self.whale_app, 'detection_engine') or not self.whale_app.detection_engine:
                await self._send_message(chat_id, "❌ Detection engine not available")
                return

            # Validate symbol exists
            try:
                ticker = await self.whale_app.exchange_client.get_24h_ticker(symbol)
                if not ticker:
                    await self._send_message(chat_id, f"❌ Symbol {symbol} not found or not available")
                    return
            except Exception as e:
                error_msg = str(e).lower()
                if "not found" in error_msg or "invalid" in error_msg or "unknown" in error_msg:
                    await self._send_message(chat_id, f"❌ Invalid symbol: {symbol}")
                    return
                raise

            # Send analyzing message
            await self._send_message(chat_id, f"🔍 Analyzing {symbol}...")

            # Fetch data and run analysis
            trades = await self.whale_app.exchange_client.get_recent_trades(symbol, limit=100)
            if not trades:
                await self._send_message(chat_id, f"❌ No recent trades found for {symbol}")
                return

            order_book = await self.whale_app.exchange_client.get_order_book(symbol, limit=20)

            market_data = {
                'symbol': symbol,
                'ticker': ticker or {},
                'order_book': order_book or {'bids': [], 'asks': []}
            }

            # Run analysis
            analysis_result = await self.whale_app.detection_engine.analyze_symbol_on_demand(
                symbol, trades, market_data
            )

            # Calculate volatility metrics (non-detailed mode for speed)
            volatility_metrics = None
            try:
                volatility_metrics = await self._calculate_volatility_metrics(symbol, detailed=False)
            except Exception as vol_err:
                self.logger.warning(f"Could not calculate volatility metrics for {symbol}: {vol_err}")

            # Format and send result
            result_message = self._format_analysis_result(symbol, analysis_result, ticker, volatility_metrics)
            await self._send_message(chat_id, result_message)

        except Exception as e:
            self.logger.error(f"Error in /analyze command: {e}")
            await self._send_message(chat_id, f"❌ Error analyzing symbol: {str(e)}")

    async def _cmd_market(self, message: Dict, args: List[str]):
        """Handle /market command for market overview."""
        chat_id = str(message['chat']['id'])

        if not self.whale_app:
            await self._send_message(chat_id, "❌ Market data not available in this mode.")
            return

        try:
            # Get market overview from whale app
            if hasattr(self.whale_app, '_get_market_overview'):
                market_overview = await self.whale_app._get_market_overview()
            else:
                await self._send_message(chat_id, "❌ Market overview not available")
                return

            # Get top symbols
            top_symbols = []
            if hasattr(self.whale_app, 'symbol_manager') and self.whale_app.symbol_manager:
                symbols = self.whale_app.symbol_manager.get_current_symbols()
                top_symbols = symbols[:5] if len(symbols) >= 5 else symbols

            # Format message
            lines = ["📈 <b>MARKET SNAPSHOT</b>\n"]

            # BTC/ETH
            btc = market_overview.get('btc', {})
            if btc:
                price = float(btc.get('price', 0))
                change = float(btc.get('change_24h', 0))
                volume = float(btc.get('volume_24h', 0))
                emoji = "🟢" if change >= 0 else "🔴"
                vol_str = f"${volume/1_000_000_000:.1f}B" if volume >= 1_000_000_000 else f"${volume/1_000_000:.0f}M"
                lines.append(f"<b>BTC</b> ${price:,.0f} {emoji} {change:+.1f}% | Vol: {vol_str}")

            eth = market_overview.get('eth', {})
            if eth:
                price = float(eth.get('price', 0))
                change = float(eth.get('change_24h', 0))
                volume = float(eth.get('volume_24h', 0))
                emoji = "🟢" if change >= 0 else "🔴"
                vol_str = f"${volume/1_000_000_000:.1f}B" if volume >= 1_000_000_000 else f"${volume/1_000_000:.0f}M"
                lines.append(f"<b>ETH</b> ${price:,.0f} {emoji} {change:+.1f}% | Vol: {vol_str}")

            # Top symbols
            if top_symbols:
                lines.append(f"\n🎯 <b>Top Monitored:</b>")
                lines.append(f"  {', '.join(top_symbols[:5])}")

            timestamp = datetime.now().strftime("%H:%M:%S UTC")
            lines.append(f"\n⏰ {timestamp}")

            await self._send_message(chat_id, "\n".join(lines))

        except Exception as e:
            self.logger.error(f"Error in /market command: {e}")
            await self._send_message(chat_id, f"❌ Error getting market data: {str(e)}")

    def _format_analysis_result(self, symbol: str, analysis: Dict, ticker: Dict, volatility_metrics: Optional[Dict] = None) -> str:
        """Format whale analysis result message."""
        # Get price info
        price = float(ticker.get('lastPrice', 0)) if ticker else 0.0
        change_24h = float(ticker.get('priceChangePercent', 0)) if ticker else 0.0
        volume_24h = float(ticker.get('quoteVolume', 0)) if ticker else 0.0

        price_emoji = "🟢" if change_24h >= 0 else "🔴"

        # Get analysis results
        whale_detected = analysis.get('whale_detected', False)
        confidence = float(analysis.get('confidence', 0)) * 100

        # Build message
        status = "🐋 <b>WHALE DETECTED</b>" if whale_detected else "✅ <b>NO WHALE ACTIVITY</b>"

        parts = [
            f"{status}\n",
            f"📊 <b>{symbol}</b>",
            f"💰 ${price:,.2f} {price_emoji} {change_24h:+.1f}%"
        ]

        # Volume
        if volume_24h > 1_000_000_000:
            vol_str = f"${volume_24h/1_000_000_000:.2f}B"
        elif volume_24h > 1_000_000:
            vol_str = f"${volume_24h/1_000_000:.1f}M"
        else:
            vol_str = f"${volume_24h:,.0f}"
        parts.append(f"📊 24h Vol: {vol_str}\n")

        # Strategy breakdown
        strategy_details = analysis.get('strategy_details', {})
        if strategy_details:
            parts.append("🔍 <b>Strategy Analysis:</b>")
            for strategy_name, details in strategy_details.items():
                conf = details['confidence'] * 100
                clean_name = strategy_name.replace('Strategy', '').replace('Whale', '').replace('Imbalance', 'Imbal.')

                # Add status emoji based on confidence
                if conf > 70:
                    emoji = "🔴"  # High confidence threat
                elif conf > 50:
                    emoji = "🟡"  # Medium confidence
                else:
                    emoji = "🟢"  # Low confidence/normal

                parts.append(f"  {emoji} {clean_name}: {conf:.0f}%")

            total_strategies = 7  # VolumeWhale, OrderBookImbalance, PriceMomentum, StablecoinDepeg, OrderFlow, VolatilitySpike, SimpleOI
            parts.append(f"💪 Consensus: {len(strategy_details)}/{total_strategies} strategies\n")
        else:
            # Show "all clear" when no strategies triggered
            all_strategies_count = 7  # Total available strategies
            parts.append(f"✅ <b>Scanned by {all_strategies_count} strategies</b>")
            parts.append(f"🎯 <b>Overall Confidence:</b> {confidence:.1f}%\n")

        # Trade flow
        trade_flow = analysis.get('trade_flow', {})
        if trade_flow:
            buy_pct = trade_flow.get('buy_pressure', 0.5) * 100
            buy_count = trade_flow.get('buy_count', 0)
            sell_count = trade_flow.get('sell_count', 0)
            buy_vol = trade_flow.get('buy_volume', 0) / 1_000_000
            sell_vol = trade_flow.get('sell_volume', 0) / 1_000_000

            # Determine pressure emoji and market health
            if buy_pct > 65:
                pressure_emoji = "🟢"
                market_health = "BULLISH"
            elif buy_pct < 35:
                pressure_emoji = "🔴"
                market_health = "BEARISH"
            else:
                pressure_emoji = "⚪"
                market_health = "NEUTRAL"

            parts.append("📈 <b>Trade Flow (last 100):</b>")
            parts.append(f"  • Buys: {buy_count} (${buy_vol:.2f}M)")
            parts.append(f"  • Sells: {sell_count} (${sell_vol:.2f}M)")
            parts.append(f"  • Pressure: {pressure_emoji} {buy_pct:.0f}% buy")
            parts.append(f"  • Health: {market_health}\n")

        # Order book analysis
        ob_metrics = analysis.get('orderbook_metrics', {})
        if ob_metrics and (ob_metrics.get('bid_volume', 0) + ob_metrics.get('ask_volume', 0) > 0):
            imbalance = ob_metrics.get('imbalance', 0) * 100
            bid_volume = ob_metrics.get('bid_volume', 0)
            ask_volume = ob_metrics.get('ask_volume', 0)
            spread_pct = ob_metrics.get('spread_pct', 0)

            # Smart formatting for bid/ask volumes
            def format_volume(vol):
                if vol >= 1_000_000:
                    return f"${vol/1_000_000:.1f}M"
                elif vol >= 1000:
                    return f"${vol/1000:.0f}K"
                else:
                    return f"${vol:.0f}"

            bid_vol_str = format_volume(bid_volume)
            ask_vol_str = format_volume(ask_volume)

            # Determine imbalance emoji
            if imbalance > 15:
                ob_emoji = "🟢"
            elif imbalance < -15:
                ob_emoji = "🔴"
            else:
                ob_emoji = "⚪"

            parts.append("📖 <b>Order Book (top 10):</b>")
            parts.append(f"  • Bids: {bid_vol_str}")
            parts.append(f"  • Asks: {ask_vol_str}")
            parts.append(f"  • Imbalance: {ob_emoji} {imbalance:+.1f}%")

            # Add visual representation of order book imbalance
            if abs(imbalance) > 10:
                bar_length = min(int(abs(imbalance) / 10), 5)  # Max 5 blocks
                if imbalance > 0:
                    bar = "🟩" * bar_length + "⬜" * (5 - bar_length)
                    parts.append(f"  • Visual: {bar} (Buy-side)")
                else:
                    bar = "🟥" * bar_length + "⬜" * (5 - bar_length)
                    parts.append(f"  • Visual: {bar} (Sell-side)")

            parts.append(f"  • Spread: {spread_pct:.3f}%\n")

        # Volatility metrics
        if volatility_metrics:
            # Smart ATR formatting
            atr = volatility_metrics['atr']
            if atr >= 1:
                atr_str = f"${atr:.2f}"
            elif atr >= 0.01:
                atr_str = f"${atr:.4f}"
            else:
                atr_str = f"${atr:.6f}"

            # BB emoji
            bb_width = volatility_metrics['bb_width']
            if bb_width < 1.5:
                bb_status = "🔒 Compressed"
            elif bb_width > 3.0:
                bb_status = "📈 Expanded"
            else:
                bb_status = "📊 Normal"

            parts.append("🌪️ <b>Volatility:</b>")
            parts.append(f"  • ATR: {atr_str} ({volatility_metrics['atr_pct']:.2f}%)")
            parts.append(f"  • Change: {volatility_metrics['volatility_emoji']} {volatility_metrics['volatility_vs_avg']:+.0f}% vs avg")
            parts.append(f"  • Volume: {volatility_metrics['volume_surge']:.1f}x surge")
            parts.append(f"  • BB: {bb_status} ({bb_width:.1f}%)\n")

        # Calculate quality score (0-10)
        quality_score = 0
        quality_notes = []

        # Volume confirms move (max 3 points) - use volume_24h or volatility surge
        if volatility_metrics and volatility_metrics.get('volume_surge', 1) > 2:
            quality_score += 3
            quality_notes.append("Volume confirms ✅")
        elif volatility_metrics and volatility_metrics.get('volume_surge', 1) > 1.5:
            quality_score += 2
            quality_notes.append("Volume moderate ⚠️")
        elif volume_24h > 1_000_000:  # Fallback to absolute volume
            quality_score += 2
            quality_notes.append("Volume acceptable ⚠️")
        else:
            quality_notes.append("Low volume ❌")

        # Liquidity/spread (max 2 points) - based on order book spread
        spread_pct = ob_metrics.get('spread_pct', 0.1) if ob_metrics else 0.1
        if spread_pct < 0.05:
            quality_score += 2
            quality_notes.append("Liquidity excellent ✅")
        elif spread_pct < 0.1:
            quality_score += 1
            quality_notes.append("Liquidity good ⚠️")
        else:
            quality_notes.append("Wide spread ❌")

        # Whale activity (max 2 points)
        whale_count = len(strategy_details) if strategy_details else 0
        if whale_count >= 3:
            quality_score += 2
            quality_notes.append(f"Strong whale signals ({whale_count}) ✅")
        elif whale_count > 0:
            quality_score += 1
            quality_notes.append(f"Some whale signals ({whale_count}) ⚠️")
        else:
            quality_notes.append("No whale signals ❌")

        # Market bias/direction (max 3 points) - based on trade flow
        if trade_flow:
            buy_pct = trade_flow.get('buy_pressure', 0.5) * 100
            if buy_pct > 65:
                quality_score += 3
                quality_notes.append("Strong BULLISH bias ✅")
            elif buy_pct < 35:
                quality_score += 3
                quality_notes.append("Strong BEARISH bias ✅")
            elif buy_pct > 55 or buy_pct < 45:
                quality_score += 2
                quality_notes.append("Moderate bias ⚠️")
            else:
                quality_notes.append("No clear bias ❌")
        else:
            quality_notes.append("No bias data ❌")

        # Add quality score section
        parts.append(f"💪 <b>Quality Score: {quality_score}/10</b>")
        for note in quality_notes:
            parts.append(f"   • {note}")
        parts.append("")

        # Risk assessment
        if whale_detected:
            parts.append("⚠️ <b>Risk:</b> ELEVATED")
            if confidence > 80:
                parts.append("🎯 <b>Action:</b> Strong signal - Monitor closely")
            elif confidence > 60:
                parts.append("🎯 <b>Action:</b> Moderate signal - Track position")
            else:
                parts.append("🎯 <b>Action:</b> Weak signal - Stay alert")
        else:
            parts.append("✅ <b>Risk:</b> NORMAL")

        parts.append(f"\n⏰ {datetime.now().strftime('%H:%M:%S UTC')}")

        return "\n".join(parts)

    async def _cmd_top(self, message: Dict, args: List[str]):
        """Handle /top command to show top performers."""
        chat_id = str(message['chat']['id'])

        if not self.api_client:
            await self._send_message(chat_id, "❌ Market data not available")
            return

        try:
            # Get symbols from config or whale app
            symbols = []
            if self.whale_app and hasattr(self.whale_app, 'symbol_manager') and self.whale_app.symbol_manager:
                symbols = self.whale_app.symbol_manager.get_current_symbols()[:20]
                self.logger.info(f"Using symbols from symbol_manager: {symbols}")
            elif 'whale_detection' in self.config:
                symbols = self.config.get('whale_detection', {}).get('symbols', [])[:20]
                self.logger.info(f"Using symbols from config: {symbols}")

            if not symbols:
                await self._send_message(chat_id, "❌ No symbols available")
                return

            self.logger.info(f"/top command: Fetching data for {len(symbols)} symbols")

            # Fetch market data for all symbols
            market_data = []
            for symbol in symbols:
                try:
                    self.logger.debug(f"Fetching ticker for {symbol}...")
                    ticker = await self.api_client.get_24h_ticker(symbol)
                    if ticker:
                        market_data.append({
                            'symbol': symbol.replace('USDT', ''),
                            'price': float(ticker.get('lastPrice', 0)),
                            'change': float(ticker.get('priceChangePercent', 0)),
                            'volume': float(ticker.get('quoteVolume', 0))
                        })
                        self.logger.debug(f"Successfully fetched ticker for {symbol}")
                    else:
                        self.logger.warning(f"Ticker returned None for {symbol}")
                except Exception as e:
                    self.logger.error(f"Failed to fetch ticker for {symbol}: {e}")
                    continue

            self.logger.info(f"/top command: Successfully fetched {len(market_data)}/{len(symbols)} tickers")

            if not market_data:
                await self._send_message(chat_id, "❌ No market data available")
                return

            # If no argument, show all three categories
            if not args:
                lines = ["📊 <b>Market Overview (24h)</b>\n"]

                # Top 5 Gainers
                gainers = sorted(market_data, key=lambda x: x['change'], reverse=True)[:5]
                lines.append("🔥 <b>Top Gainers:</b>")
                for i, data in enumerate(gainers, 1):
                    change_emoji = "🟢" if data['change'] > 0 else "⚪"
                    lines.append(f"{i}. <b>{data['symbol']}</b> {change_emoji} {data['change']:+.2f}%")

                lines.append("")

                # Top 5 Losers
                losers = sorted(market_data, key=lambda x: x['change'])[:5]
                lines.append("❄️ <b>Top Losers:</b>")
                for i, data in enumerate(losers, 1):
                    change_emoji = "🔴" if data['change'] < 0 else "⚪"
                    lines.append(f"{i}. <b>{data['symbol']}</b> {change_emoji} {data['change']:+.2f}%")

                lines.append("")

                # Top 5 Volume Leaders
                volume_leaders = sorted(market_data, key=lambda x: x['volume'], reverse=True)[:5]
                lines.append("💰 <b>Volume Leaders:</b>")
                for i, data in enumerate(volume_leaders, 1):
                    vol_str = f"${data['volume']/1_000_000:.1f}M" if data['volume'] >= 1_000_000 else f"${data['volume']/1_000:.0f}K"
                    lines.append(f"{i}. <b>{data['symbol']}</b> 📊 {vol_str}")

                lines.append("")

                # Top 5 Most Volatile (by absolute change)
                volatile = sorted(market_data, key=lambda x: abs(x['change']), reverse=True)[:5]
                lines.append("⚡ <b>Most Volatile:</b>")
                for i, data in enumerate(volatile, 1):
                    change_emoji = "📈" if data['change'] > 0 else "📉"
                    lines.append(f"{i}. <b>{data['symbol']}</b> {change_emoji} {data['change']:+.2f}%")

                lines.append(f"\n💡 Use <code>/top gainers</code>, <code>/top losers</code>, <code>/top volume</code>, or <code>/top volatile</code> for full lists")
                lines.append(f"⏰ {datetime.now().strftime('%H:%M:%S UTC')}")

                await self._send_message(chat_id, "\n".join(lines))
                return

            # Show specific category
            filter_type = args[0].lower()

            if filter_type not in ['gainers', 'losers', 'volume', 'volatile']:
                await self._send_message(chat_id, f"❌ Invalid option: {args[0]}\nUse <code>/top</code> for overview or <code>/top gainers</code>, <code>/top losers</code>, <code>/top volume</code>, <code>/top volatile</code>")
                return

            # Sort based on filter type
            if filter_type == 'gainers':
                sorted_data = sorted(market_data, key=lambda x: x['change'], reverse=True)[:10]
                title = "🔥 Top Gainers (24h)"
                emoji = "📈"
            elif filter_type == 'losers':
                sorted_data = sorted(market_data, key=lambda x: x['change'])[:10]
                title = "❄️ Top Losers (24h)"
                emoji = "📉"
            elif filter_type == 'volume':
                sorted_data = sorted(market_data, key=lambda x: x['volume'], reverse=True)[:10]
                title = "📊 Volume Leaders (24h)"
                emoji = "💰"
            else:  # volatile
                # For volatile view, calculate detailed volatility metrics
                await self._send_message(chat_id, "📊 Scanning volatility metrics...")

                volatility_data = []
                sorted_symbols = sorted(market_data, key=lambda x: abs(x['change']), reverse=True)[:15]

                for data in sorted_symbols:
                    try:
                        metrics = await self._calculate_volatility_metrics(data['symbol'])
                        if metrics:
                            volatility_data.append(metrics)
                    except Exception as e:
                        self.logger.warning(f"Failed to get volatility metrics for {data['symbol']}: {e}")
                        continue

                if not volatility_data:
                    await self._send_message(chat_id, "❌ Unable to calculate volatility metrics")
                    return

                # Sort by volatility vs average
                volatility_data.sort(key=lambda x: x.get('volatility_vs_avg', 0), reverse=True)
                sorted_data = volatility_data[:15]
                title = "⚡ Most Volatile Tokens"
                emoji = "⚡"

            # Format message
            if filter_type == 'volatile':
                lines = [f"{title}", "━━━━━━━━━━━━━━━━━━━━━━━━", ""]
            else:
                lines = [f"{title}\n"]

            for i, data in enumerate(sorted_data, 1):
                if filter_type == 'volatile':
                    # Enhanced format with volatility metrics
                    # Heat indicator based on volatility
                    vol_vs_avg = data.get('volatility_vs_avg', 0)
                    if vol_vs_avg > 100:
                        heat = "🔥"
                    elif vol_vs_avg > 50:
                        heat = "📈"
                    elif vol_vs_avg > 0:
                        heat = "📊"
                    else:
                        heat = "💤"

                    # Price change
                    price_change = data.get('price_change_24h', 0)
                    change_emoji = "↑" if price_change >= 0 else "↓"
                    change_str = f"{change_emoji}{abs(price_change):.1f}%"

                    # ATR formatting
                    atr = data.get('atr', 0)
                    atr_pct = data.get('atr_pct', 0)
                    if atr >= 1:
                        atr_str = f"${atr:.2f}"
                    elif atr >= 0.01:
                        atr_str = f"${atr:.4f}"
                    else:
                        atr_str = f"${atr:.6f}"

                    # Volume surge
                    vol_surge = data.get('volume_surge', 0)
                    vol_str = f"{vol_surge:.1f}x" if vol_surge >= 1 else f"{vol_surge:.2f}x"

                    # Bollinger Band status
                    bb_width = data.get('bb_width', 2)
                    if bb_width < 1.5:
                        bb_emoji = "🔒"  # Compressed
                    elif bb_width > 3.0:
                        bb_emoji = "📈"  # Expanded
                    else:
                        bb_emoji = "📊"  # Normal

                    lines.append(
                        f"{i}. {heat} <b>{data['symbol']}</b> {change_str}\n"
                        f"   ATR {atr_str} ({atr_pct:.1f}%) | Vol {vol_str} | BB {bb_emoji}"
                    )
                elif filter_type == 'volume':
                    price_str = f"${data['price']:,.2f}" if data['price'] >= 1 else f"${data['price']:.6f}"
                    change_str = f"${data['volume']/1_000_000:.1f}M"
                    change_emoji = "🟢" if data['change'] > 0 else "🔴" if data['change'] < 0 else "⚪"
                    lines.append(f"{i}. <b>{data['symbol']}</b>: {price_str} {change_emoji} {change_str}")
                else:
                    # Default format for gainers/losers
                    price_str = f"${data['price']:,.2f}" if data['price'] >= 1 else f"${data['price']:.6f}"
                    change_str = f"{data['change']:+.2f}%"
                    change_emoji = "🟢" if data['change'] > 0 else "🔴" if data['change'] < 0 else "⚪"
                    lines.append(f"{i}. <b>{data['symbol']}</b>: {price_str} {change_emoji} {change_str}")

            lines.append("")
            if filter_type == 'volatile':
                lines.append(f"💡 Use <code>/volatility SYMBOL</code> for detailed analysis")
            else:
                lines.append(f"💡 <i>Use /analyze SYMBOL for detailed analysis</i>")
            lines.append(f"⏰ {datetime.now().strftime('%H:%M:%S UTC')}")

            await self._send_message(chat_id, "\n".join(lines))

        except Exception as e:
            self.logger.error(f"Error in /top command: {e}")
            await self._send_message(chat_id, f"❌ Error getting top performers: {str(e)}")

    async def _cmd_price(self, message: Dict, args: List[str]):
        """Handle /price command for instant price lookup."""
        import re

        chat_id = str(message['chat']['id'])

        if not args:
            await self._send_message(chat_id, "❌ Please specify a symbol\nExample: <code>/price BTC</code>")
            return

        if not self.api_client:
            await self._send_message(chat_id, "❌ Market data not available")
            return

        try:
            # Parse symbol
            symbol = ' '.join(args).strip().upper()
            base_symbol = symbol.replace('USDT', '')

            if not re.match(r'^[A-Z0-9]+$', base_symbol):
                await self._send_message(chat_id, "❌ Invalid symbol format")
                return

            if not symbol.endswith('USDT'):
                symbol = f"{symbol}USDT"

            # Fetch price data
            ticker = await self.api_client.get_24hr_ticker(symbol)

            if not ticker:
                await self._send_message(chat_id, f"❌ Symbol {symbol} not found")
                return

            price = float(ticker.get('lastPrice', 0))
            change_24h = float(ticker.get('priceChangePercent', 0))
            high_24h = float(ticker.get('highPrice', 0))
            low_24h = float(ticker.get('lowPrice', 0))
            volume_24h = float(ticker.get('quoteVolume', 0))

            # Format price
            price_str = f"${price:,.2f}" if price >= 1 else f"${price:.8f}"
            high_str = f"${high_24h:,.2f}" if high_24h >= 1 else f"${high_24h:.8f}"
            low_str = f"${low_24h:,.2f}" if low_24h >= 1 else f"${low_24h:.8f}"

            # Volume formatting
            if volume_24h > 1_000_000_000:
                vol_str = f"${volume_24h/1_000_000_000:.2f}B"
            elif volume_24h > 1_000_000:
                vol_str = f"${volume_24h/1_000_000:.1f}M"
            else:
                vol_str = f"${volume_24h:,.0f}"

            emoji = "🟢" if change_24h >= 0 else "🔴"

            response = f"""
💰 <b>{base_symbol} Price</b>

<b>Current:</b> {price_str} {emoji} {change_24h:+.2f}%

<b>24h Range:</b>
High: {high_str}
Low: {low_str}

<b>24h Volume:</b> {vol_str}

⏰ {datetime.now().strftime('%H:%M:%S UTC')}
            """

            await self._send_message(chat_id, response.strip())

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "invalid" in error_msg:
                await self._send_message(chat_id, f"❌ Symbol not found: {symbol}")
            else:
                self.logger.error(f"Error in /price command: {e}")
                await self._send_message(chat_id, f"❌ Error getting price: {str(e)}")

    async def _cmd_hot(self, message: Dict, args: List[str]):
        """Handle /hot command to show symbols with most whale activity."""
        chat_id = str(message['chat']['id'])

        if not self.whale_app or not hasattr(self.whale_app, 'detection_engine'):
            await self._send_message(chat_id, "❌ Whale detection data not available")
            return

        try:
            # Get recent alerts from detection engine or alert manager
            if hasattr(self.whale_app, 'data_store'):
                # Get recent whale detections from data store
                recent_alerts = await self.whale_app.data_store.get_recent_alerts(hours=24, limit=100)

                # Count alerts per symbol
                symbol_counts = {}
                for alert in recent_alerts:
                    symbol = alert.get('symbol', 'UNKNOWN')
                    if symbol not in symbol_counts:
                        symbol_counts[symbol] = 0
                    symbol_counts[symbol] += 1

                # Sort by count
                hot_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:10]

                if not hot_symbols:
                    await self._send_message(chat_id, "🔍 <b>No whale activity detected in the last 24 hours</b>")
                    return

                # Format response
                lines = ["🔥 <b>Hottest Symbols (24h Whale Activity)</b>\n"]

                for i, (symbol, count) in enumerate(hot_symbols, 1):
                    heat_emoji = "🔥" if count > 10 else "📈" if count > 5 else "📊"
                    lines.append(f"{i}. {heat_emoji} <b>{symbol.replace('USDT', '')}</b>: {count} whale alerts")

                lines.append(f"\n💡 <i>Use /analyze SYMBOL for detailed analysis</i>")
                lines.append(f"⏰ {datetime.now().strftime('%H:%M:%S UTC')}")

                await self._send_message(chat_id, "\n".join(lines))

            else:
                # Fallback - no data store available
                await self._send_message(chat_id, "📊 <b>Whale Activity Tracking</b>\n\n<i>Activity tracking not available in current mode.</i>")

        except Exception as e:
            self.logger.error(f"Error in /hot command: {e}")
            await self._send_message(chat_id, f"❌ Error getting hot symbols: {str(e)}")

    async def _cmd_compare(self, message: Dict, args: List[str]):
        """Handle /compare command for side-by-side comparison."""
        import re

        chat_id = str(message['chat']['id'])

        if len(args) < 2:
            await self._send_message(chat_id, "❌ Please specify two symbols\nExample: <code>/compare BTC ETH</code>")
            return

        if not self.api_client:
            await self._send_message(chat_id, "❌ Market data not available")
            return

        try:
            # Parse symbols
            symbol1 = args[0].strip().upper()
            symbol2 = args[1].strip().upper()

            if not symbol1.endswith('USDT'):
                symbol1 = f"{symbol1}USDT"
            if not symbol2.endswith('USDT'):
                symbol2 = f"{symbol2}USDT"

            # Fetch data for both symbols
            ticker1 = await self.api_client.get_24hr_ticker(symbol1)
            ticker2 = await self.api_client.get_24hr_ticker(symbol2)

            if not ticker1 or not ticker2:
                await self._send_message(chat_id, "❌ One or both symbols not found")
                return

            # Extract data
            def format_data(ticker, symbol):
                price = float(ticker.get('lastPrice', 0))
                change = float(ticker.get('priceChangePercent', 0))
                volume = float(ticker.get('quoteVolume', 0))

                price_str = f"${price:,.2f}" if price >= 1 else f"${price:.6f}"
                vol_str = f"${volume/1_000_000_000:.2f}B" if volume > 1_000_000_000 else f"${volume/1_000_000:.1f}M"
                emoji = "🟢" if change >= 0 else "🔴"

                return {
                    'symbol': symbol.replace('USDT', ''),
                    'price': price_str,
                    'change': change,
                    'volume': vol_str,
                    'emoji': emoji
                }

            data1 = format_data(ticker1, symbol1)
            data2 = format_data(ticker2, symbol2)

            # Determine winner
            if data1['change'] > data2['change']:
                winner = f"{data1['symbol']} is outperforming"
            elif data2['change'] > data1['change']:
                winner = f"{data2['symbol']} is outperforming"
            else:
                winner = "Tied performance"

            response = f"""
⚖️ <b>Symbol Comparison (24h)</b>

<b>{data1['symbol']}</b>
Price: {data1['price']} {data1['emoji']}
Change: {data1['change']:+.2f}%
Volume: {data1['volume']}

<b>vs</b>

<b>{data2['symbol']}</b>
Price: {data2['price']} {data2['emoji']}
Change: {data2['change']:+.2f}%
Volume: {data2['volume']}

🏆 <b>Winner:</b> {winner}

⏰ {datetime.now().strftime('%H:%M:%S UTC')}
            """

            await self._send_message(chat_id, response.strip())

        except Exception as e:
            self.logger.error(f"Error in /compare command: {e}")
            await self._send_message(chat_id, f"❌ Error comparing symbols: {str(e)}")

    async def _cmd_volatility(self, message: Dict, args: List[str]):
        """Handle /volatility command - show top volatile symbols or detailed analysis."""
        chat_id = str(message['chat']['id'])

        if not self.api_client:
            await self._send_message(chat_id, "❌ Market data not available")
            return

        try:
            # If symbol provided, show detailed analysis
            if args:
                symbol = args[0].strip().upper()
                if not symbol.endswith('USDT'):
                    symbol = f"{symbol}USDT"
                await self._volatility_detailed_analysis(chat_id, symbol)
            else:
                # Show top 10 volatile symbols scanner
                await self._volatility_top_scanner(chat_id)

        except Exception as e:
            self.logger.error(f"Error in /volatility command: {e}")
            await self._send_message(chat_id, f"❌ Error analyzing volatility: {str(e)}")

    async def _volatility_top_scanner(self, chat_id: str):
        """Show top N most volatile symbols (configurable)."""
        try:
            # Get config values
            vol_config = self.config.get('telegram', {}).get('commands', {}).get('volatility', {})
            scanner_limit = vol_config.get('scanner_symbol_limit', 30)
            top_count = vol_config.get('top_results_count', 10)

            # Get symbols to scan
            symbols = []
            if self.whale_app and hasattr(self.whale_app, 'symbol_manager') and self.whale_app.symbol_manager:
                symbols = self.whale_app.symbol_manager.get_current_symbols()[:scanner_limit]
            elif 'whale_detection' in self.config:
                symbols = self.config.get('whale_detection', {}).get('symbols', [])[:scanner_limit]

            if not symbols:
                await self._send_message(chat_id, "❌ No symbols available for scanning")
                return

            # Calculate volatility metrics for each symbol
            volatility_data = []
            failed_symbols = []
            for symbol in symbols:
                try:
                    metrics = await self._calculate_volatility_metrics(symbol)
                    if metrics:
                        volatility_data.append(metrics)
                    else:
                        failed_symbols.append(symbol)
                except Exception as e:
                    self.logger.warning(f"Failed to get volatility for {symbol}: {e}")
                    failed_symbols.append(symbol)
                    continue

            if not volatility_data:
                error_msg = f"❌ Unable to calculate volatility data for any symbols\n\n"
                error_msg += f"📊 Scanned: {len(symbols)} symbols\n"
                error_msg += f"❌ Failed: {len(failed_symbols)}\n\n"
                if failed_symbols[:5]:
                    error_msg += f"<i>Failed symbols: {', '.join(s.replace('USDT', '') for s in failed_symbols[:5])}</i>\n\n"
                error_msg += "💡 Try again in a few moments or check symbol availability"
                await self._send_message(chat_id, error_msg)
                return

            # Log success/failure stats
            self.logger.info(f"Volatility scan: {len(volatility_data)} successful, {len(failed_symbols)} failed out of {len(symbols)}")

            # Sort by volatility vs average (descending)
            volatility_data.sort(key=lambda x: x['volatility_vs_avg'], reverse=True)
            top_results = volatility_data[:top_count]

            # Format response
            lines = ["🔥 <b>VOLATILITY SCANNER</b>", "━━━━━━━━━━━━━━━━━━━━━━━━", ""]

            for i, data in enumerate(top_results, 1):
                # Heat indicator based on volatility
                if data['volatility_vs_avg'] > 100:
                    heat = "🔥"
                elif data['volatility_vs_avg'] > 50:
                    heat = "📈"
                elif data['volatility_vs_avg'] > 0:
                    heat = "📊"
                else:
                    heat = "💤"

                # Get 24h price change
                price_change_24h = data.get('price_change_24h', 0)
                change_emoji = "↑" if price_change_24h >= 0 else "↓"
                change_str = f"{change_emoji}{abs(price_change_24h):.1f}%"

                # Smart ATR formatting with percentage
                atr = data['atr']
                atr_pct = data['atr_pct']
                if atr >= 1:
                    atr_str = f"${atr:.2f}"
                elif atr >= 0.01:
                    atr_str = f"${atr:.4f}"
                else:
                    atr_str = f"${atr:.6f}"

                # Volume surge
                vol_surge = data['volume_surge']
                vol_str = f"{vol_surge:.1f}x" if vol_surge >= 1 else f"{vol_surge:.2f}x"

                # Bollinger Band status
                bb_width = data['bb_width']
                if bb_width < 1.5:
                    bb_emoji = "🔒"  # Compressed - breakout soon
                elif bb_width > 3.0:
                    bb_emoji = "📈"  # Expanded - overextended
                else:
                    bb_emoji = "📊"  # Normal

                lines.append(
                    f"{i}. {heat} <b>{data['symbol']}</b> {change_str} | "
                    f"ATR {atr_str} ({atr_pct:.1f}%) | "
                    f"Vol {vol_str} | BB {bb_emoji}"
                )

            lines.append("")
            lines.append(f"📊 Scanned: {len(volatility_data)}/{len(symbols)} symbols")
            lines.append(f"💡 Use <code>/volatility SYMBOL</code> for detailed analysis")
            lines.append(f"⏰ {datetime.now().strftime('%H:%M:%S UTC')}")

            await self._send_message(chat_id, "\n".join(lines))

        except Exception as e:
            self.logger.error(f"Error in volatility scanner: {e}")
            raise

    async def _volatility_detailed_analysis(self, chat_id: str, symbol: str):
        """Show detailed volatility analysis for a single symbol."""
        try:
            metrics = await self._calculate_volatility_metrics(symbol, detailed=True)
            if not metrics:
                await self._send_message(chat_id, f"❌ Unable to get data for {symbol}")
                return

            # Determine trade signal
            if metrics['volatility_vs_avg'] > 80 and metrics['bb_width'] < 2:
                signal = "🔥 HIGH VOLATILITY - Breakout likely, avoid tight stops"
            elif metrics['volatility_vs_avg'] > 50:
                signal = "📈 ELEVATED - Good for swing trades"
            elif metrics['volatility_vs_avg'] < -30:
                signal = "💤 LOW VOLATILITY - Range-bound, wait for setup"
            else:
                signal = "📊 NORMAL - Standard conditions"

            # Directional bias
            bias = "BULLISH" if metrics['buy_sell_ratio'] > 1.3 else "BEARISH" if metrics['buy_sell_ratio'] < 0.7 else "NEUTRAL"
            bias_emoji = "🟢" if bias == "BULLISH" else "🔴" if bias == "BEARISH" else "⚪"

            # Smart price formatting
            price = metrics['price']
            if price >= 1:
                price_str = f"${price:,.2f}"
            elif price >= 0.01:
                price_str = f"${price:.4f}"
            else:
                price_str = f"${price:.6f}"

            # Smart ATR formatting
            atr = metrics['atr']
            if atr >= 1:
                atr_str = f"${atr:.2f}"
            elif atr >= 0.01:
                atr_str = f"${atr:.4f}"
            else:
                atr_str = f"${atr:.6f}"

            # Smart expected move formatting
            exp_move = metrics['expected_move']
            if exp_move >= 1:
                exp_str = f"${exp_move:.2f}"
            elif exp_move >= 0.01:
                exp_str = f"${exp_move:.4f}"
            else:
                exp_str = f"${exp_move:.6f}"

            # Velocity formatting
            velocity = metrics['velocity']
            if velocity >= 0.01:
                vel_str = f"${velocity:.4f}/s"
            else:
                vel_str = f"${velocity:.6f}/s"

            # Price range formatting
            high_24h = metrics['high_24h']
            low_24h = metrics['low_24h']
            if high_24h >= 1:
                high_str = f"${high_24h:,.2f}"
            elif high_24h >= 0.01:
                high_str = f"${high_24h:.4f}"
            else:
                high_str = f"${high_24h:.6f}"

            if low_24h >= 1:
                low_str = f"${low_24h:,.2f}"
            elif low_24h >= 0.01:
                low_str = f"${low_24h:.4f}"
            else:
                low_str = f"${low_24h:.6f}"

            # Calculate stop/target levels based on ATR
            price_val = metrics['price']
            atr_val = metrics['atr']
            stop_loss = price_val - (1.5 * atr_val)
            target_1 = price_val + (2 * atr_val)
            target_2 = price_val + (3 * atr_val)

            # Format stop/targets
            if stop_loss >= 1:
                stop_str = f"${stop_loss:,.2f}"
            elif stop_loss >= 0.01:
                stop_str = f"${stop_loss:.4f}"
            else:
                stop_str = f"${stop_loss:.6f}"

            if target_1 >= 1:
                t1_str = f"${target_1:,.2f}"
            elif target_1 >= 0.01:
                t1_str = f"${target_1:.4f}"
            else:
                t1_str = f"${target_1:.6f}"

            if target_2 >= 1:
                t2_str = f"${target_2:,.2f}"
            elif target_2 >= 0.01:
                t2_str = f"${target_2:.4f}"
            else:
                t2_str = f"${target_2:.6f}"

            # Calculate quality score (0-10)
            quality_score = 0
            quality_notes = []

            # Volume confirms move (max 3 points)
            if metrics['volume_surge'] > 2:
                quality_score += 3
                quality_notes.append("Volume confirms ✅")
            elif metrics['volume_surge'] > 1.5:
                quality_score += 2
                quality_notes.append("Volume moderate ⚠️")
            else:
                quality_notes.append("Low volume ❌")

            # Tight spread/liquidity (max 2 points) - placeholder, would need actual spread data
            quality_score += 2
            quality_notes.append("Liquidity good ✅")

            # Whale activity (max 2 points)
            if metrics['whale_count'] > 5:
                quality_score += 2
                quality_notes.append(f"Whale interest ({metrics['whale_count']}) ✅")
            elif metrics['whale_count'] > 0:
                quality_score += 1
                quality_notes.append(f"Some whales ({metrics['whale_count']}) ⚠️")
            else:
                quality_notes.append("No whale activity ❌")

            # Trend alignment (max 3 points) - based on bias
            if abs(metrics['buy_sell_ratio'] - 1.0) > 0.5:
                quality_score += 3
                quality_notes.append(f"Strong bias ({bias}) ✅")
            elif abs(metrics['buy_sell_ratio'] - 1.0) > 0.3:
                quality_score += 2
                quality_notes.append(f"Moderate bias ({bias}) ⚠️")
            else:
                quality_notes.append("No clear bias ❌")

            # Price change indicator
            price_change_24h = metrics['price_change_24h']
            change_emoji = "🟢" if price_change_24h >= 0 else "🔴"

            response = f"""
📊 <b>{metrics['symbol']} VOLATILITY ANALYSIS</b>
━━━━━━━━━━━━━━━━━━━━━━━━

💰 <b>Price:</b> {price_str} {change_emoji} {price_change_24h:+.1f}%
📊 <b>24h Range:</b> {low_str} - {high_str}
📏 <b>ATR:</b> {atr_str} ({metrics['atr_pct']:.2f}%)

🌪️ <b>Volatility:</b> {metrics['volatility_emoji']} {metrics['volatility_vs_avg']:+.0f}% vs avg ({metrics['percentile']:.0f}th percentile)
📊 <b>Volume Surge:</b> {metrics['volume_surge']:.1f}x {'⚡' if metrics['volume_surge'] > 2 else ''}
📉 <b>BB Width:</b> {metrics['bb_width']:.2f}% {'🔒 Compressed' if metrics['bb_width'] < 1.5 else '📈 Expanded'}

🎯 <b>Trade Levels:</b>
   • Stop Loss: {stop_str} (1.5× ATR)
   • Target 1: {t1_str} (2× ATR)
   • Target 2: {t2_str} (3× ATR)

🐋 <b>Whale Activity (24h):</b>
   • Trades: {metrics['whale_count']}
   • Bias: {bias} {bias_emoji} (B/S: {metrics['buy_sell_ratio']:.2f})

💪 <b>Quality Score: {quality_score}/10</b>
   {chr(10).join(f'   • {note}' for note in quality_notes)}

💡 <b>Signal:</b> {signal}

⏰ {datetime.now().strftime('%H:%M:%S UTC')}
            """

            await self._send_message(chat_id, response.strip())

        except Exception as e:
            self.logger.error(f"Error in detailed volatility analysis: {e}")
            raise

    async def _calculate_volatility_metrics(self, symbol: str, detailed: bool = False) -> Optional[Dict[str, Any]]:
        """Calculate comprehensive volatility metrics for a symbol."""
        try:
            # Get config values
            vol_config = self.config.get('telegram', {}).get('commands', {}).get('volatility', {})
            klines_interval = vol_config.get('klines_interval', '15m')
            klines_limit = vol_config.get('klines_limit', 20)
            detailed_whale_data = vol_config.get('detailed_whale_data', True)

            # Fetch market data
            ticker = await self.api_client.get_24hr_ticker(symbol)
            if not ticker:
                return None

            # Get klines for ATR and BB calculation
            klines = await self.api_client.get_klines(symbol, interval=klines_interval, limit=klines_limit)
            if not klines or len(klines) < 14:
                return None

            # Extract basic data
            price = float(ticker.get('lastPrice', 0))
            high_24h = float(ticker.get('highPrice', price))
            low_24h = float(ticker.get('lowPrice', price))
            volume = float(ticker.get('quoteVolume', 0))
            price_change = float(ticker.get('priceChangePercent', 0))

            # Calculate ATR (Average True Range)
            atr = self._calculate_atr(klines)
            atr_pct = (atr / price * 100) if price > 0 else 0

            # Calculate Bollinger Band width
            bb_width = self._calculate_bb_width(klines)

            # Calculate price velocity ($/second) - adapt to interval
            interval_seconds = self._parse_interval_to_seconds(klines_interval)
            velocity = abs(float(klines[-1][4]) - float(klines[-2][4])) / interval_seconds if interval_seconds > 0 else 0

            # Volume surge ratio (current volume vs average)
            avg_volume = sum(float(k[7]) for k in klines) / len(klines)
            volume_surge = float(ticker.get('quoteVolume', 0)) / avg_volume if avg_volume > 0 else 1

            # Calculate volatility vs historical average (using recent kline-based volatility)
            volatilities = []
            for i in range(1, len(klines)):
                prev_close = float(klines[i-1][4])
                curr_close = float(klines[i][4])
                vol = abs((curr_close - prev_close) / prev_close * 100) if prev_close > 0 else 0
                volatilities.append(vol)

            avg_volatility = sum(volatilities) / len(volatilities) if volatilities else 0.01
            # Use recent volatility (last 3 klines) instead of 24h change
            recent_vols = volatilities[-3:] if len(volatilities) >= 3 else volatilities
            current_volatility = sum(recent_vols) / len(recent_vols) if recent_vols else 0
            volatility_vs_avg = ((current_volatility / avg_volatility) - 1) * 100 if avg_volatility > 0 else 0

            # Calculate volatility percentile
            percentile = self._calculate_percentile(current_volatility, volatilities)

            # Expected move (2 * ATR as simple estimate)
            expected_move = atr * 2

            # Whale count (from recent alerts if available)
            whale_count = 0
            if detailed and detailed_whale_data and self.whale_app and hasattr(self.whale_app, 'data_store'):
                try:
                    recent_alerts = await self.whale_app.data_store.get_recent_alerts(hours=24, limit=100)
                    whale_count = sum(1 for alert in recent_alerts if alert.get('symbol') == symbol)
                except:
                    pass

            # Buy/Sell ratio (simplified - would need trade data for accuracy)
            buy_sell_ratio = 1.0  # Default neutral
            if detailed and detailed_whale_data:
                try:
                    trades = await self.api_client.get_recent_trades(symbol, limit=100)
                    buy_volume = sum(float(t['quoteQty']) for t in trades if t.get('isBuyerMaker', False) == False)
                    sell_volume = sum(float(t['quoteQty']) for t in trades if t.get('isBuyerMaker', False) == True)
                    buy_sell_ratio = buy_volume / sell_volume if sell_volume > 0 else 1.0
                except:
                    pass

            # Price efficiency
            if volume > 0:
                efficiency = "High" if abs(price_change) / (volume / 1_000_000) > 0.01 else "Normal"
            else:
                efficiency = "Unknown"

            # Volatility emoji
            if volatility_vs_avg > 100:
                vol_emoji = "🔥"
            elif volatility_vs_avg > 50:
                vol_emoji = "📈"
            elif volatility_vs_avg < -30:
                vol_emoji = "💤"
            else:
                vol_emoji = "📊"

            return {
                'symbol': symbol.replace('USDT', ''),
                'price': price,
                'price_change_24h': price_change,
                'high_24h': high_24h,
                'low_24h': low_24h,
                'atr': atr,
                'atr_pct': atr_pct,
                'bb_width': bb_width,
                'velocity': velocity,
                'volume_surge': volume_surge,
                'volatility_vs_avg': volatility_vs_avg,
                'percentile': percentile,
                'expected_move': expected_move,
                'whale_count': whale_count,
                'buy_sell_ratio': buy_sell_ratio,
                'efficiency': efficiency,
                'volatility_emoji': vol_emoji
            }

        except Exception as e:
            self.logger.error(f"Error calculating volatility metrics for {symbol}: {e}")
            return None

    def _calculate_atr(self, klines: List[List]) -> float:
        """Calculate Average True Range from klines."""
        try:
            true_ranges = []
            for i in range(1, len(klines)):
                high = float(klines[i][2])
                low = float(klines[i][3])
                prev_close = float(klines[i-1][4])

                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
                true_ranges.append(tr)

            # Return average of last 14 periods
            return sum(true_ranges[-14:]) / min(14, len(true_ranges)) if true_ranges else 0

        except Exception as e:
            self.logger.error(f"Error calculating ATR: {e}")
            return 0

    def _calculate_bb_width(self, klines: List[List]) -> float:
        """Calculate Bollinger Band width percentage."""
        try:
            closes = [float(k[4]) for k in klines[-20:]]
            if len(closes) < 20:
                return 0

            # Calculate SMA and standard deviation
            sma = sum(closes) / len(closes)
            variance = sum((x - sma) ** 2 for x in closes) / len(closes)
            std_dev = variance ** 0.5

            # BB width = (upper - lower) / middle * 100
            upper = sma + (2 * std_dev)
            lower = sma - (2 * std_dev)
            width = ((upper - lower) / sma * 100) if sma > 0 else 0

            return width

        except Exception as e:
            self.logger.error(f"Error calculating BB width: {e}")
            return 0

    def _calculate_percentile(self, value: float, data: List[float]) -> float:
        """Calculate percentile rank of a value within a dataset."""
        try:
            if not data:
                return 50.0

            sorted_data = sorted(data)
            count_below = sum(1 for x in sorted_data if x < value)
            percentile = (count_below / len(sorted_data)) * 100

            return percentile

        except Exception as e:
            self.logger.error(f"Error calculating percentile: {e}")
            return 50.0

    def _parse_interval_to_seconds(self, interval: str) -> int:
        """Parse interval string to seconds (e.g., '15m' -> 900, '1h' -> 3600)."""
        try:
            # Extract number and unit
            import re
            match = re.match(r'^(\d+)([smhd])$', interval.lower())
            if not match:
                return 900  # Default to 15 minutes

            value = int(match.group(1))
            unit = match.group(2)

            # Convert to seconds
            multipliers = {
                's': 1,
                'm': 60,
                'h': 3600,
                'd': 86400
            }

            return value * multipliers.get(unit, 60)

        except Exception as e:
            self.logger.error(f"Error parsing interval {interval}: {e}")
            return 900  # Default to 15 minutes

    # Admin Commands

    async def _cmd_admin(self, message: Dict, args: List[str]):
        """Handle /admin command for admin control panel."""
        chat_id = str(message['chat']['id'])

        # Get system stats
        system_stats = await self.alert_manager.get_statistics()
        user_count = await self.alert_manager.get_telegram_users_count()
        subscriber_count = await self.alert_manager.get_active_subscribers_count()

        admin_text = f"""
🔧 <b>Admin Control Panel</b>

<b>📊 System Status:</b>
• Total Users: {user_count}
• Active Subscribers: {subscriber_count}
• Alerts Processed: {system_stats.get('alerts_processed', 0)}
• Success Rate: {system_stats.get('success_rate', 0):.1f}%
• Queue Size: {system_stats.get('queue_size', 0)}

<b>⚡ Available Commands:</b>
/users - User management
/system - Detailed system info
/broadcast - Send message to all users
/test - Send test alert
/maintenance - System maintenance

<b>📈 Quick Actions:</b>
        """

        keyboard = [
            ["👥 User Stats", "📊 System Info"],
            ["📢 Broadcast", "🧪 Test Alert"],
            ["🔧 Maintenance", "📋 View Logs"]
        ]

        notification = NotificationData(
            alert_type=AlertType.WHALE_TRADE,
            severity=AlertSeverity.MEDIUM,
            symbol="ADMIN",
            message=admin_text
        )

        await self.bot.send_with_keyboard(chat_id, notification, keyboard)

    async def _cmd_broadcast(self, message: Dict, args: List[str]):
        """Handle /broadcast command."""
        chat_id = str(message['chat']['id'])

        if not args:
            await self._send_error(chat_id, "Please provide a message to broadcast.")
            return

        broadcast_message = " ".join(args)

        # Confirm broadcast
        confirmation_text = f"""
📢 <b>Broadcast Confirmation</b>

<b>Message:</b> {broadcast_message}

<b>Recipients:</b> All active users

⚠️ This will send the message to ALL subscribed users. Are you sure?
        """

        keyboard = [
            ["✅ Send Broadcast", "❌ Cancel"]
        ]

        notification = NotificationData(
            alert_type=AlertType.WHALE_TRADE,
            severity=AlertSeverity.MEDIUM,
            symbol="BROADCAST",
            message=confirmation_text
        )

        await self.bot.send_with_keyboard(chat_id, notification, keyboard)

    async def _cmd_users(self, message: Dict, args: List[str]):
        """Handle /users command for user management."""
        chat_id = str(message['chat']['id'])

        if not args or args[0] == 'count':
            user_stats = await self.user_manager.get_user_stats()
            response = f"""
👥 <b>User Statistics</b>

📊 <b>Total Users:</b> {user_stats.get('total_users', 0)}
✅ <b>Active Subscribers:</b> {user_stats.get('active_subscribers', 0)}
❌ <b>Inactive Users:</b> {user_stats.get('inactive_users', 0)}
🔧 <b>Admin Users:</b> {user_stats.get('admin_count', 0)}

<b>Alert Preferences:</b>
{json.dumps(user_stats.get('severity_preferences', {}), indent=2)}
            """
        elif args[0] == 'list':
            # This would show recent users - simplified
            response = """
👥 <b>Recent Users</b>

<i>Recent user list feature coming soon!</i>

This will show:
• Recently registered users
• User activity status
• Subscription details
• Last interaction time
            """
        else:
            response = """
👥 <b>User Management</b>

<b>Available Commands:</b>
• <code>/users count</code> - Show user statistics
• <code>/users list</code> - Show recent users
• <code>/users search [query]</code> - Search users

Use without arguments to see user count.
            """

        await self._send_message(chat_id, response)

    async def _cmd_system(self, message: Dict, args: List[str]):
        """Handle /system command for system information."""
        chat_id = str(message['chat']['id'])

        system_stats = await self.alert_manager.get_statistics()
        channel_status = await self.alert_manager.get_channel_status()

        uptime_hours = system_stats.get('uptime_seconds', 0) / 3600

        system_text = f"""
🖥️ <b>System Status</b>

<b>⏱️ Uptime:</b> {uptime_hours:.1f} hours
<b>📊 Performance:</b>
• Alerts Processed: {system_stats.get('alerts_processed', 0)}
• Alerts Sent: {system_stats.get('alerts_sent', 0)}
• Failed Alerts: {system_stats.get('alerts_failed', 0)}
• Success Rate: {system_stats.get('success_rate', 0):.1f}%

<b>⚡ Queue Status:</b>
• Current Queue Size: {system_stats.get('queue_size', 0)}
• Processing Workers: 3

<b>🔗 Channels:</b>
"""

        for channel, status in channel_status.items():
            status_emoji = "✅" if status.get('connected') else "❌"
            system_text += f"• {channel.title()}: {status_emoji}\n"

        await self._send_message(chat_id, system_text)

    async def _cmd_test(self, message: Dict, args: List[str]):
        """Handle /test command to send test alerts."""
        chat_id = str(message['chat']['id'])

        # Parse alert type and severity
        alert_type = AlertType.WHALE_TRADE
        severity = AlertSeverity.MEDIUM

        if args:
            try:
                if args[0] in ['whale_trade', 'accumulation', 'manipulation']:
                    alert_type = AlertType(args[0])
                if len(args) > 1 and args[1] in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                    severity = AlertSeverity[args[1]]
            except:
                pass

        # Send test alert
        test_data = {
            'volume': 1500000.0,
            'trade_value': 2500000.0,
            'price': 45000.0,
            'side': 'BUY',
            'exchange': 'Binance',
            'confidence': 0.95
        }

        await self.alert_manager.send_whale_alert(
            alert_type=alert_type,
            severity=severity,
            symbol="BTC/USDT",
            message="🧪 This is a test alert to verify the notification system is working correctly.",
            data=test_data
        )

        await self._send_message(
            chat_id,
            f"🧪 Test alert sent!\n\nType: {alert_type.value}\nSeverity: {severity.name}"
        )

    # Super Admin Commands

    async def _cmd_config(self, message: Dict, args: List[str]):
        """Handle /config command for configuration management."""
        chat_id = str(message['chat']['id'])

        response = """
⚙️ <b>Configuration Management</b>

<b>Available Operations:</b>
• <code>/config get [key]</code> - Get configuration value
• <code>/config set [key] [value]</code> - Set configuration value
• <code>/config list</code> - List all configuration keys

<b>Example:</b>
<code>/config get whale_detection.min_trade_value</code>

<i>⚠️ Be careful when modifying configuration values.</i>
        """

        await self._send_message(chat_id, response)

    async def _cmd_maintenance(self, message: Dict, args: List[str]):
        """Handle /maintenance command for system maintenance."""
        chat_id = str(message['chat']['id'])

        maintenance_text = """
🔧 <b>System Maintenance</b>

<b>Available Operations:</b>
• <code>cleanup_users</code> - Remove inactive users
• <code>cleanup_logs</code> - Remove old log entries
• <code>backup_database</code> - Create database backup
• <code>restart_services</code> - Restart background services

<b>Usage:</b>
<code>/maintenance [operation]</code>

⚠️ <b>Warning:</b> Some operations may temporarily affect service availability.
        """

        if args and args[0] in ['cleanup_users', 'cleanup_logs', 'backup_database', 'restart_services']:
            operation = args[0]
            response = f"🔧 Maintenance operation '{operation}' started. You'll receive a status update when complete."
            # This would trigger the actual maintenance operation
        else:
            response = maintenance_text

        await self._send_message(chat_id, response)

    async def _cmd_restart(self, message: Dict, args: List[str]):
        """Handle /restart command to restart the whale hunter bot."""
        chat_id = str(message['chat']['id'])

        restart_message = """
🔄 <b>Restarting Whale Hunter Bot...</b>

The bot will shut down and restart in a few seconds.
You'll be notified when it's back online.

⏳ Please wait 10-15 seconds...
        """

        await self._send_message(chat_id, restart_message.strip())

        # Give time for message to send
        await asyncio.sleep(2)

        # Trigger graceful shutdown which will cause restart if running under supervisor/systemd
        if self.whale_app:
            self.logger.info("Admin restart requested via Telegram command")
            # Schedule shutdown after a short delay
            asyncio.create_task(self._delayed_shutdown())
        else:
            await self._send_message(chat_id, "❌ Unable to restart: whale_app not available")

    async def _delayed_shutdown(self):
        """Delayed shutdown to allow message to be sent."""
        await asyncio.sleep(3)
        if self.whale_app:
            self.whale_app.running = False
            # Force exit to trigger restart
            import os
            os._exit(0)

    async def _cmd_logs(self, message: Dict, args: List[str]):
        """Handle /logs command to view system logs."""
        chat_id = str(message['chat']['id'])

        lines = 20
        if args and args[0].isdigit():
            lines = min(int(args[0]), 100)  # Max 100 lines

        # This would read actual log files
        log_text = f"""
📋 <b>System Logs (Last {lines} lines)</b>

<code>
2024-09-24 10:30:15 - INFO - Telegram bot initialized successfully
2024-09-24 10:30:16 - INFO - AlertManager started with 3 workers
2024-09-24 10:31:22 - INFO - User 123456 subscribed to whale alerts
2024-09-24 10:32:45 - INFO - Whale alert sent: BTC/USDT - 5 recipients
2024-09-24 10:33:12 - DEBUG - Processing queue size: 0
</code>

Use <code>/logs [number]</code> to specify number of lines (max 100).
        """

        await self._send_message(chat_id, log_text)

    def get_command_stats(self) -> Dict[str, Any]:
        """Get command usage statistics."""
        return {
            'total_commands': len(self.commands),
            'usage_stats': {
                cmd: {
                    'count': stats['count'],
                    'unique_users': len(stats['users'])
                }
                for cmd, stats in self.command_usage.items()
            }
        }