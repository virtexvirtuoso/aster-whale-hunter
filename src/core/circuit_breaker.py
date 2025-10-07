"""
Circuit Breaker Pattern Implementation
Provides automatic failure detection and recovery for API endpoints.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5          # Failures before opening
    timeout_seconds: int = 60           # Time to wait before half-open
    recovery_threshold: int = 3         # Successes to close circuit
    sliding_window_size: int = 10       # Window for failure tracking


class CircuitBreaker:
    """Circuit breaker for API endpoint protection."""

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        """Initialize circuit breaker.

        Args:
            name: Identifier for this circuit breaker
            config: Configuration settings
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0

        # Sliding window for failure tracking
        self.recent_calls = []

        logger.info(f"Circuit breaker '{name}' initialized")

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: When circuit is open
        """
        if await self._should_reject_request():
            raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is OPEN")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result

        except Exception as e:
            await self._on_failure(e)
            raise

    async def _should_reject_request(self) -> bool:
        """Check if request should be rejected."""
        current_time = time.time()

        if self.state == CircuitState.CLOSED:
            return False

        elif self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if current_time - self.last_failure_time >= self.config.timeout_seconds:
                logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return False
            return True

        elif self.state == CircuitState.HALF_OPEN:
            # Allow limited requests in half-open state
            return False

    async def _on_success(self):
        """Handle successful call."""
        current_time = time.time()
        self._add_call_result(True, current_time)

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.recovery_threshold:
                logger.info(f"Circuit breaker '{self.name}' transitioning to CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0

        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)

    async def _on_failure(self, exception: Exception):
        """Handle failed call."""
        current_time = time.time()
        self._add_call_result(False, current_time)
        self.last_failure_time = current_time

        # Special-case known transient errors that should not trip the breaker
        if isinstance(exception, asyncio.CancelledError):
            logger.debug(f"Circuit breaker '{self.name}' ignoring transient CancelledError")
            return

        if self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker '{self.name}' failed in HALF_OPEN, returning to OPEN")
            self.state = CircuitState.OPEN
            self.failure_count = self.config.failure_threshold

        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            failure_rate = self._calculate_failure_rate()

            if self.failure_count >= self.config.failure_threshold or failure_rate > 0.5:
                logger.warning(f"Circuit breaker '{self.name}' transitioning to OPEN after {self.failure_count} failures")
                self.state = CircuitState.OPEN

    def _add_call_result(self, success: bool, timestamp: float):
        """Add call result to sliding window."""
        self.recent_calls.append((success, timestamp))

        # Remove old entries outside sliding window
        cutoff_time = timestamp - 60  # 1 minute window
        self.recent_calls = [(s, t) for s, t in self.recent_calls if t > cutoff_time]

        # Limit window size
        if len(self.recent_calls) > self.config.sliding_window_size:
            self.recent_calls = self.recent_calls[-self.config.sliding_window_size:]

    def _calculate_failure_rate(self) -> float:
        """Calculate current failure rate."""
        if not self.recent_calls:
            return 0.0

        failures = sum(1 for success, _ in self.recent_calls if not success)
        return failures / len(self.recent_calls)

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        failure_rate = self._calculate_failure_rate()

        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'failure_rate': failure_rate,
            'recent_calls_count': len(self.recent_calls),
            'last_failure_time': self.last_failure_time
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""

    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """Get or create circuit breaker."""
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(name, config)
        return self.breakers[name]

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {name: breaker.get_stats() for name, breaker in self.breakers.items()}


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()