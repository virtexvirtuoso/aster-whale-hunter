"""
System-wide Debug Monitor - Provides comprehensive debug logging and performance monitoring
for the entire whale detection system.
"""

import logging
import time
import psutil
import asyncio
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from datetime import datetime
from dataclasses import dataclass

from .debug_table_formatter import debug_formatter

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics snapshot."""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    symbols_processed: int
    total_alerts: int
    active_strategies: int
    cache_hit_rate: float
    avg_analysis_time_ms: float


class SystemDebugMonitor:
    """
    System-wide debug monitor for whale detection system.
    
    Features:
    - Tracks performance metrics across all components
    - Provides system-wide summary logging
    - Monitors resource usage and bottlenecks
    - Aggregates statistics from all strategies and components
    - Only logs when DEBUG level is enabled
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the system debug monitor.

        Args:
            config: Configuration containing:
                - summary_interval_seconds: How often to log system summary (default: 60)
                - performance_history_size: Number of metrics to keep in memory (default: 100)
                - enable_resource_monitoring: Enable CPU/memory monitoring (default: True)
                - alert_rate_threshold: Alert rate threshold for warnings (default: 0.1)
        """
        self.summary_interval_seconds = config.get('summary_interval_seconds', 60)
        self.performance_history_size = config.get('performance_history_size', 100)
        self.enable_resource_monitoring = config.get('enable_resource_monitoring', True)
        self.alert_rate_threshold = config.get('alert_rate_threshold', 0.1)

        # Performance tracking
        self.system_metrics_history = deque(maxlen=self.performance_history_size)
        self.component_stats = {}  # Component name -> latest stats
        self.strategy_stats = {}   # Strategy name -> latest stats
        
        # Cycle tracking
        self.cycle_count = 0
        self.total_symbols_processed = 0
        self.total_alerts_generated = 0
        self.total_errors_encountered = 0
        
        # Timing
        self.last_summary_time = time.time()
        self.system_start_time = time.time()
        
        # Process for resource monitoring
        self.process = psutil.Process() if self.enable_resource_monitoring else None

        logger.info(f"SystemDebugMonitor initialized: summary_interval={self.summary_interval_seconds}s")

    def update_component_stats(self, component_name: str, stats: Dict[str, Any]) -> None:
        """Update statistics for a system component.

        Args:
            component_name: Name of the component (e.g., 'VolatilityCache', 'SignalFusion')
            stats: Latest statistics from the component
        """
        self.component_stats[component_name] = {
            'timestamp': time.time(),
            'stats': stats.copy()
        }

    def update_strategy_stats(self, strategy_name: str, stats: Dict[str, Any]) -> None:
        """Update statistics for a detection strategy.

        Args:
            strategy_name: Name of the strategy (e.g., 'VolumeWhaleStrategy')
            stats: Latest statistics from the strategy
        """
        self.strategy_stats[strategy_name] = {
            'timestamp': time.time(),
            'stats': stats.copy()
        }

    def log_cycle_start(self, symbols: List[str]) -> float:
        """Log the start of a processing cycle.

        Args:
            symbols: List of symbols being processed this cycle

        Returns:
            Cycle start timestamp for timing
        """
        self.cycle_count += 1
        self.total_symbols_processed += len(symbols)
        
        cycle_start_time = time.time()
        
        if debug_formatter.is_debug_enabled():
            logger.debug(f"🔄 Processing Cycle {self.cycle_count} Started - {len(symbols)} symbols")
            
        return cycle_start_time

    def log_cycle_complete(
        self, 
        cycle_start_time: float, 
        symbols_processed: List[str],
        total_alerts_generated: int,
        errors_encountered: int = 0
    ) -> None:
        """Log the completion of a processing cycle.

        Args:
            cycle_start_time: Timestamp from log_cycle_start
            symbols_processed: List of symbols that were processed
            total_alerts_generated: Total alerts generated this cycle
            errors_encountered: Number of errors encountered this cycle
        """
        cycle_end_time = time.time()
        cycle_duration_s = cycle_end_time - cycle_start_time
        
        self.total_alerts_generated += total_alerts_generated
        self.total_errors_encountered += errors_encountered
        
        # Calculate performance metrics
        processing_rate = len(symbols_processed) / max(cycle_duration_s, 0.001)
        
        if debug_formatter.is_debug_enabled():
            logger.debug(
                f"✅ Processing Cycle {self.cycle_count} Complete - "
                f"{len(symbols_processed)} symbols, {total_alerts_generated} alerts, "
                f"{processing_rate:.1f} sym/s, {cycle_duration_s:.2f}s"
            )

        # Check if it's time for system summary
        if cycle_end_time - self.last_summary_time >= self.summary_interval_seconds:
            self.log_system_summary()

    def log_system_summary(self) -> None:
        """Log comprehensive system summary with performance metrics."""
        if not debug_formatter.is_debug_enabled():
            return

        current_time = time.time()
        
        try:
            # Collect system resource metrics
            system_metrics = self._collect_system_metrics(current_time)
            self.system_metrics_history.append(system_metrics)
            
            # Aggregate strategy statistics
            strategy_summary = self._aggregate_strategy_stats()
            
            # Aggregate component statistics
            component_summary = self._aggregate_component_stats()
            
            # Calculate system performance metrics
            system_performance = self._calculate_system_performance()
            
            # Log the comprehensive summary table
            debug_formatter.log_system_summary_debug(
                timestamp=current_time,
                symbols_processed=list(self.component_stats.keys()),  # Placeholder
                total_alerts=self.total_alerts_generated,
                strategy_stats=strategy_summary,
                system_performance=system_performance,
                error_count=self.total_errors_encountered
            )
            
            # Log performance summary table
            performance_table = debug_formatter.format_performance_summary_table(
                system_stats=system_performance,
                period_minutes=int(self.summary_interval_seconds / 60)
            )
            
            if performance_table:
                logger.debug(f"\n{performance_table}")
            
            # Update last summary time
            self.last_summary_time = current_time
            
        except Exception as e:
            logger.error(f"Error generating system summary: {e}")

    def _collect_system_metrics(self, current_time: float) -> SystemMetrics:
        """Collect current system resource metrics.

        Args:
            current_time: Current timestamp

        Returns:
            SystemMetrics object with current system state
        """
        cpu_percent = 0.0
        memory_mb = 0.0
        memory_percent = 0.0
        
        if self.enable_resource_monitoring and self.process:
            try:
                cpu_percent = self.process.cpu_percent()
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
                memory_percent = self.process.memory_percent()
            except Exception as e:
                logger.warning(f"Could not collect resource metrics: {e}")

        # Calculate aggregated metrics
        total_symbols = sum(
            stats['stats'].get('symbols_tracked', 0) 
            for stats in self.strategy_stats.values()
        )
        
        total_alerts = sum(
            stats['stats'].get('alerts_generated', 0)
            for stats in self.strategy_stats.values()
        )
        
        active_strategies = len([
            s for s in self.strategy_stats.values()
            if s['stats'].get('alerts_generated', 0) > 0
        ])
        
        # Calculate average cache hit rate
        cache_components = [
            stats['stats'] for stats in self.component_stats.values()
            if 'hit_rate' in stats.get('stats', {})
        ]
        cache_hit_rate = (
            sum(comp.get('hit_rate', 0) for comp in cache_components) / max(len(cache_components), 1)
        )
        
        # Calculate average analysis time
        strategy_times = [
            stats['stats'].get('avg_analysis_time_ms', 0)
            for stats in self.strategy_stats.values()
            if 'avg_analysis_time_ms' in stats['stats']
        ]
        avg_analysis_time = sum(strategy_times) / max(len(strategy_times), 1)

        return SystemMetrics(
            timestamp=current_time,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            memory_percent=memory_percent,
            symbols_processed=total_symbols,
            total_alerts=total_alerts,
            active_strategies=active_strategies,
            cache_hit_rate=cache_hit_rate,
            avg_analysis_time_ms=avg_analysis_time
        )

    def _aggregate_strategy_stats(self) -> Dict[str, Dict[str, Any]]:
        """Aggregate statistics from all strategies.

        Returns:
            Dictionary mapping strategy names to their aggregated stats
        """
        aggregated = {}
        
        for strategy_name, strategy_data in self.strategy_stats.items():
            stats = strategy_data['stats']
            
            # Extract key metrics
            aggregated[strategy_name] = {
                'analysis_count': stats.get('analysis_count', 0),
                'alerts_generated': stats.get('alerts_generated', 0),
                'alert_rate': stats.get('alert_rate', 0),
                'symbols_tracked': stats.get('symbols_tracked', 0),
                'avg_analysis_time_ms': stats.get('avg_analysis_time_ms', 0),
                'last_update': strategy_data['timestamp']
            }
            
        return aggregated

    def _aggregate_component_stats(self) -> Dict[str, Dict[str, Any]]:
        """Aggregate statistics from all system components.

        Returns:
            Dictionary mapping component names to their aggregated stats
        """
        aggregated = {}
        
        for component_name, component_data in self.component_stats.items():
            stats = component_data['stats']
            
            # Extract key metrics (different components have different metrics)
            aggregated[component_name] = {
                'system_name': stats.get('system_name', component_name),
                'last_update': component_data['timestamp']
            }
            
            # Add component-specific metrics
            if 'cache_hits' in stats:
                aggregated[component_name].update({
                    'cache_hits': stats.get('cache_hits', 0),
                    'cache_misses': stats.get('cache_misses', 0),
                    'hit_rate': stats.get('hit_rate', 0)
                })
                
            if 'alerts_processed' in stats:
                aggregated[component_name].update({
                    'alerts_processed': stats.get('alerts_processed', 0),
                    'fused_signals_created': stats.get('fused_signals_created', 0),
                    'fusion_rate': stats.get('fusion_rate', 0)
                })
                
        return aggregated

    def _calculate_system_performance(self) -> Dict[str, Any]:
        """Calculate overall system performance metrics.

        Returns:
            Dictionary with system performance metrics
        """
        current_time = time.time()
        uptime_seconds = current_time - self.system_start_time
        
        # Get latest system metrics
        latest_metrics = self.system_metrics_history[-1] if self.system_metrics_history else None
        
        # Calculate rates
        symbols_per_minute = (self.total_symbols_processed / max(uptime_seconds / 60, 1))
        alerts_per_minute = (self.total_alerts_generated / max(uptime_seconds / 60, 1))
        cycles_per_minute = (self.cycle_count / max(uptime_seconds / 60, 1))
        
        # Memory growth calculation
        memory_growth_mb_per_hour = 0.0
        if len(self.system_metrics_history) >= 2:
            first_memory = self.system_metrics_history[0].memory_mb
            last_memory = self.system_metrics_history[-1].memory_mb
            time_span_hours = (self.system_metrics_history[-1].timestamp - 
                             self.system_metrics_history[0].timestamp) / 3600
            if time_span_hours > 0:
                memory_growth_mb_per_hour = (last_memory - first_memory) / time_span_hours

        performance_metrics = {
            'uptime_seconds': uptime_seconds,
            'uptime_hours': uptime_seconds / 3600,
            'cycle_duration_s': self.summary_interval_seconds,
            'symbols_processed_per_minute': symbols_per_minute,
            'alerts_per_minute': alerts_per_minute,
            'cycles_per_minute': cycles_per_minute,
            'total_cycles': self.cycle_count,
            'total_symbols_processed': self.total_symbols_processed,
            'total_alerts_generated': self.total_alerts_generated,
            'total_errors': self.total_errors_encountered,
            'error_rate': self.total_errors_encountered / max(self.cycle_count, 1),
            'memory_growth_mb_per_hour': memory_growth_mb_per_hour
        }
        
        # Add latest system metrics if available
        if latest_metrics:
            performance_metrics.update({
                'memory_usage_mb': latest_metrics.memory_mb,
                'memory_usage_percent': latest_metrics.memory_percent,
                'cpu_usage_percent': latest_metrics.cpu_percent,
                'cache_stats': {
                    'hit_rate': latest_metrics.cache_hit_rate
                }
            })

        # Add strategy and component stats
        performance_metrics['strategy_stats'] = self._get_aggregated_strategy_performance()
        performance_metrics['component_stats'] = self._get_aggregated_component_performance()
        
        return performance_metrics

    def _get_aggregated_strategy_performance(self) -> Dict[str, Any]:
        """Get aggregated performance metrics for strategies."""
        if not self.strategy_stats:
            return {}

        total_analyses = sum(
            stats['stats'].get('analysis_count', 0) 
            for stats in self.strategy_stats.values()
        )
        
        total_alerts = sum(
            stats['stats'].get('alerts_generated', 0)
            for stats in self.strategy_stats.values()
        )
        
        avg_analysis_times = [
            stats['stats'].get('avg_analysis_time_ms', 0)
            for stats in self.strategy_stats.values()
            if 'avg_analysis_time_ms' in stats['stats']
        ]
        
        return {
            'total_analyses': total_analyses,
            'total_strategy_alerts': total_alerts,
            'avg_analysis_time_ms': sum(avg_analysis_times) / max(len(avg_analysis_times), 1),
            'active_strategies': len(self.strategy_stats)
        }

    def _get_aggregated_component_performance(self) -> Dict[str, Any]:
        """Get aggregated performance metrics for components."""
        if not self.component_stats:
            return {}

        # Aggregate cache performance
        cache_hits = sum(
            stats['stats'].get('cache_hits', 0)
            for stats in self.component_stats.values()
            if 'cache_hits' in stats['stats']
        )
        
        cache_misses = sum(
            stats['stats'].get('cache_misses', 0)
            for stats in self.component_stats.values()
            if 'cache_misses' in stats['stats']
        )
        
        total_requests = cache_hits + cache_misses
        overall_hit_rate = cache_hits / max(total_requests, 1)
        
        # Aggregate fusion performance
        fusion_stats = {}
        for stats in self.component_stats.values():
            if 'alerts_processed' in stats['stats']:  # SignalFusion component
                fusion_stats = stats['stats']
                break

        return {
            'cache_performance': {
                'total_hits': cache_hits,
                'total_misses': cache_misses,
                'overall_hit_rate': overall_hit_rate
            },
            'signal_fusion_stats': fusion_stats,
            'active_components': len(self.component_stats)
        }

    def get_system_health_status(self) -> Dict[str, Any]:
        """Get overall system health status.

        Returns:
            Dictionary with system health indicators
        """
        if not self.system_metrics_history:
            return {'status': 'UNKNOWN', 'reason': 'No metrics available'}

        latest_metrics = self.system_metrics_history[-1]
        issues = []
        
        # Check memory usage
        if latest_metrics.memory_percent > 90:
            issues.append(f"High memory usage: {latest_metrics.memory_percent:.1f}%")
        
        # Check CPU usage
        if latest_metrics.cpu_percent > 80:
            issues.append(f"High CPU usage: {latest_metrics.cpu_percent:.1f}%")
        
        # Check error rate
        error_rate = self.total_errors_encountered / max(self.cycle_count, 1)
        if error_rate > 0.1:  # >10% error rate
            issues.append(f"High error rate: {error_rate:.1%}")
        
        # Check if strategies are generating alerts (system effectiveness)
        recent_alerts = sum(
            stats['stats'].get('alerts_generated', 0)
            for stats in self.strategy_stats.values()
        )
        
        if recent_alerts == 0 and self.cycle_count > 10:
            issues.append("No alerts generated recently - system may be misconfigured")

        # Determine overall status
        if not issues:
            status = 'HEALTHY'
        elif len(issues) == 1:
            status = 'WARNING'
        else:
            status = 'CRITICAL'

        return {
            'status': status,
            'issues': issues,
            'uptime_hours': (time.time() - self.system_start_time) / 3600,
            'cycles_completed': self.cycle_count,
            'total_alerts': self.total_alerts_generated,
            'memory_mb': latest_metrics.memory_mb,
            'cpu_percent': latest_metrics.cpu_percent
        }


# Global instance for easy access
system_monitor = None


def get_system_monitor(config: Optional[Dict[str, Any]] = None) -> SystemDebugMonitor:
    """Get or create the global system debug monitor.

    Args:
        config: Configuration for monitor (only used on first call)

    Returns:
        SystemDebugMonitor instance
    """
    global system_monitor
    if system_monitor is None:
        if config is None:
            config = {}
        system_monitor = SystemDebugMonitor(config)
    return system_monitor


def log_cycle_start(symbols: List[str]) -> float:
    """Convenience function for logging cycle start."""
    return get_system_monitor().log_cycle_start(symbols)


def log_cycle_complete(
    cycle_start_time: float,
    symbols_processed: List[str],
    total_alerts_generated: int,
    errors_encountered: int = 0
) -> None:
    """Convenience function for logging cycle completion."""
    get_system_monitor().log_cycle_complete(
        cycle_start_time, symbols_processed, total_alerts_generated, errors_encountered
    )


def update_strategy_stats(strategy_name: str, stats: Dict[str, Any]) -> None:
    """Convenience function for updating strategy statistics."""
    get_system_monitor().update_strategy_stats(strategy_name, stats)


def update_component_stats(component_name: str, stats: Dict[str, Any]) -> None:
    """Convenience function for updating component statistics."""
    get_system_monitor().update_component_stats(component_name, stats)