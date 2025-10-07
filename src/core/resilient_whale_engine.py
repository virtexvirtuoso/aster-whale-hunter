"""
Resilient Whale Engine Integration

This module integrates the error analysis, async task management, session management,
and retry mechanisms into a unified whale detection engine wrapper.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime, timedelta

from .async_task_manager import AsyncTaskManager, get_task_manager
from .session_manager import SessionManager, SessionConfig, get_session_manager
from .retry_manager import RetryManager, RetryConfig, CircuitBreakerConfig, get_retry_manager
from .error_analysis import ErrorAnalyzer, ErrorSeverity, ErrorCategory
from implementations.multi_strategy_whale_engine import MultiStrategyWhaleEngine


class ResilientWhaleEngine:
    """
    Enhanced whale detection engine with integrated error handling,
    async management, and resilience features.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize resilient whale engine.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.resilience_config = config.get('resilience', {})

        # Initialize core components
        self.task_manager = get_task_manager()
        self.session_manager = get_session_manager()
        self.retry_manager = get_retry_manager()
        self.error_analyzer = ErrorAnalyzer(self.resilience_config.get('error_analysis', {}))

        # Configure session manager
        session_config = SessionConfig(
            timeout=self.resilience_config.get('session_timeout', 30.0),
            connection_limit=self.resilience_config.get('connection_limit', 100),
            connection_limit_per_host=self.resilience_config.get('connection_limit_per_host', 10)
        )
        self.default_session_config = session_config

        # Configure retry settings
        self.default_retry_config = RetryConfig(
            max_attempts=self.resilience_config.get('max_retry_attempts', 3),
            base_delay=self.resilience_config.get('retry_base_delay', 1.0),
            max_delay=self.resilience_config.get('retry_max_delay', 60.0),
            timeout=self.resilience_config.get('request_timeout', 30.0)
        )

        # Circuit breaker configuration
        self.circuit_breaker_config = CircuitBreakerConfig(
            failure_threshold=self.resilience_config.get('circuit_breaker_failure_threshold', 5),
            success_threshold=self.resilience_config.get('circuit_breaker_success_threshold', 3),
            timeout=self.resilience_config.get('circuit_breaker_timeout', 60.0)
        )

        # Underlying engines
        self.multi_strategy_engine = None

        # State management
        self.running = False
        self.initialization_complete = False

        # Statistics and monitoring
        self.stats = {
            'start_time': None,
            'total_errors': 0,
            'cancelled_tasks': 0,
            'session_leaks_prevented': 0,
            'circuit_breaker_activations': 0,
            'successful_recoveries': 0
        }

        self.logger = logging.getLogger(f"{__name__}.ResilientWhaleEngine")

        # Setup error recovery handlers
        self._setup_error_recovery()

    def _setup_error_recovery(self):
        """Setup automated error recovery handlers"""

        # Register recovery handlers with error analyzer
        self.error_analyzer.register_recovery_handler(
            "restart_monitoring_loop",
            self._restart_monitoring_loop
        )

        self.error_analyzer.register_recovery_handler(
            "close_all_sessions",
            self._close_leaky_sessions
        )

        self.error_analyzer.register_recovery_handler(
            "activate_circuit_breaker",
            self._activate_circuit_breaker
        )

        # Register error callback with task manager
        self.task_manager.add_error_callback(self._handle_task_error)

    async def initialize(self, asterdex_client, hyperliquid_client):
        """
        Initialize the resilient whale engine.

        Args:
            asterdex_client: AsterDex API client
            hyperliquid_client: HyperLiquid API client
        """
        self.logger.info("Initializing resilient whale detection engine...")

        try:
            # Wrap API clients with resilient session management
            wrapped_asterdx_client = self._wrap_api_client(asterdex_client, "asterdex")
            wrapped_hyperliquid_client = self._wrap_api_client(hyperliquid_client, "hyperliquid")

            # Initialize underlying engines with wrapped clients
            self.multi_strategy_engine = MultiStrategyWhaleEngine(self.config)
            await self.multi_strategy_engine.initialize(wrapped_asterdx_client, wrapped_hyperliquid_client)

            # Setup alert callbacks with error handling
            self.multi_strategy_engine.add_alert_callback(self._resilient_alert_handler)

            self.initialization_complete = True
            self.logger.info("Resilient whale detection engine initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize resilient whale engine: {e}")
            await self.error_analyzer.analyze_error(e, "initialization")
            raise

    def _wrap_api_client(self, client, client_name: str):
        """Wrap API client with resilient session and retry management"""

        class ResilientAPIWrapper:
            def __init__(self, original_client, engine):
                self.original_client = original_client
                self.engine = engine
                self.client_name = client_name
                self.logger = logging.getLogger(f"{__name__}.{client_name}_wrapper")

            async def __getattr__(self, name):
                """Wrap all method calls with resilience"""
                original_method = getattr(self.original_client, name)

                if not asyncio.iscoroutinefunction(original_method):
                    return original_method

                async def resilient_method(*args, **kwargs):
                    return await self.engine._execute_with_resilience(
                        original_method,
                        args,
                        kwargs,
                        f"{self.client_name}.{name}"
                    )

                return resilient_method

        return ResilientAPIWrapper(client, self)

    async def _execute_with_resilience(self, method, args, kwargs, operation_name: str):
        """Execute method with full resilience features"""

        async def execute():
            # Use managed session if method involves HTTP requests
            if hasattr(method, '__self__') and hasattr(method.__self__, 'session'):
                # Replace session with managed session
                session = self.session_manager.get_or_create_named_session(
                    f"{operation_name}_session",
                    self.default_session_config
                )
                method.__self__.session = session

            return await method(*args, **kwargs)

        try:
            # Execute with retry and circuit breaker
            result = await self.retry_manager.retry_call(
                execute,
                self.default_retry_config,
                circuit_breaker_name=operation_name,
                circuit_breaker_config=self.circuit_breaker_config
            )

            return result

        except Exception as e:
            # Analyze error and trigger recovery if needed
            await self.error_analyzer.analyze_error(e, operation_name)
            self.stats['total_errors'] += 1
            raise

    async def start(self):
        """Start the resilient whale detection engine"""
        if not self.initialization_complete:
            raise RuntimeError("Engine must be initialized before starting")

        self.running = True
        self.stats['start_time'] = time.time()
        self.logger.info("Starting resilient whale detection engine...")

        try:
            # Create main monitoring tasks with resilience
            main_tasks = [
                ("multi_strategy_monitoring", self._resilient_multi_strategy_loop),
                ("error_analysis_reporting", self._error_analysis_loop),
                ("health_monitoring", self._health_monitoring_loop),
                ("resource_cleanup", self._resource_cleanup_loop)
            ]

            # Start all tasks with the task manager
            for task_name, task_coro in main_tasks:
                self.task_manager.create_task(
                    task_coro(),
                    name=task_name,
                    group="main_monitoring",
                    auto_restart=True,
                    max_restarts=5
                )

            self.logger.info("All resilient monitoring tasks started")

            # Wait for shutdown signal
            await self.task_manager.shutdown_event.wait()

        except Exception as e:
            self.logger.error(f"Error in resilient whale engine: {e}")
            await self.error_analyzer.analyze_error(e, "main_engine")
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop the resilient whale detection engine"""
        self.logger.info("Stopping resilient whale detection engine...")
        self.running = False

        try:
            # Stop underlying engines
            if self.multi_strategy_engine:
                await self.multi_strategy_engine.stop()

            # Shutdown all managers
            await self.task_manager.shutdown_all()
            await self.session_manager.shutdown()

            self.logger.info("Resilient whale detection engine stopped successfully")

        except Exception as e:
            self.logger.error(f"Error stopping resilient whale engine: {e}")

    async def _resilient_multi_strategy_loop(self):
        """Main multi-strategy monitoring loop with resilience"""
        while self.running:
            try:
                # Run multi-strategy engine with timeout
                await asyncio.wait_for(
                    self.multi_strategy_engine.start(),
                    timeout=300  # 5 minute timeout for main loop iteration
                )

            except asyncio.CancelledError:
                self.logger.info("Multi-strategy monitoring loop cancelled")
                self.stats['cancelled_tasks'] += 1
                raise

            except asyncio.TimeoutError:
                self.logger.warning("Multi-strategy loop iteration timed out, restarting...")
                await self.error_analyzer.analyze_error(
                    TimeoutError("Multi-strategy loop timeout"),
                    "multi_strategy_loop"
                )

            except Exception as e:
                self.logger.error(f"Error in multi-strategy loop: {e}")
                await self.error_analyzer.analyze_error(e, "multi_strategy_loop")

                # Brief pause before retry
                await asyncio.sleep(5)

    async def _error_analysis_loop(self):
        """Periodic error analysis and reporting"""
        while self.running:
            try:
                # Generate error analysis report
                report = await self.error_analyzer.generate_error_report()

                # Log summary
                self.logger.info("Error analysis report generated")

                # Clean up old errors
                await self.error_analyzer.cleanup_old_errors()

                # Wait before next analysis
                await asyncio.sleep(900)  # 15 minutes

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger.error(f"Error in analysis loop: {e}")
                await asyncio.sleep(300)  # 5 minutes before retry

    async def _health_monitoring_loop(self):
        """Periodic health monitoring and statistics collection"""
        while self.running:
            try:
                # Collect statistics from all components
                task_stats = self.task_manager.get_statistics()
                session_stats = self.session_manager.get_statistics()
                retry_stats = self.retry_manager.get_statistics()
                error_stats = self.error_analyzer.get_error_statistics()

                # Log health summary
                self.logger.info(f"Health check - Tasks: {task_stats['active_tasks']}, "
                               f"Sessions: {session_stats['active_sessions']}, "
                               f"Errors: {error_stats.total_errors}")

                # Check for concerning patterns
                await self._check_health_alerts(task_stats, session_stats, retry_stats, error_stats)

                # Wait before next check
                await asyncio.sleep(300)  # 5 minutes

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(60)

    async def _resource_cleanup_loop(self):
        """Periodic resource cleanup"""
        while self.running:
            try:
                # Clean up old error records
                await self.error_analyzer.cleanup_old_errors()

                # Session cleanup is handled automatically by session manager

                # Wait before next cleanup
                await asyncio.sleep(1800)  # 30 minutes

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(300)

    async def _check_health_alerts(self, task_stats, session_stats, retry_stats, error_stats):
        """Check for health alert conditions"""
        alerts = []

        # Check task health
        if task_stats['tasks_failed'] > task_stats['tasks_completed'] * 0.1:
            alerts.append("High task failure rate detected")

        # Check session health
        if session_stats['active_sessions'] > 50:
            alerts.append("High number of active sessions - potential leak")

        # Check error rate
        if error_stats.error_rate_per_minute > 10:
            alerts.append(f"High error rate: {error_stats.error_rate_per_minute:.1f} errors/minute")

        # Log alerts
        for alert in alerts:
            self.logger.warning(f"Health Alert: {alert}")

    async def _resilient_alert_handler(self, alert):
        """Handle alerts with error resilience"""
        try:
            # Process alert with all configured callbacks
            for callback in self.multi_strategy_engine.alert_callbacks:
                try:
                    await callback(alert)
                except Exception as e:
                    self.logger.error(f"Alert callback failed: {e}")
                    await self.error_analyzer.analyze_error(e, "alert_callback")

        except Exception as e:
            self.logger.error(f"Error in alert handler: {e}")
            await self.error_analyzer.analyze_error(e, "alert_handler")

    async def _handle_task_error(self, task_id: str, error: Exception):
        """Handle task errors from task manager"""
        self.logger.error(f"Task {task_id} failed: {error}")
        await self.error_analyzer.analyze_error(error, f"task_{task_id}")

    async def _restart_monitoring_loop(self, error_instance):
        """Recovery action: restart monitoring loop"""
        self.logger.info("Attempting to restart monitoring loop...")
        try:
            # Cancel current multi-strategy tasks
            await self.task_manager.cancel_group("main_monitoring")

            # Brief pause
            await asyncio.sleep(2)

            # Restart main monitoring
            self.task_manager.create_task(
                self._resilient_multi_strategy_loop(),
                name="multi_strategy_monitoring_restart",
                group="main_monitoring",
                auto_restart=True
            )

            self.stats['successful_recoveries'] += 1
            self.logger.info("Monitoring loop restart completed")

        except Exception as e:
            self.logger.error(f"Failed to restart monitoring loop: {e}")

    async def _close_leaky_sessions(self, error_instance):
        """Recovery action: close potentially leaky sessions"""
        self.logger.info("Closing potentially leaky sessions...")
        try:
            # Close all sessions
            await self.session_manager.close_all_sessions()

            self.stats['session_leaks_prevented'] += 1
            self.logger.info("Session cleanup completed")

        except Exception as e:
            self.logger.error(f"Failed to close sessions: {e}")

    async def _activate_circuit_breaker(self, error_instance):
        """Recovery action: activate circuit breaker"""
        self.logger.info("Activating circuit breaker protection...")
        try:
            # Circuit breakers are automatically activated by retry manager
            # This is mainly for logging
            self.stats['circuit_breaker_activations'] += 1
            self.logger.info("Circuit breaker activation noted")

        except Exception as e:
            self.logger.error(f"Error in circuit breaker activation: {e}")

    def add_alert_callback(self, callback: Callable):
        """Add alert callback to the underlying engine"""
        if self.multi_strategy_engine:
            self.multi_strategy_engine.add_alert_callback(callback)

    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all components"""
        return {
            'resilient_engine': self.stats,
            'task_manager': self.task_manager.get_statistics(),
            'session_manager': self.session_manager.get_statistics(),
            'retry_manager': self.retry_manager.get_statistics(),
            'error_analyzer': self.error_analyzer.get_error_statistics(),
            'running': self.running,
            'initialized': self.initialization_complete
        }