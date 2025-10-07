"""
Debug Table Formatter - Provides pretty table formatting for debug logging.
Only shows tables when DEBUG logging is enabled to avoid performance impact.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal
from datetime import datetime
from prettytable import PrettyTable, PLAIN_COLUMNS
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DebugTableFormatter:
    """
    Pretty table formatter for debug logging in whale detection system.
    
    Features:
    - Only formats tables when DEBUG logging is enabled
    - Provides various table formats for different data types
    - Includes timing information and performance metrics
    - Supports both individual symbol analysis and system-wide summaries
    """

    def __init__(self, enable_colors: bool = False):
        """Initialize the debug table formatter.

        Args:
            enable_colors: Enable colored output (may not work in all terminals)
        """
        self.enable_colors = enable_colors
        self.formatting_times = []  # Track formatting performance

    @contextmanager
    def timing_context(self, operation_name: str):
        """Context manager for timing operations."""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration = (end_time - start_time) * 1000  # Convert to milliseconds
            self.formatting_times.append({
                'operation': operation_name,
                'duration_ms': duration,
                'timestamp': time.time()
            })

    def is_debug_enabled(self) -> bool:
        """Check if DEBUG logging is enabled."""
        return logger.isEnabledFor(logging.DEBUG)

    def format_symbol_analysis_table(
        self,
        symbol: str,
        timestamp: float,
        price_data: Dict[str, Any],
        volume_analysis: Dict[str, Any],
        orderbook_analysis: Dict[str, Any],
        momentum_analysis: Dict[str, Any],
        volatility_analysis: Dict[str, Any],
        signal_fusion: Dict[str, Any],
        alerts_generated: List[Any],
        performance_metrics: Dict[str, Any]
    ) -> str:
        """Format comprehensive symbol analysis table.

        Args:
            symbol: Trading symbol
            timestamp: Analysis timestamp
            price_data: Current price and change information
            volume_analysis: Volume analysis results
            orderbook_analysis: Order book imbalance analysis
            momentum_analysis: Price momentum analysis
            volatility_analysis: Volatility metrics
            signal_fusion: Signal fusion results
            alerts_generated: List of alerts generated
            performance_metrics: Timing and performance data

        Returns:
            Formatted table string
        """
        if not self.is_debug_enabled():
            return ""

        with self.timing_context(f"format_symbol_analysis_{symbol}"):
            # Create main analysis table
            table = PrettyTable()
            table.field_names = ["Metric", "Value", "Status", "Details"]
            table.align = "l"

            # Header with timestamp
            time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
            table.title = f"🔍 WHALE ANALYSIS - {symbol} @ {time_str}"

            # Price Information
            price = price_data.get('current_price', 0)
            change_24h = price_data.get('price_change_24h', 0)
            change_color = "🟢" if change_24h > 0 else "🔴" if change_24h < 0 else "⚪"
            
            table.add_row([
                "💰 Price",
                f"${float(price):.6f}",
                f"{change_color} {change_24h:+.2f}%",
                f"24h Vol: ${price_data.get('volume_24h', 0):,.0f}"
            ])

            # Volume Analysis
            vol_ratio = volume_analysis.get('volume_surge', 1)
            vol_status = "🔥 SPIKE" if vol_ratio >= 3 else "📈 HIGH" if vol_ratio >= 2 else "📊 NORMAL"
            
            table.add_row([
                "📊 Volume",
                f"${volume_analysis.get('current_volume', 0):,.0f}",
                f"{vol_status} ({vol_ratio:.1f}x)",
                f"Avg: ${volume_analysis.get('avg_volume', 0):,.0f}, Trades: {volume_analysis.get('significant_trades', 0)}"
            ])

            # Order Book Analysis
            imbalance = orderbook_analysis.get('bid_ask_ratio', 1)
            dominant = orderbook_analysis.get('dominant_side', 'balanced')
            imbalance_status = "⚖️ HEAVY" if imbalance >= 3 or imbalance <= 0.33 else "📊 NORMAL"
            
            table.add_row([
                "⚖️ Order Book",
                f"{imbalance:.2f}",
                f"{imbalance_status} {dominant.upper()}",
                f"Bid: ${orderbook_analysis.get('bid_volume', 0):,.0f}, Ask: ${orderbook_analysis.get('ask_volume', 0):,.0f}"
            ])

            # Momentum Analysis
            momentum_rate = momentum_analysis.get('price_change_rate', 0)
            momentum_dir = momentum_analysis.get('momentum_direction', 'sideways')
            momentum_status = "🚀 STRONG" if abs(momentum_rate) >= 5 else "📈 MODERATE" if abs(momentum_rate) >= 2 else "➡️ WEAK"
            
            table.add_row([
                "🚀 Momentum",
                f"{momentum_rate:+.2f}%/min",
                f"{momentum_status} {momentum_dir.upper()}",
                f"Strength: {momentum_analysis.get('momentum_strength', 0):.2f}, Duration: {momentum_analysis.get('duration_seconds', 0)}s"
            ])

            # Volatility Analysis
            volatility = volatility_analysis.get('current_volatility', 0)
            z_score = volatility_analysis.get('z_score', 0)
            vol_status = "🌋 EXTREME" if abs(z_score) >= 3 else "🔥 HIGH" if abs(z_score) >= 2 else "📊 NORMAL"
            
            table.add_row([
                "🌪️ Volatility",
                f"{volatility:.2f}%",
                f"{vol_status} ({z_score:+.1f}σ)",
                f"Baseline: {volatility_analysis.get('baseline_volatility', 0):.2f}%, Ratio: {volatility_analysis.get('volatility_ratio', 1):.1f}x"
            ])

            # Signal Fusion
            consensus = signal_fusion.get('strategy_consensus', 0)
            contributing = len(signal_fusion.get('contributing_strategies', []))
            fusion_conf = signal_fusion.get('fusion_confidence', 0)
            fusion_status = "🔥 STRONG" if consensus >= 0.75 else "📈 MODERATE" if consensus >= 0.5 else "📊 WEAK"
            
            table.add_row([
                "🧠 Signal Fusion",
                f"{fusion_conf:.3f}",
                f"{fusion_status} ({contributing}/4 strategies)",
                f"Consensus: {consensus:.2f}, Method: {signal_fusion.get('fusion_method', 'none')}"
            ])

            # Alerts Generated
            alert_count = len(alerts_generated)
            if alert_count > 0:
                # Handle both dict and object alert types
                def get_alert_value(alert, key, default=0):
                    if isinstance(alert, dict):
                        return alert.get(key, default)
                    else:
                        return getattr(alert, key, default)

                highest_conf = max((get_alert_value(a, 'confidence', 0) for a in alerts_generated), default=0)
                alert_status = "🚨 CRITICAL" if highest_conf >= 0.85 else "⚠️ HIGH" if highest_conf >= 0.75 else "📢 MEDIUM"
                alert_types = ", ".join(set(str(get_alert_value(a, 'detection_type', 'unknown')) for a in alerts_generated))
                
                table.add_row([
                    "🚨 Alerts",
                    f"{alert_count} alerts",
                    f"{alert_status} (conf: {highest_conf:.3f})",
                    f"Types: {alert_types}"
                ])
            else:
                table.add_row([
                    "🚨 Alerts",
                    "0 alerts",
                    "✅ NONE",
                    "No whale activity detected"
                ])

            # Performance Metrics
            analysis_time = performance_metrics.get('analysis_duration_ms', 0)
            perf_status = "⚡ FAST" if analysis_time < 50 else "📊 NORMAL" if analysis_time < 150 else "🐌 SLOW"
            
            table.add_row([
                "⏱️ Performance",
                f"{analysis_time:.1f}ms",
                perf_status,
                f"Cache: {performance_metrics.get('cache_hits', 0)}H/{performance_metrics.get('cache_misses', 0)}M"
            ])

            return str(table)

    def format_system_summary_table(
        self,
        timestamp: float,
        symbols_processed: List[str],
        total_alerts: int,
        strategy_stats: Dict[str, Dict[str, Any]],
        system_performance: Dict[str, Any],
        error_count: int = 0
    ) -> str:
        """Format system-wide summary table.

        Args:
            timestamp: Summary timestamp
            symbols_processed: List of symbols processed this cycle
            total_alerts: Total alerts generated this cycle
            strategy_stats: Statistics for each strategy
            system_performance: System performance metrics
            error_count: Number of errors encountered

        Returns:
            Formatted summary table string
        """
        if not self.is_debug_enabled():
            return ""

        with self.timing_context("format_system_summary"):
            # Main system status table
            table = PrettyTable()
            table.field_names = ["Component", "Status", "Metrics", "Performance"]
            table.align = "l"

            time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
            table.title = f"🐋 WHALE HUNTER SYSTEM STATUS @ {time_str}"

            # System Overview
            processing_rate = len(symbols_processed) / max(system_performance.get('cycle_duration_s', 1), 0.1)
            system_status = "🟢 HEALTHY" if error_count == 0 else "🟡 DEGRADED" if error_count < 5 else "🔴 ERROR"
            
            table.add_row([
                "🎛️ System",
                system_status,
                f"{len(symbols_processed)} symbols, {total_alerts} alerts",
                f"{processing_rate:.1f} symbols/s, {system_performance.get('memory_usage_mb', 0):.0f}MB"
            ])

            # Strategy Performance
            for strategy_name, stats in strategy_stats.items():
                alerts = stats.get('alerts_generated', 0)
                analyses = stats.get('analysis_count', 0)
                alert_rate = alerts / max(analyses, 1)
                avg_time = stats.get('avg_analysis_time_ms', 0)
                
                status = "🔥 ACTIVE" if alerts > 0 else "📊 MONITORING"
                perf_status = "⚡" if avg_time < 50 else "🐌" if avg_time > 200 else "📊"
                
                table.add_row([
                    f"🧩 {strategy_name.replace('Strategy', '')}",
                    f"{status} ({alert_rate:.1%})",
                    f"{analyses} analyses, {alerts} alerts",
                    f"{perf_status} {avg_time:.1f}ms avg"
                ])

            # Cache Performance (if available)
            cache_stats = system_performance.get('cache_stats', {})
            if cache_stats:
                hit_rate = cache_stats.get('hit_rate', 0)
                cache_status = "🎯 EXCELLENT" if hit_rate > 0.8 else "📈 GOOD" if hit_rate > 0.6 else "📊 NORMAL"
                
                table.add_row([
                    "💾 Cache",
                    f"{cache_status} ({hit_rate:.1%})",
                    f"{cache_stats.get('cache_hits', 0)}H/{cache_stats.get('cache_misses', 0)}M",
                    f"{cache_stats.get('total_entries', 0)} entries"
                ])

            # Signal Fusion
            fusion_stats = system_performance.get('signal_fusion_stats', {})
            if fusion_stats:
                fusion_rate = fusion_stats.get('fusion_rate', 0)
                fused_signals = fusion_stats.get('fused_signals_created', 0)
                fusion_status = "🧠 ACTIVE" if fused_signals > 0 else "📊 STANDBY"
                
                table.add_row([
                    "🧠 Signal Fusion",
                    f"{fusion_status} ({fusion_rate:.1%})",
                    f"{fused_signals} fused, {fusion_stats.get('single_strategy_alerts', 0)} single",
                    f"{fusion_stats.get('pending_alerts', 0)} pending"
                ])

            # Network/API Performance
            api_stats = system_performance.get('api_stats', {})
            if api_stats:
                response_time = api_stats.get('avg_response_time_ms', 0)
                api_status = "⚡ FAST" if response_time < 200 else "📊 NORMAL" if response_time < 500 else "🐌 SLOW"
                
                table.add_row([
                    "🌐 API",
                    f"{api_status} ({response_time:.0f}ms)",
                    f"{api_stats.get('requests_made', 0)} requests, {api_stats.get('errors', 0)} errors",
                    f"{api_stats.get('rate_limit_remaining', 'N/A')} remaining"
                ])

            return str(table)

    def format_strategy_detail_table(
        self,
        strategy_name: str,
        symbol: str,
        calculations: Dict[str, Any],
        thresholds: Dict[str, Any],
        results: Dict[str, Any]
    ) -> str:
        """Format detailed strategy analysis table.

        Args:
            strategy_name: Name of the strategy
            symbol: Trading symbol
            calculations: Detailed calculation results
            thresholds: Strategy thresholds and configuration
            results: Final strategy results

        Returns:
            Formatted strategy detail table
        """
        if not self.is_debug_enabled():
            return ""

        with self.timing_context(f"format_{strategy_name}_detail"):
            table = PrettyTable()
            table.field_names = ["Parameter", "Value", "Threshold", "Status"]
            table.align = "l"
            table.title = f"🔍 {strategy_name.upper()} ANALYSIS - {symbol}"

            # Add calculations vs thresholds
            for param, value in calculations.items():
                threshold = thresholds.get(param, "N/A")
                
                # Determine status based on parameter type
                status = "✅ PASS"
                if isinstance(value, (int, float, Decimal)) and isinstance(threshold, (int, float, Decimal)):
                    if "ratio" in param.lower() or "multiplier" in param.lower():
                        status = "🔥 TRIGGER" if value >= threshold else "📊 NORMAL"
                    elif "confidence" in param.lower():
                        status = "🎯 HIGH" if value >= threshold else "📊 LOW"
                    elif "change" in param.lower():
                        status = "📈 SIGNIFICANT" if abs(value) >= abs(threshold) else "➡️ MINOR"
                
                table.add_row([
                    param.replace('_', ' ').title(),
                    self._format_value(value),
                    self._format_value(threshold),
                    status
                ])

            # Add results summary
            confidence = results.get('confidence', 0)
            whale_score = results.get('whale_score', 0)
            alert_generated = results.get('alert_generated', False)
            
            table.add_row([
                "Final Confidence",
                f"{confidence:.3f}",
                f"{thresholds.get('confidence_threshold', 0.6):.2f}",
                "🎯 PASS" if confidence >= thresholds.get('confidence_threshold', 0.6) else "❌ FAIL"
            ])
            
            table.add_row([
                "Whale Score",
                f"{whale_score:.1f}/100",
                "N/A",
                "🐋 WHALE" if whale_score >= 70 else "🐠 SMALL" if whale_score >= 40 else "🦐 MINOR"
            ])
            
            table.add_row([
                "Alert Status",
                "GENERATED" if alert_generated else "NONE",
                "N/A",
                "🚨 ALERT" if alert_generated else "✅ QUIET"
            ])

            return str(table)

    def format_performance_summary_table(
        self,
        system_stats: Dict[str, Any],
        period_minutes: int = 60
    ) -> str:
        """Format system performance summary table.

        Args:
            system_stats: System performance statistics
            period_minutes: Time period for statistics

        Returns:
            Formatted performance table
        """
        if not self.is_debug_enabled():
            return ""

        with self.timing_context("format_performance_summary"):
            table = PrettyTable()
            table.field_names = ["Component", "Throughput", "Latency", "Efficiency"]
            table.align = "l"
            table.title = f"⚡ PERFORMANCE SUMMARY - Last {period_minutes}min"

            # Processing throughput
            symbols_per_min = system_stats.get('symbols_processed_per_minute', 0)
            alerts_per_min = system_stats.get('alerts_per_minute', 0)
            
            table.add_row([
                "🔍 Analysis Engine",
                f"{symbols_per_min:.1f} symbols/min",
                f"{system_stats.get('avg_analysis_time_ms', 0):.1f}ms avg",
                f"{alerts_per_min:.2f} alerts/min"
            ])

            # Memory usage
            memory_mb = system_stats.get('memory_usage_mb', 0)
            memory_growth = system_stats.get('memory_growth_mb_per_hour', 0)
            
            table.add_row([
                "💾 Memory",
                f"{memory_mb:.1f}MB current",
                f"{memory_growth:+.1f}MB/hr growth",
                f"{system_stats.get('memory_efficiency_percent', 100):.1f}% efficient"
            ])

            # API performance
            api_calls = system_stats.get('api_calls_per_minute', 0)
            api_latency = system_stats.get('api_avg_latency_ms', 0)
            
            table.add_row([
                "🌐 API Calls",
                f"{api_calls:.1f} calls/min",
                f"{api_latency:.0f}ms avg",
                f"{system_stats.get('api_success_rate_percent', 100):.1f}% success"
            ])

            # Database operations (if applicable)
            if 'db_operations_per_minute' in system_stats:
                db_ops = system_stats.get('db_operations_per_minute', 0)
                db_latency = system_stats.get('db_avg_latency_ms', 0)
                
                table.add_row([
                    "🗃️ Database",
                    f"{db_ops:.1f} ops/min",
                    f"{db_latency:.1f}ms avg",
                    f"{system_stats.get('db_connection_pool_efficiency', 100):.1f}% pool"
                ])

            return str(table)

    def _format_value(self, value: Any) -> str:
        """Format a value for table display.

        Args:
            value: Value to format

        Returns:
            Formatted string representation
        """
        if isinstance(value, Decimal):
            if value < 1:
                return f"{value:.6f}"
            elif value < 1000:
                return f"{value:.2f}"
            else:
                return f"{value:,.0f}"
        elif isinstance(value, float):
            if value < 1:
                return f"{value:.6f}"
            elif value < 1000:
                return f"{value:.2f}"
            else:
                return f"{value:,.0f}"
        elif isinstance(value, int):
            return f"{value:,}"
        elif isinstance(value, str):
            return value[:50] + "..." if len(value) > 50 else value
        else:
            return str(value)

    def log_symbol_analysis_debug(
        self,
        symbol: str,
        timestamp: float,
        price_data: Dict[str, Any],
        volume_analysis: Dict[str, Any],
        orderbook_analysis: Dict[str, Any],
        momentum_analysis: Dict[str, Any],
        volatility_analysis: Dict[str, Any],
        signal_fusion: Dict[str, Any],
        alerts_generated: List[Any],
        performance_metrics: Dict[str, Any]
    ) -> None:
        """Log symbol analysis table if DEBUG is enabled.

        Args:
            symbol: Trading symbol
            timestamp: Analysis timestamp
            price_data: Current price and change information
            volume_analysis: Volume analysis results
            orderbook_analysis: Order book imbalance analysis
            momentum_analysis: Price momentum analysis
            volatility_analysis: Volatility metrics
            signal_fusion: Signal fusion results
            alerts_generated: List of alerts generated
            performance_metrics: Timing and performance data
        """
        if not self.is_debug_enabled():
            return

        table_output = self.format_symbol_analysis_table(
            symbol, timestamp, price_data, volume_analysis, orderbook_analysis,
            momentum_analysis, volatility_analysis, signal_fusion, alerts_generated,
            performance_metrics
        )
        
        if table_output:
            logger.debug(f"\n{table_output}")

    def log_system_summary_debug(
        self,
        timestamp: float,
        symbols_processed: List[str],
        total_alerts: int,
        strategy_stats: Dict[str, Dict[str, Any]],
        system_performance: Dict[str, Any],
        error_count: int = 0
    ) -> None:
        """Log system summary table if DEBUG is enabled.

        Args:
            timestamp: Summary timestamp
            symbols_processed: List of symbols processed this cycle
            total_alerts: Total alerts generated this cycle
            strategy_stats: Statistics for each strategy
            system_performance: System performance metrics
            error_count: Number of errors encountered
        """
        if not self.is_debug_enabled():
            return

        table_output = self.format_system_summary_table(
            timestamp, symbols_processed, total_alerts, strategy_stats,
            system_performance, error_count
        )
        
        if table_output:
            logger.debug(f"\n{table_output}")

    def get_formatting_stats(self) -> Dict[str, Any]:
        """Get statistics about table formatting performance.

        Returns:
            Dictionary with formatting performance statistics
        """
        if not self.formatting_times:
            return {"total_operations": 0, "avg_duration_ms": 0}

        recent_times = [
            op for op in self.formatting_times 
            if time.time() - op['timestamp'] <= 300  # Last 5 minutes
        ]

        return {
            "total_operations": len(recent_times),
            "avg_duration_ms": sum(op['duration_ms'] for op in recent_times) / max(len(recent_times), 1),
            "max_duration_ms": max((op['duration_ms'] for op in recent_times), default=0),
            "operations_by_type": {
                op_type: len([o for o in recent_times if op_type in o['operation']])
                for op_type in set(op['operation'].split('_')[0] for op in recent_times)
            }
        }


# Global instance for easy access
debug_formatter = DebugTableFormatter()


def log_symbol_debug(
    symbol: str,
    timestamp: float,
    price_data: Dict[str, Any],
    volume_analysis: Dict[str, Any],
    orderbook_analysis: Dict[str, Any],
    momentum_analysis: Dict[str, Any],
    volatility_analysis: Dict[str, Any],
    signal_fusion: Dict[str, Any],
    alerts_generated: List[Any],
    performance_metrics: Dict[str, Any]
) -> None:
    """Convenience function for logging symbol analysis debug tables."""
    debug_formatter.log_symbol_analysis_debug(
        symbol, timestamp, price_data, volume_analysis, orderbook_analysis,
        momentum_analysis, volatility_analysis, signal_fusion, alerts_generated,
        performance_metrics
    )


def log_system_debug(
    timestamp: float,
    symbols_processed: List[str],
    total_alerts: int,
    strategy_stats: Dict[str, Dict[str, Any]],
    system_performance: Dict[str, Any],
    error_count: int = 0
) -> None:
    """Convenience function for logging system summary debug tables."""
    debug_formatter.log_system_summary_debug(
        timestamp, symbols_processed, total_alerts, strategy_stats,
        system_performance, error_count
    )


def format_strategy_debug(
    strategy_name: str,
    symbol: str,
    calculations: Dict[str, Any],
    thresholds: Dict[str, Any],
    results: Dict[str, Any]
) -> str:
    """Convenience function for formatting strategy detail tables."""
    return debug_formatter.format_strategy_detail_table(
        strategy_name, symbol, calculations, thresholds, results
    )