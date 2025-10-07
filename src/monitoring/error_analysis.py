"""
Advanced Error Analysis and Systematic Categorization System

This module provides comprehensive error analysis, categorization, tracking,
and reporting capabilities for the whale hunter system.
"""

import asyncio
import time
import traceback
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
import logging
import json
from pathlib import Path
import aiofiles


class ErrorSeverity(Enum):
    """Error severity levels with color coding for display"""
    CRITICAL = ("🔴", "CRITICAL", 4)
    HIGH = ("🟡", "HIGH", 3)
    MEDIUM = ("🟠", "MEDIUM", 2)
    LOW = ("🟢", "LOW", 1)

    def __init__(self, emoji: str, display_name: str, priority: int):
        self.emoji = emoji
        self.display_name = display_name
        self.priority = priority


class ErrorCategory(Enum):
    """Error categorization for systematic analysis"""
    INFRASTRUCTURE = "infrastructure"  # Network, connections, resources
    APPLICATION_LOGIC = "application_logic"  # Business logic, validation
    INTEGRATION = "integration"  # API failures, external services
    DEVELOPMENT = "development"  # Import errors, configuration
    ASYNC_OPERATIONS = "async_operations"  # Async/await related issues
    RESOURCE_MANAGEMENT = "resource_management"  # Memory, connections
    DATA_PROCESSING = "data_processing"  # Data validation, transformation
    MONITORING = "monitoring"  # Monitoring and alerting failures


@dataclass
class ErrorPattern:
    """Represents an identified error pattern"""
    pattern_id: str
    description: str
    regex_patterns: List[str]
    category: ErrorCategory
    severity: ErrorSeverity
    suggested_actions: List[str]
    threshold_per_minute: int = 5
    recovery_actions: List[str] = field(default_factory=list)


@dataclass
class ErrorInstance:
    """Individual error occurrence"""
    timestamp: datetime
    error_type: str
    message: str
    component: str
    stack_trace: Optional[str]
    pattern_id: Optional[str]
    category: ErrorCategory
    severity: ErrorSeverity
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorStatistics:
    """Error statistics and trends"""
    total_errors: int = 0
    errors_by_severity: Dict[ErrorSeverity, int] = field(default_factory=lambda: defaultdict(int))
    errors_by_category: Dict[ErrorCategory, int] = field(default_factory=lambda: defaultdict(int))
    errors_by_component: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_rate_per_minute: float = 0.0
    most_frequent_errors: List[tuple] = field(default_factory=list)
    trend_analysis: Dict[str, Any] = field(default_factory=dict)


