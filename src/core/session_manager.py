"""
HTTP Session Manager with Proper Resource Cleanup

This module provides robust aiohttp session management with automatic cleanup,
connection pooling, and resource leak prevention for the whale hunter system.
"""

import asyncio
import aiohttp
import logging
import time
import weakref
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Union, Set
import ssl
import socket
from urllib.parse import urlparse


@dataclass
class SessionConfig:
    """Configuration for HTTP session"""
    timeout: float = 30.0
    connection_limit: int = 100
    connection_limit_per_host: int = 10
    keepalive_timeout: float = 30.0
    enable_cleanup_closed: bool = True
    connector_limit: int = 0  # 0 = unlimited
    ttl_dns_cache: int = 300
    use_dns_cache: bool = True


@dataclass
class SessionStats:
    """Statistics for a session"""
    session_id: str
    created_at: datetime
    requests_made: int = 0
    errors_count: int = 0
    last_used: Optional[datetime] = None
    is_closed: bool = False


class SessionManager:
    """
    Advanced HTTP session manager with proper resource cleanup.

    Features:
    - Automatic session cleanup and resource management
    - Connection pooling with limits
    - Session reuse and lifecycle management
    - Leak detection and prevention
    - Context manager support
    - Graceful shutdown with timeout
    """

    def __init__(self, default_config: Optional[SessionConfig] = None):
        """
        Initialize the session manager.

        Args:
            default_config: Default session configuration
        """
        self.default_config = default_config or SessionConfig()

        # Active sessions tracking
        self.sessions: Dict[str, aiohttp.ClientSession] = {}
        self.session_stats: Dict[str, SessionStats] = {}
        self.session_configs: Dict[str, SessionConfig] = {}

        # Named sessions for reuse
        self.named_sessions: Dict[str, str] = {}  # name -> session_id

        # Cleanup management
        self.cleanup_tasks: Set[asyncio.Task] = set()
        self.auto_cleanup_enabled = True
        self.cleanup_interval = 300  # 5 minutes
        self.max_idle_time = timedelta(minutes=10)

        # Shutdown management
        self.shutdown_event = asyncio.Event()
        self.shutdown_timeout = 30.0

        self.logger = logging.getLogger(f"{__name__}.SessionManager")

        # Start background cleanup if in async context
        try:
            loop = asyncio.get_running_loop()
            if self.auto_cleanup_enabled:
                self._start_background_cleanup()
        except RuntimeError:
            # No event loop running yet
            pass

    def _start_background_cleanup(self):
        """Start background cleanup task"""
        cleanup_task = asyncio.create_task(self._background_cleanup_loop())
        self.cleanup_tasks.add(cleanup_task)
        cleanup_task.add_done_callback(self.cleanup_tasks.discard)

    async def _background_cleanup_loop(self):
        """Background loop for cleaning up idle sessions"""
        while not self.shutdown_event.is_set():
            try:
                await self._cleanup_idle_sessions()
                await asyncio.wait_for(
                    self.shutdown_event.wait(),
                    timeout=self.cleanup_interval
                )
            except asyncio.TimeoutError:
                continue  # Continue cleanup loop
            except Exception as e:
                self.logger.error(f"Error in background cleanup: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _cleanup_idle_sessions(self):
        """Clean up idle sessions that haven't been used recently"""
        current_time = datetime.now()
        idle_sessions = []

        for session_id, stats in self.session_stats.items():
            if stats.is_closed:
                continue

            last_used = stats.last_used or stats.created_at
            if current_time - last_used > self.max_idle_time:
                idle_sessions.append(session_id)

        for session_id in idle_sessions:
            self.logger.info(f"Cleaning up idle session: {session_id}")
            await self.close_session(session_id)

    def create_session(self,
                      session_id: Optional[str] = None,
                      config: Optional[SessionConfig] = None,
                      name: Optional[str] = None) -> str:
        """
        Create a new HTTP session.

        Args:
            session_id: Optional custom session ID
            config: Session configuration (uses default if None)
            name: Optional name for session reuse

        Returns:
            Session ID string
        """
        if session_id is None:
            session_id = f"session_{int(time.time() * 1000)}"

        if session_id in self.sessions:
            raise ValueError(f"Session with ID '{session_id}' already exists")

        config = config or self.default_config

        # Create SSL context with proper settings
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        # Create connector with limits
        connector = aiohttp.TCPConnector(
            limit=config.connection_limit,
            limit_per_host=config.connection_limit_per_host,
            keepalive_timeout=config.keepalive_timeout,
            enable_cleanup_closed=config.enable_cleanup_closed,
            ssl=ssl_context,
            ttl_dns_cache=config.ttl_dns_cache,
            use_dns_cache=config.use_dns_cache
        )

        # Create timeout configuration
        timeout = aiohttp.ClientTimeout(total=config.timeout)

        # Create session
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            raise_for_status=False,  # Handle status manually
            auto_decompress=True,
            trust_env=True
        )

        # Store session and metadata
        self.sessions[session_id] = session
        self.session_configs[session_id] = config
        self.session_stats[session_id] = SessionStats(
            session_id=session_id,
            created_at=datetime.now()
        )

        # Store named reference if provided
        if name:
            self.named_sessions[name] = session_id

        self.logger.debug(f"Created session '{session_id}' with config: {config}")
        return session_id

    def get_session(self, session_id: str) -> Optional[aiohttp.ClientSession]:
        """
        Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            ClientSession or None if not found
        """
        session = self.sessions.get(session_id)
        if session and not session.closed:
            # Update last used time
            if session_id in self.session_stats:
                self.session_stats[session_id].last_used = datetime.now()
            return session
        return None

    def get_named_session(self, name: str) -> Optional[aiohttp.ClientSession]:
        """
        Get session by name.

        Args:
            name: Session name

        Returns:
            ClientSession or None if not found
        """
        session_id = self.named_sessions.get(name)
        if session_id:
            return self.get_session(session_id)
        return None

    def get_or_create_named_session(self,
                                   name: str,
                                   config: Optional[SessionConfig] = None) -> aiohttp.ClientSession:
        """
        Get existing named session or create new one.

        Args:
            name: Session name
            config: Configuration for new session

        Returns:
            ClientSession instance
        """
        session = self.get_named_session(name)
        if session:
            return session

        # Create new session
        session_id = self.create_session(config=config, name=name)
        return self.get_session(session_id)

    async def close_session(self, session_id: str) -> bool:
        """
        Close a specific session.

        Args:
            session_id: Session ID to close

        Returns:
            True if session was closed successfully
        """
        session = self.sessions.get(session_id)
        if not session:
            self.logger.warning(f"Session '{session_id}' not found for closure")
            return False

        try:
            # Mark as closed in stats
            if session_id in self.session_stats:
                self.session_stats[session_id].is_closed = True

            # Close session if not already closed
            if not session.closed:
                await session.close()
                self.logger.debug(f"Closed session '{session_id}'")

            # Remove from tracking
            del self.sessions[session_id]

            # Remove from named sessions
            for name, sid in list(self.named_sessions.items()):
                if sid == session_id:
                    del self.named_sessions[name]

            return True

        except Exception as e:
            self.logger.error(f"Error closing session '{session_id}': {e}")
            return False

    async def close_all_sessions(self):
        """Close all active sessions"""
        session_ids = list(self.sessions.keys())
        self.logger.info(f"Closing {len(session_ids)} active sessions")

        close_tasks = []
        for session_id in session_ids:
            task = asyncio.create_task(self.close_session(session_id))
            close_tasks.append(task)

        if close_tasks:
            results = await asyncio.gather(*close_tasks, return_exceptions=True)

            failed_closures = sum(1 for result in results if isinstance(result, Exception))
            if failed_closures > 0:
                self.logger.warning(f"{failed_closures} sessions failed to close properly")

    async def shutdown(self, timeout: Optional[float] = None):
        """
        Shutdown session manager gracefully.

        Args:
            timeout: Shutdown timeout
        """
        timeout = timeout or self.shutdown_timeout
        self.logger.info(f"Shutting down session manager (timeout: {timeout}s)")

        # Signal shutdown
        self.shutdown_event.set()

        try:
            # Cancel cleanup tasks
            for task in self.cleanup_tasks:
                if not task.done():
                    task.cancel()

            # Wait for cleanup tasks to finish
            if self.cleanup_tasks:
                await asyncio.wait_for(
                    asyncio.gather(*self.cleanup_tasks, return_exceptions=True),
                    timeout=timeout / 2
                )

            # Close all sessions
            await asyncio.wait_for(
                self.close_all_sessions(),
                timeout=timeout / 2
            )

            self.logger.info("Session manager shutdown completed")

        except asyncio.TimeoutError:
            self.logger.warning("Session manager shutdown timeout exceeded")

    @asynccontextmanager
    async def session_context(self,
                             config: Optional[SessionConfig] = None,
                             name: Optional[str] = None):
        """
        Context manager for temporary sessions with automatic cleanup.

        Args:
            config: Session configuration
            name: Optional session name

        Yields:
            ClientSession instance
        """
        session_id = None
        try:
            session_id = self.create_session(config=config, name=name)
            session = self.get_session(session_id)

            yield session

        finally:
            if session_id:
                await self.close_session(session_id)

    @asynccontextmanager
    async def request_context(self,
                             method: str,
                             url: str,
                             session_name: Optional[str] = None,
                             session_config: Optional[SessionConfig] = None,
                             **kwargs) -> aiohttp.ClientResponse:
        """
        Context manager for HTTP requests with automatic session management.

        Args:
            method: HTTP method
            url: Request URL
            session_name: Optional session name for reuse
            session_config: Session configuration
            **kwargs: Additional request parameters

        Yields:
            ClientResponse instance
        """
        if session_name:
            session = self.get_or_create_named_session(session_name, session_config)
        else:
            async with self.session_context(session_config) as session:
                async with session.request(method, url, **kwargs) as response:
                    yield response
                return

        # For named sessions, don't auto-close
        try:
            async with session.request(method, url, **kwargs) as response:
                # Update request stats
                session_id = None
                for sid, sess in self.sessions.items():
                    if sess is session:
                        session_id = sid
                        break

                if session_id and session_id in self.session_stats:
                    self.session_stats[session_id].requests_made += 1

                yield response

        except Exception as e:
            # Update error stats
            session_id = None
            for sid, sess in self.sessions.items():
                if sess is session:
                    session_id = sid
                    break

            if session_id and session_id in self.session_stats:
                self.session_stats[session_id].errors_count += 1

            raise

    def get_statistics(self) -> Dict[str, Any]:
        """Get session manager statistics"""
        active_sessions = len([s for s in self.sessions.values() if not s.closed])
        total_requests = sum(stats.requests_made for stats in self.session_stats.values())
        total_errors = sum(stats.errors_count for stats in self.session_stats.values())

        return {
            'active_sessions': active_sessions,
            'total_sessions_created': len(self.session_stats),
            'named_sessions': len(self.named_sessions),
            'total_requests': total_requests,
            'total_errors': total_errors,
            'cleanup_tasks_active': len(self.cleanup_tasks),
            'auto_cleanup_enabled': self.auto_cleanup_enabled,
            'shutdown_requested': self.shutdown_event.is_set()
        }

    def get_session_details(self) -> List[Dict[str, Any]]:
        """Get detailed information about all sessions"""
        details = []

        for session_id, stats in self.session_stats.items():
            session = self.sessions.get(session_id)

            details.append({
                'session_id': session_id,
                'created_at': stats.created_at.isoformat(),
                'last_used': stats.last_used.isoformat() if stats.last_used else None,
                'requests_made': stats.requests_made,
                'errors_count': stats.errors_count,
                'is_closed': stats.is_closed,
                'session_exists': session is not None,
                'session_closed': session.closed if session else True
            })

        return details


# Global session manager instance
_global_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance"""
    global _global_session_manager
    if _global_session_manager is None:
        _global_session_manager = SessionManager()
    return _global_session_manager


def set_session_manager(manager: SessionManager):
    """Set the global session manager instance"""
    global _global_session_manager
    _global_session_manager = manager


# Convenience functions for common use cases
async def managed_request(method: str,
                         url: str,
                         session_name: Optional[str] = None,
                         session_config: Optional[SessionConfig] = None,
                         **kwargs) -> aiohttp.ClientResponse:
    """
    Make an HTTP request with managed session.

    Args:
        method: HTTP method
        url: Request URL
        session_name: Optional session name for reuse
        session_config: Session configuration
        **kwargs: Additional request parameters

    Returns:
        ClientResponse instance
    """
    manager = get_session_manager()
    async with manager.request_context(method, url, session_name, session_config, **kwargs) as response:
        return response


async def managed_get(url: str, **kwargs) -> aiohttp.ClientResponse:
    """Convenience function for GET requests"""
    return await managed_request('GET', url, **kwargs)


async def managed_post(url: str, **kwargs) -> aiohttp.ClientResponse:
    """Convenience function for POST requests"""
    return await managed_request('POST', url, **kwargs)