"""
Advanced Retry and Timeout Manager for API Calls

This module provides sophisticated retry logic, timeout handling, and circuit breaker
functionality to improve reliability of API calls in the whale hunter system.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable, Union, Type
import aiohttp
import traceback
from functools import wraps


class RetryStrategy(Enum):
    """Retry strategy types"""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    RANDOM = "random"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.1

    # Timeout configuration
    timeout: float = 30.0
    connect_timeout: float = 10.0
    read_timeout: float = 30.0

    # Retry conditions
    retry_on_timeout: bool = True
    retry_on_connection_error: bool = True
    retry_on_status_codes: List[int] = field(default_factory=lambda: [502, 503, 504, 429])
    retry_on_exceptions: List[Type[Exception]] = field(default_factory=lambda: [
        aiohttp.ClientConnectionError,
        aiohttp.ClientTimeout,
        aiohttp.ServerTimeoutError,
        asyncio.TimeoutError,
        ConnectionError
    ])


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout: float = 60.0
    half_open_max_calls: int = 1
    monitor_window: float = 300.0  # 5 minutes


@dataclass
class RetryAttempt:
    """Information about a retry attempt"""
    attempt: int
    timestamp: datetime
    error: Optional[Exception]
    response_time: float
    status_code: Optional[int] = None


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics"""
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_time: Optional[datetime]
    last_success_time: Optional[datetime]
    total_requests: int
    failed_requests: int
    state_change_time: datetime