class ErrorAnalyzer:
    """Advanced error analysis and categorization system"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.error_patterns = self._initialize_error_patterns()
        self.error_history: List[ErrorInstance] = []
        self.error_counters = defaultdict(int)
        self.component_errors = defaultdict(list)
        self.alert_thresholds = self._setup_alert_thresholds()
        self.recovery_handlers: Dict[str, Callable] = {}
        self.circuit_breakers: Dict[str, Dict] = {}
        self.logger = logging.getLogger(f"{__name__}.ErrorAnalyzer")

        # Time window for analysis (configurable)
        self.analysis_window = timedelta(minutes=self.config.get('analysis_window_minutes', 15))

    def _initialize_error_patterns(self) -> Dict[str, ErrorPattern]:
        """Initialize known error patterns based on the analysis summary"""
        patterns = {}

        # CRITICAL ERRORS
        patterns["cancelled_error"] = ErrorPattern(
            pattern_id="cancelled_error",
            description="Async operations being cancelled - monitoring loop failures",
            regex_patterns=[
                r"CancelledError",
                r"asyncio\.CancelledError",
                r"Task was cancelled",
                r"operation was cancelled"
            ],
            category=ErrorCategory.ASYNC_OPERATIONS,
            severity=ErrorSeverity.CRITICAL,
            threshold_per_minute=3,
            suggested_actions=[
                "Check async task lifecycle management",
                "Implement proper cancellation handling",
                "Add timeout configuration for async operations",
                "Review task scheduling and cleanup"
            ],
            recovery_actions=[
                "restart_monitoring_loop",
                "clear_cancelled_tasks",
                "reinitialize_async_components"
            ]
        )

        patterns["unclosed_sessions"] = ErrorPattern(
            pattern_id="unclosed_sessions",
            description="aiohttp sessions not properly closed - resource leak",
            regex_patterns=[
                r"Unclosed client session",
                r"ResourceWarning.*unclosed",
                r"aiohttp.*session.*not.*closed",
                r"connector.*not.*closed"
            ],
            category=ErrorCategory.RESOURCE_MANAGEMENT,
            severity=ErrorSeverity.CRITICAL,
            threshold_per_minute=2,
            suggested_actions=[
                "Implement proper session cleanup",
                "Add context managers for aiohttp sessions",
                "Review connection pooling configuration",
                "Add session lifecycle monitoring"
            ],
            recovery_actions=[
                "close_all_sessions",
                "reinitialize_http_clients",
                "clear_connection_pool"
            ]
        )

        # HIGH PRIORITY ERRORS
        patterns["api_connection_failures"] = ErrorPattern(
            pattern_id="api_connection_failures",
            description="API fetch operations failing rapidly",
            regex_patterns=[
                r"fetch.*order.*book.*failed",
                r"fetch.*open.*interest.*failed",
                r"API.*connection.*failed",
                r"timeout.*api.*call",
                r"ConnectionError.*api"
            ],
            category=ErrorCategory.INTEGRATION,
            severity=ErrorSeverity.HIGH,
            threshold_per_minute=10,
            suggested_actions=[
                "Check API endpoint availability",
                "Implement exponential backoff",
                "Add circuit breaker protection",
                "Review rate limiting configuration"
            ],
            recovery_actions=[
                "activate_circuit_breaker",
                "switch_to_backup_endpoints",
                "reduce_request_frequency"
            ]
        )

        # MEDIUM PRIORITY ERRORS
        patterns["module_import_errors"] = ErrorPattern(
            pattern_id="module_import_errors",
            description="Module import and path resolution issues",
            regex_patterns=[
                r"ModuleNotFoundError",
                r"ImportError",
                r"No module named",
                r"utils.*module.*not.*found"
            ],
            category=ErrorCategory.DEVELOPMENT,
            severity=ErrorSeverity.MEDIUM,
            threshold_per_minute=1,
            suggested_actions=[
                "Fix import paths and PYTHONPATH",
                "Verify module installation",
                "Check package structure",
                "Update requirements.txt"
            ],
            recovery_actions=[
                "reload_modules",
                "fix_import_paths"
            ]
        )

        patterns["parameter_mismatch"] = ErrorPattern(
            pattern_id="parameter_mismatch",
            description="Strategy initialization parameter mismatches",
            regex_patterns=[
                r"TypeError.*parameter.*mismatch",
                r"unexpected.*keyword.*argument",
                r"missing.*required.*parameter",
                r"side.*parameter.*not.*expected"
            ],
            category=ErrorCategory.APPLICATION_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            threshold_per_minute=1,
            suggested_actions=[
                "Review strategy initialization parameters",
                "Update strategy interfaces",
                "Validate configuration schemas",
                "Add parameter validation"
            ],
            recovery_actions=[
                "use_default_parameters",
                "skip_invalid_strategies"
            ]
        )

        return patterns

    def _setup_alert_thresholds(self) -> Dict[str, Dict]:
        """Setup alert thresholds for different error types"""
        return {
            "error_rate": {
                "critical": 20,  # errors per minute
                "high": 10,
                "medium": 5,
                "low": 1
            },
            "component_failure_rate": {
                "critical": 0.8,  # 80% failure rate
                "high": 0.5,
                "medium": 0.3,
                "low": 0.1
            },
            "pattern_frequency": {
                "cancelled_error": 3,
                "unclosed_sessions": 2,
                "api_connection_failures": 10
            }
        }

    async def analyze_error(self, error: Exception, component: str, context: Dict[str, Any] = None) -> ErrorInstance:
        """Analyze and categorize a single error"""
        error_message = str(error)
        error_type = type(error).__name__
        stack_trace = traceback.format_exc()

        # Pattern matching
        pattern_id, category, severity = self._match_error_pattern(error_message, stack_trace)

        error_instance = ErrorInstance(
            timestamp=datetime.now(),
            error_type=error_type,
            message=error_message,
            component=component,
            stack_trace=stack_trace,
            pattern_id=pattern_id,
            category=category,
            severity=severity,
            context=context or {}
        )

        # Store error
        self.error_history.append(error_instance)
        self.error_counters[pattern_id] += 1
        self.component_errors[component].append(error_instance)

        # Check for alerts
        await self._check_alert_conditions(error_instance)

        # Trigger recovery actions if needed
        await self._trigger_recovery_actions(error_instance)

        return error_instance

    def _match_error_pattern(self, message: str, stack_trace: str = None) -> tuple:
        """Match error against known patterns"""
        import re

        text_to_search = f"{message}\n{stack_trace or ''}"

        for pattern in self.error_patterns.values():
            for regex_pattern in pattern.regex_patterns:
                if re.search(regex_pattern, text_to_search, re.IGNORECASE):
                    return pattern.pattern_id, pattern.category, pattern.severity

        # Default categorization
        if "async" in message.lower() or "cancelled" in message.lower():
            return "unknown_async", ErrorCategory.ASYNC_OPERATIONS, ErrorSeverity.MEDIUM
        elif "connection" in message.lower() or "timeout" in message.lower():
            return "unknown_connection", ErrorCategory.INTEGRATION, ErrorSeverity.HIGH
        elif "import" in message.lower() or "module" in message.lower():
            return "unknown_import", ErrorCategory.DEVELOPMENT, ErrorSeverity.LOW
        else:
            return "unknown_error", ErrorCategory.APPLICATION_LOGIC, ErrorSeverity.MEDIUM

    async def _check_alert_conditions(self, error_instance: ErrorInstance):
        """Check if error instance triggers any alert conditions"""
        current_time = datetime.now()
        window_start = current_time - timedelta(minutes=1)

        # Count recent errors of same pattern
        recent_pattern_errors = [
            err for err in self.error_history
            if err.pattern_id == error_instance.pattern_id
            and err.timestamp >= window_start
        ]

        pattern = self.error_patterns.get(error_instance.pattern_id)
        if pattern and len(recent_pattern_errors) >= pattern.threshold_per_minute:
            await self._send_alert(f"Pattern threshold exceeded: {pattern.description}",
                                 pattern.severity, recent_pattern_errors)

        # Check overall error rate
        recent_errors = [err for err in self.error_history if err.timestamp >= window_start]
        error_rate = len(recent_errors)

        thresholds = self.alert_thresholds["error_rate"]
        if error_rate >= thresholds["critical"]:
            await self._send_alert(f"CRITICAL error rate: {error_rate} errors/minute",
                                 ErrorSeverity.CRITICAL, recent_errors)
        elif error_rate >= thresholds["high"]:
            await self._send_alert(f"HIGH error rate: {error_rate} errors/minute",
                                 ErrorSeverity.HIGH, recent_errors)

    async def _send_alert(self, message: str, severity: ErrorSeverity, errors: List[ErrorInstance]):
        """Send alert for error condition"""
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity.name,
            "message": message,
            "error_count": len(errors),
            "affected_components": list(set(err.component for err in errors)),
            "error_types": list(set(err.error_type for err in errors))
        }

        self.logger.error(f"{severity.emoji} ALERT: {message}")
        self.logger.error(f"Alert details: {json.dumps(alert_data, indent=2)}")

        # Here you could integrate with external alerting systems
        # e.g., send to Telegram, Slack, email, etc.

    async def _trigger_recovery_actions(self, error_instance: ErrorInstance):
        """Trigger automated recovery actions for known error patterns"""
        pattern = self.error_patterns.get(error_instance.pattern_id)
        if not pattern:
            return

        for recovery_action in pattern.recovery_actions:
            handler = self.recovery_handlers.get(recovery_action)
            if handler:
                try:
                    self.logger.info(f"Triggering recovery action: {recovery_action}")
                    await handler(error_instance)
                except Exception as e:
                    self.logger.error(f"Recovery action {recovery_action} failed: {e}")

    def get_error_statistics(self, time_window: timedelta = None) -> ErrorStatistics:
        """Generate comprehensive error statistics"""
        if time_window is None:
            time_window = self.analysis_window

        cutoff_time = datetime.now() - time_window
        recent_errors = [err for err in self.error_history if err.timestamp >= cutoff_time]

        stats = ErrorStatistics()
        stats.total_errors = len(recent_errors)

        # Count by severity and category
        for error in recent_errors:
            stats.errors_by_severity[error.severity] += 1
            stats.errors_by_category[error.category] += 1
            stats.errors_by_component[error.component] += 1

        # Calculate error rate per minute
        window_minutes = time_window.total_seconds() / 60
        stats.error_rate_per_minute = stats.total_errors / window_minutes if window_minutes > 0 else 0

        # Most frequent errors
        error_counts = Counter(err.pattern_id for err in recent_errors)
        stats.most_frequent_errors = error_counts.most_common(10)

        # Trend analysis
        stats.trend_analysis = self._calculate_trends(recent_errors)

        return stats

    def _calculate_trends(self, errors: List[ErrorInstance]) -> Dict[str, Any]:
        """Calculate error trends and patterns"""
        if not errors:
            return {}

        # Group errors by hour
        hourly_counts = defaultdict(int)
        for error in errors:
            hour_key = error.timestamp.strftime("%Y-%m-%d %H:00")
            hourly_counts[hour_key] += 1

        # Calculate trend direction
        hours = sorted(hourly_counts.keys())
        if len(hours) >= 2:
            recent_count = hourly_counts[hours[-1]]
            previous_count = hourly_counts[hours[-2]] if len(hours) > 1 else 0
            trend = "increasing" if recent_count > previous_count else "decreasing"
        else:
            trend = "stable"

        return {
            "hourly_distribution": dict(hourly_counts),
            "trend_direction": trend,
            "peak_error_hour": max(hourly_counts.items(), key=lambda x: x[1])[0] if hourly_counts else None,
            "error_distribution_by_hour": hourly_counts
        }

    async def generate_error_report(self, output_file: str = None) -> str:
        """Generate comprehensive error analysis report"""
        stats = self.get_error_statistics()

        report = f"""
🔍 ERROR ANALYSIS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Analysis Window: {self.analysis_window}

📊 SUMMARY STATISTICS
Total Errors: {stats.total_errors}
Error Rate: {stats.error_rate_per_minute:.2f} errors/minute
Trend: {stats.trend_analysis.get('trend_direction', 'unknown')}

🔴 ERRORS BY SEVERITY:
"""
        for severity in ErrorSeverity:
            count = stats.errors_by_severity[severity]
            percentage = (count / stats.total_errors * 100) if stats.total_errors > 0 else 0
            report += f"{severity.emoji} {severity.name}: {count} ({percentage:.1f}%)\n"

        report += f"\n📂 ERRORS BY CATEGORY:\n"
        for category in ErrorCategory:
            count = stats.errors_by_category[category]
            percentage = (count / stats.total_errors * 100) if stats.total_errors > 0 else 0
            report += f"  {category.value}: {count} ({percentage:.1f}%)\n"

        report += f"\n🏗️ ERRORS BY COMPONENT:\n"
        for component, count in sorted(stats.errors_by_component.items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / stats.total_errors * 100) if stats.total_errors > 0 else 0
            report += f"  {component}: {count} ({percentage:.1f}%)\n"

        report += f"\n🔥 MOST FREQUENT ERROR PATTERNS:\n"
        for pattern_id, count in stats.most_frequent_errors[:5]:
            pattern = self.error_patterns.get(pattern_id)
            severity_emoji = pattern.severity.emoji if pattern else "❓"
            report += f"{severity_emoji} {pattern_id}: {count} occurrences\n"
            if pattern:
                report += f"   Description: {pattern.description}\n"
                report += f"   Category: {pattern.category.value}\n"

        report += f"\n💡 RECOMMENDATIONS:\n"
        recommendations = self._generate_recommendations(stats)
        for rec in recommendations:
            report += f"• {rec}\n"

        if output_file:
            async with aiofiles.open(output_file, 'w') as f:
                await f.write(report)

        return report

    def _generate_recommendations(self, stats: ErrorStatistics) -> List[str]:
        """Generate actionable recommendations based on error analysis"""
        recommendations = []

        # Critical error rate
        if stats.error_rate_per_minute > 10:
            recommendations.append("🚨 URGENT: Error rate is critically high - immediate investigation required")

        # Pattern-specific recommendations
        for pattern_id, count in stats.most_frequent_errors[:3]:
            pattern = self.error_patterns.get(pattern_id)
            if pattern and count > pattern.threshold_per_minute:
                recommendations.extend([f"🔧 {action}" for action in pattern.suggested_actions])

        # Category-specific recommendations
        async_errors = stats.errors_by_category.get(ErrorCategory.ASYNC_OPERATIONS, 0)
        if async_errors > stats.total_errors * 0.3:  # More than 30% are async errors
            recommendations.append("⚡ High async error rate - review async/await patterns and task management")

        resource_errors = stats.errors_by_category.get(ErrorCategory.RESOURCE_MANAGEMENT, 0)
        if resource_errors > stats.total_errors * 0.2:  # More than 20% are resource errors
            recommendations.append("💾 Resource management issues detected - audit connection and memory usage")

        return recommendations

    def register_recovery_handler(self, action_name: str, handler: Callable):
        """Register a recovery action handler"""
        self.recovery_handlers[action_name] = handler

    async def cleanup_old_errors(self, max_age: timedelta = None):
        """Clean up old error records to prevent memory bloat"""
        if max_age is None:
            max_age = timedelta(hours=24)

        cutoff_time = datetime.now() - max_age
        self.error_history = [err for err in self.error_history if err.timestamp >= cutoff_time]

        # Clean up component errors
        for component in self.component_errors:
            self.component_errors[component] = [
                err for err in self.component_errors[component]
                if err.timestamp >= cutoff_time
            ]