class CircuitBreaker:
    """Circuit breaker implementation for API protection"""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        self.state_change_time = datetime.now()
        self.total_requests = 0
        self.failed_requests = 0
        self.half_open_calls = 0

        self.logger = logging.getLogger(f"{__name__}.CircuitBreaker.{name}")

    async def call(self, func: Callable[[], Awaitable[Any]]) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Async function to execute

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: When circuit is open
        """
        self.total_requests += 1

        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is open")

        elif self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.config.half_open_max_calls:
                raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' half-open limit exceeded")

        try:
            # Execute function
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1

            result = await func()

            # Success
            await self._on_success()
            return result

        except Exception as e:
            # Failure
            await self._on_failure(e)
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset"""
        if self.last_failure_time is None:
            return True

        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.config.timeout

    def _transition_to_half_open(self):
        """Transition circuit to half-open state"""
        self.logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        self.state_change_time = datetime.now()

    async def _on_success(self):
        """Handle successful request"""
        self.last_success_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        else:
            # Reset failure count on success in closed state
            self.failure_count = 0

    async def _on_failure(self, error: Exception):
        """Handle failed request"""
        self.failed_requests += 1
        self.last_failure_time = datetime.now()
        self.failure_count += 1

        if self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._transition_to_open()

    def _transition_to_closed(self):
        """Transition circuit to closed state"""
        self.logger.info(f"Circuit breaker '{self.name}' transitioning to CLOSED")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.state_change_time = datetime.now()

    def _transition_to_open(self):
        """Transition circuit to open state"""
        self.logger.warning(f"Circuit breaker '{self.name}' transitioning to OPEN")
        self.state = CircuitState.OPEN
        self.success_count = 0
        self.state_change_time = datetime.now()

    def get_stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics"""
        return CircuitBreakerStats(
            state=self.state,
            failure_count=self.failure_count,
            success_count=self.success_count,
            last_failure_time=self.last_failure_time,
            last_success_time=self.last_success_time,
            total_requests=self.total_requests,
            failed_requests=self.failed_requests,
            state_change_time=self.state_change_time
        )


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


class RetryManager:
    """
    Advanced retry manager with circuit breakers and timeout handling.

    Features:
    - Multiple retry strategies (fixed, exponential, linear, random)
    - Circuit breaker protection
    - Configurable timeout handling
    - Detailed retry statistics
    - Conditional retry based on error types and status codes
    - Jitter to prevent thundering herd
    """

    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_stats: Dict[str, List[RetryAttempt]] = {}
        self.global_stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'retried_calls': 0,
            'circuit_breaker_trips': 0
        }

        self.logger = logging.getLogger(f"{__name__}.RetryManager")

    def get_or_create_circuit_breaker(self, name: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Get existing or create new circuit breaker"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        return self.circuit_breakers[name]

    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for retry attempt"""
        if config.strategy == RetryStrategy.FIXED:
            delay = config.base_delay

        elif config.strategy == RetryStrategy.EXPONENTIAL:
            delay = config.base_delay * (config.backoff_multiplier ** (attempt - 1))

        elif config.strategy == RetryStrategy.LINEAR:
            delay = config.base_delay * attempt

        elif config.strategy == RetryStrategy.RANDOM:
            delay = random.uniform(config.base_delay, config.max_delay)

        else:
            delay = config.base_delay

        # Apply maximum delay limit
        delay = min(delay, config.max_delay)

        # Add jitter if enabled
        if config.jitter:
            jitter_amount = delay * config.jitter_range
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay + jitter)

        return delay

    def _should_retry(self, error: Exception, status_code: Optional[int], config: RetryConfig) -> bool:
        """Determine if request should be retried"""
        # Check exception types
        if any(isinstance(error, exc_type) for exc_type in config.retry_on_exceptions):
            return True

        # Check timeout errors
        if config.retry_on_timeout and isinstance(error, (asyncio.TimeoutError, aiohttp.ClientTimeout)):
            return True

        # Check connection errors
        if config.retry_on_connection_error and isinstance(error, (
            aiohttp.ClientConnectionError,
            ConnectionError,
            aiohttp.ClientConnectorError
        )):
            return True

        # Check status codes
        if status_code and status_code in config.retry_on_status_codes:
            return True

        return False

    async def retry_call(self,
                        func: Callable[[], Awaitable[Any]],
                        config: RetryConfig,
                        circuit_breaker_name: Optional[str] = None,
                        circuit_breaker_config: Optional[CircuitBreakerConfig] = None) -> Any:
        """
        Execute function with retry logic and optional circuit breaker.

        Args:
            func: Async function to execute
            config: Retry configuration
            circuit_breaker_name: Optional circuit breaker name
            circuit_breaker_config: Circuit breaker configuration

        Returns:
            Function result

        Raises:
            Exception: Last exception if all retries failed
        """
        self.global_stats['total_calls'] += 1
        call_id = f"call_{int(time.time() * 1000)}"
        attempts = []

        # Get circuit breaker if specified
        circuit_breaker = None
        if circuit_breaker_name:
            cb_config = circuit_breaker_config or CircuitBreakerConfig()
            circuit_breaker = self.get_or_create_circuit_breaker(circuit_breaker_name, cb_config)

        last_exception = None
        for attempt in range(1, config.max_attempts + 1):
            start_time = time.time()

            try:
                # Execute through circuit breaker if available
                if circuit_breaker:
                    result = await circuit_breaker.call(func)
                else:
                    result = await func()

                # Success
                response_time = time.time() - start_time
                attempt_info = RetryAttempt(
                    attempt=attempt,
                    timestamp=datetime.now(),
                    error=None,
                    response_time=response_time
                )
                attempts.append(attempt_info)

                self.retry_stats[call_id] = attempts
                self.global_stats['successful_calls'] += 1

                if attempt > 1:
                    self.global_stats['retried_calls'] += 1
                    self.logger.info(f"Retry successful on attempt {attempt}")

                return result

            except CircuitBreakerOpenError as e:
                self.global_stats['circuit_breaker_trips'] += 1
                self.logger.warning(f"Circuit breaker blocked call: {e}")
                raise

            except Exception as e:
                response_time = time.time() - start_time
                last_exception = e

                # Extract status code if available
                status_code = None
                if hasattr(e, 'status'):
                    status_code = e.status
                elif hasattr(e, 'response') and hasattr(e.response, 'status'):
                    status_code = e.response.status

                attempt_info = RetryAttempt(
                    attempt=attempt,
                    timestamp=datetime.now(),
                    error=e,
                    response_time=response_time,
                    status_code=status_code
                )
                attempts.append(attempt_info)

                self.logger.warning(f"Attempt {attempt} failed: {e}")

                # Check if we should retry
                if attempt < config.max_attempts and self._should_retry(e, status_code, config):
                    delay = self._calculate_delay(attempt, config)
                    self.logger.info(f"Retrying in {delay:.2f} seconds (attempt {attempt + 1}/{config.max_attempts})")
                    await asyncio.sleep(delay)
                else:
                    break

        # All attempts failed
        self.retry_stats[call_id] = attempts
        self.global_stats['failed_calls'] += 1
        self.global_stats['retried_calls'] += 1

        self.logger.error(f"All {config.max_attempts} attempts failed")
        raise last_exception

    def retry_with_config(self, config: RetryConfig,
                         circuit_breaker_name: Optional[str] = None,
                         circuit_breaker_config: Optional[CircuitBreakerConfig] = None):
        """
        Decorator for retrying functions with specified configuration.

        Args:
            config: Retry configuration
            circuit_breaker_name: Optional circuit breaker name
            circuit_breaker_config: Circuit breaker configuration

        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                async def call_func():
                    return await func(*args, **kwargs)

                return await self.retry_call(
                    call_func,
                    config,
                    circuit_breaker_name,
                    circuit_breaker_config
                )
            return wrapper
        return decorator

    async def timeout_call(self, func: Callable[[], Awaitable[Any]], timeout: float) -> Any:
        """
        Execute function with timeout.

        Args:
            func: Async function to execute
            timeout: Timeout in seconds

        Returns:
            Function result

        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        try:
            return await asyncio.wait_for(func(), timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.warning(f"Function timed out after {timeout} seconds")
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """Get retry manager statistics"""
        circuit_breaker_stats = {}
        for name, cb in self.circuit_breakers.items():
            circuit_breaker_stats[name] = cb.get_stats()

        recent_attempts = sum(
            len(attempts) for attempts in self.retry_stats.values()
        )

        return {
            'global_stats': self.global_stats,
            'circuit_breakers': len(self.circuit_breakers),
            'recent_retry_attempts': recent_attempts,
            'circuit_breaker_details': circuit_breaker_stats
        }

    def get_retry_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent retry history"""
        history = []

        for call_id, attempts in list(self.retry_stats.items())[-limit:]:
            call_info = {
                'call_id': call_id,
                'total_attempts': len(attempts),
                'success': attempts[-1].error is None,
                'total_time': sum(a.response_time for a in attempts),
                'attempts': [
                    {
                        'attempt': a.attempt,
                        'timestamp': a.timestamp.isoformat(),
                        'success': a.error is None,
                        'response_time': a.response_time,
                        'status_code': a.status_code,
                        'error': str(a.error) if a.error else None
                    }
                    for a in attempts
                ]
            }
            history.append(call_info)

        return history


# Global retry manager instance
_global_retry_manager: Optional[RetryManager] = None


def get_retry_manager() -> RetryManager:
    """Get the global retry manager instance"""
    global _global_retry_manager
    if _global_retry_manager is None:
        _global_retry_manager = RetryManager()
    return _global_retry_manager


def set_retry_manager(manager: RetryManager):
    """Set the global retry manager instance"""
    global _global_retry_manager
    _global_retry_manager = manager


# Convenience decorators
def retry_exponential(max_attempts: int = 3,
                     base_delay: float = 1.0,
                     max_delay: float = 60.0,
                     circuit_breaker: Optional[str] = None):
    """Convenience decorator for exponential retry"""
    config = RetryConfig(
        max_attempts=max_attempts,
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay=base_delay,
        max_delay=max_delay
    )
    return get_retry_manager().retry_with_config(config, circuit_breaker)


def retry_fixed(max_attempts: int = 3,
               delay: float = 1.0,
               circuit_breaker: Optional[str] = None):
    """Convenience decorator for fixed delay retry"""
    config = RetryConfig(
        max_attempts=max_attempts,
        strategy=RetryStrategy.FIXED,
        base_delay=delay,
        max_delay=delay
    )
    return get_retry_manager().retry_with_config(config, circuit_breaker)


def timeout(seconds: float):
    """Convenience decorator for timeout"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async def call_func():
                return await func(*args, **kwargs)

            return await get_retry_manager().timeout_call(call_func, seconds)
        return wrapper
    return decorator