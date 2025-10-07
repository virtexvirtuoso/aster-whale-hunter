"""
AsterDex REST API Client
Comprehensive REST API client with rate limiting, caching, and error handling.
"""

import asyncio
import aiohttp
import logging
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlencode
import json

from .models import MarketTicker, OrderBook, Trade, Kline, ExchangeInfo, PremiumIndex, FundingRateEntry, AggTrade
from ..config.asterdex import ASTERDEX_FAPI_BASE_URL


class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, requests_per_minute: int = 2400, burst_limit: int = 100):
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.requests = []
        self.burst_tokens = burst_limit
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a request."""
        async with self._lock:
            now = time.time()
            
            # Refill burst tokens
            time_passed = now - self.last_refill
            if time_passed >= 60:  # Refill every minute
                self.burst_tokens = self.burst_limit
                self.last_refill = now
                self.requests.clear()
            
            # Remove old requests (older than 1 minute)
            cutoff = now - 60
            self.requests = [req_time for req_time in self.requests if req_time > cutoff]
            
            # Check if we can make a request
            if len(self.requests) >= self.requests_per_minute:
                # Wait until oldest request is more than 1 minute old
                wait_time = 60 - (now - self.requests[0])
                await asyncio.sleep(max(0, wait_time))
                return await self.acquire()
            
            # Use burst token if available
            if self.burst_tokens > 0:
                self.burst_tokens -= 1
            
            self.requests.append(now)


class APICache:
    """Simple in-memory cache for API responses."""
    
    def __init__(self, default_ttl: int = 300):
        self.default_ttl = default_ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        async with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                if time.time() < entry['expires_at']:
                    return entry['data']
                else:
                    del self.cache[key]
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set cached value."""
        async with self._lock:
            ttl = ttl or self.default_ttl
            self.cache[key] = {
                'data': value,
                'expires_at': time.time() + ttl,
                'created_at': time.time()
            }
    
    async def clear(self):
        """Clear all cached entries."""
        async with self._lock:
            self.cache.clear()
    
    async def cleanup_expired(self):
        """Remove expired entries."""
        async with self._lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self.cache.items()
                if now >= entry['expires_at']
            ]
            for key in expired_keys:
                del self.cache[key]


class AsterDexAPIClient:
    """
    AsterDex REST API Client with comprehensive features:
    - Rate limiting and retry logic
    - Response caching
    - Error handling and logging
    - Data model integration
    - Connection pooling
    """
    
    BASE_URL = ASTERDEX_FAPI_BASE_URL
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        requests_per_minute: int = 2400,
        cache_ttl: int = 30,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        enable_cache: bool = True
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_cache = enable_cache
        
        # Rate limiting
        self.rate_limiter = RateLimiter(requests_per_minute)
        
        # Caching
        self.cache = APICache(cache_ttl) if enable_cache else None
        
        # HTTP session
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.stats = {
            'requests_made': 0,
            'requests_cached': 0,
            'requests_failed': 0,
            'rate_limit_hits': 0,
            'start_time': time.time()
        }
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def initialize(self):
        """Initialize the HTTP session."""
        if not self.session:
            connector = aiohttp.TCPConnector(
                limit=100,  # Connection pool limit
                limit_per_host=50,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'AsterDex-WhaleBot/1.0',
                    'Content-Type': 'application/json'
                }
            )
            
            self.logger.info("AsterDex API client initialized")
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
            self.logger.info("AsterDex API client closed")
    
    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC SHA256 signature for authenticated requests."""
        if not self.api_secret:
            raise ValueError("API secret is required for signed requests")
        
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _prepare_signed_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare parameters for signed requests."""
        if not self.api_key:
            raise ValueError("API key is required for signed requests")
        
        # Add timestamp
        params['timestamp'] = int(time.time() * 1000)
        
        # Create query string
        query_string = urlencode(sorted(params.items()))
        
        # Generate signature
        signature = self._generate_signature(query_string)
        params['signature'] = signature
        
        return params
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with rate limiting, caching, and error handling."""
        if not self.session:
            await self.initialize()
        
        # Check cache first
        if cache_key and self.cache:
            cached_response = await self.cache.get(cache_key)
            if cached_response is not None:
                self.stats['requests_cached'] += 1
                self.logger.debug(f"Cache hit for {cache_key}")
                return cached_response
        
        # Rate limiting
        await self.rate_limiter.acquire()
        
        # Prepare parameters
        params = params or {}
        if signed:
            params = self._prepare_signed_params(params)
        
        # Prepare headers
        headers = {}
        if signed and self.api_key:
            headers['X-MBX-APIKEY'] = self.api_key
        
        # Build URL
        url = f"{self.BASE_URL}{endpoint}"
        
        # Retry logic
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"Making request to {url} (attempt {attempt + 1})")
                
                async with self.session.request(
                    method,
                    url,
                    params=params,
                    headers=headers
                ) as response:
                    self.stats['requests_made'] += 1
                    
                    # Handle rate limiting
                    if response.status == 429:
                        self.stats['rate_limit_hits'] += 1
                        retry_after = int(response.headers.get('Retry-After', 60))
                        self.logger.warning(f"Rate limited, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    # Handle other errors
                    if response.status >= 400:
                        error_text = await response.text()
                        self.logger.error(f"API error {response.status}: {error_text}")
                        
                        if response.status >= 500 and attempt < self.max_retries:
                            await asyncio.sleep(self.retry_delay * (2 ** attempt))
                            continue
                        
                        response.raise_for_status()
                    
                    # Parse response
                    data = await response.json()
                    
                    # Cache successful response
                    if cache_key and self.cache:
                        await self.cache.set(cache_key, data, cache_ttl)
                        self.logger.debug(f"Cached response for {cache_key}")
                    
                    return data
            
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"Request failed, retrying in {wait_time}s: {str(e)}")
                    await asyncio.sleep(wait_time)
                else:
                    self.stats['requests_failed'] += 1
                    self.logger.error(f"Request failed after {self.max_retries} retries: {str(e)}")
        
        # All retries exhausted
        raise last_exception or Exception("Request failed")
    
    # Public API Methods
    
    async def ping(self) -> Dict[str, Any]:
        """Test connectivity to the REST API."""
        return await self._make_request('GET', '/fapi/v1/ping')
    
    async def get_server_time(self) -> datetime:
        """Get current server time."""
        response = await self._make_request(
            'GET', 
            '/fapi/v1/time',
            cache_key='server_time',
            cache_ttl=60
        )
        return datetime.fromtimestamp(response['serverTime'] / 1000)
    
    async def get_exchange_info(self) -> ExchangeInfo:
        """Get current exchange trading rules and symbol information."""
        data = await self._make_request(
            'GET',
            '/fapi/v1/exchangeInfo',
            cache_key='exchange_info',
            cache_ttl=3600  # Cache for 1 hour
        )
        return ExchangeInfo.from_api_data(data)
    
    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        """Get order book (market depth) for a symbol."""
        params = {'symbol': symbol, 'limit': limit}
        cache_key = f"depth_{symbol}_{limit}"
        
        data = await self._make_request(
            'GET',
            '/fapi/v1/depth',
            params=params,
            cache_key=cache_key,
            cache_ttl=5  # Very short cache for order book
        )
        
        return OrderBook.from_api_data({**data, 'symbol': symbol})
    
    async def get_recent_trades(self, symbol: str, limit: int = 500) -> List[Trade]:
        """Get recent trades for a symbol."""
        params = {'symbol': symbol, 'limit': limit}
        
        data = await self._make_request(
            'GET',
            '/fapi/v1/trades',
            params=params,
            cache_key=f"trades_{symbol}_{limit}",
            cache_ttl=10  # Short cache for trades
        )
        
        return [Trade.from_api_data({**trade, 'symbol': symbol}) for trade in data]
    
    async def get_historical_trades(
        self,
        symbol: str,
        limit: int = 500,
        from_id: Optional[int] = None
    ) -> List[Trade]:
        """Get historical trades (requires API key)."""
        params = {'symbol': symbol, 'limit': limit}
        if from_id is not None:
            params['fromId'] = from_id
        
        data = await self._make_request(
            'GET',
            '/fapi/v1/historicalTrades',
            params=params,
            signed=True
        )
        
        return [Trade.from_api_data({**trade, 'symbol': symbol}) for trade in data]
    
    async def get_klines(
        self,
        symbol: str,
        interval: str = '1m',
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500
    ) -> List[Kline]:
        """Get candlestick/kline data for a symbol."""
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        cache_key = f"klines_{symbol}_{interval}_{limit}"
        
        data = await self._make_request(
            'GET',
            '/fapi/v1/klines',
            params=params,
            cache_key=cache_key,
            cache_ttl=60  # Cache klines for 1 minute
        )
        
        return [Kline.from_api_data(kline_data, symbol) for kline_data in data]
    
    async def get_ticker_24hr(self, symbol: Optional[str] = None) -> Union[MarketTicker, List[MarketTicker]]:
        """Get 24hr ticker price change statistics."""
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        cache_key = f"ticker_24hr_{symbol or 'all'}"
        
        data = await self._make_request(
            'GET',
            '/fapi/v1/ticker/24hr',
            params=params,
            cache_key=cache_key,
            cache_ttl=30  # Cache for 30 seconds
        )
        
        if isinstance(data, list):
            return [MarketTicker.from_api_data(ticker) for ticker in data]
        else:
            return MarketTicker.from_api_data(data)
    
    async def get_ticker_price(self, symbol: Optional[str] = None) -> Union[Dict[str, Decimal], Decimal]:
        """Get current price for a symbol or all symbols."""
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        cache_key = f"ticker_price_{symbol or 'all'}"
        
        data = await self._make_request(
            'GET',
            '/fapi/v1/ticker/price',
            params=params,
            cache_key=cache_key,
            cache_ttl=5  # Very short cache for current price
        )
        
        if isinstance(data, list):
            return {item['symbol']: Decimal(item['price']) for item in data}
        else:
            return Decimal(data['price'])
    
    async def get_book_ticker(self, symbol: Optional[str] = None) -> Union[Dict, List[Dict]]:
        """Get best price/qty on the order book for a symbol or symbols."""
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        cache_key = f"book_ticker_{symbol or 'all'}"
        
        return await self._make_request(
            'GET',
            '/fapi/v1/ticker/bookTicker',
            params=params,
            cache_key=cache_key,
            cache_ttl=5
        )
    
    async def get_premium_index(self, symbol: Optional[str] = None) -> Union[PremiumIndex, List[PremiumIndex]]:
        """Get Mark Price and Funding Rate (premium index)."""
        params: Dict[str, Any] = {}
        if symbol:
            params['symbol'] = symbol
        data = await self._make_request(
            'GET',
            '/fapi/v1/premiumIndex',
            params=params,
            cache_key=f"premium_index_{symbol or 'all'}",
            cache_ttl=5
        )
        if isinstance(data, list):
            return [PremiumIndex.from_api_data(item) for item in data]
        return PremiumIndex.from_api_data(data)
    
    async def get_funding_rate_history(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100
    ) -> List[FundingRateEntry]:
        """Get funding rate history."""
        params: Dict[str, Any] = {'limit': limit}
        if symbol:
            params['symbol'] = symbol
        if start_time is not None:
            params['startTime'] = start_time
        if end_time is not None:
            params['endTime'] = end_time
        data = await self._make_request(
            'GET',
            '/fapi/v1/fundingRate',
            params=params,
            cache_key=f"funding_rate_{symbol or 'all'}_{start_time or 'na'}_{end_time or 'na'}_{limit}",
            cache_ttl=30
        )
        return [FundingRateEntry.from_api_data(item) for item in data]
    
    async def get_agg_trades(
        self,
        symbol: str,
        from_id: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500
    ) -> List[AggTrade]:
        """Get compressed/aggregate trades for a symbol."""
        params: Dict[str, Any] = {'symbol': symbol, 'limit': limit}
        if from_id is not None:
            params['fromId'] = from_id
        if start_time is not None:
            params['startTime'] = start_time
        if end_time is not None:
            params['endTime'] = end_time
        data = await self._make_request(
            'GET',
            '/fapi/v1/aggTrades',
            params=params,
            cache_key=f"agg_trades_{symbol}_{from_id or 'na'}_{start_time or 'na'}_{end_time or 'na'}_{limit}",
            cache_ttl=5
        )
        return [AggTrade.from_api_data(item) for item in data]
    
    # Batch operations
    
    async def get_multiple_tickers(self, symbols: List[str]) -> List[MarketTicker]:
        """Get 24hr ticker data for multiple symbols efficiently."""
        # Use batch request to get all tickers, then filter
        all_tickers = await self.get_ticker_24hr()
        if isinstance(all_tickers, list):
            symbol_set = set(symbols)
            return [ticker for ticker in all_tickers if ticker.symbol in symbol_set]
        return []
    
    async def get_multiple_order_books(self, symbols: List[str], limit: int = 100) -> Dict[str, OrderBook]:
        """Get order books for multiple symbols."""
        tasks = []
        for symbol in symbols:
            task = asyncio.create_task(self.get_order_book(symbol, limit))
            tasks.append((symbol, task))
        
        results = {}
        for symbol, task in tasks:
            try:
                results[symbol] = await task
            except Exception as e:
                self.logger.error(f"Failed to get order book for {symbol}: {str(e)}")
        
        return results
    
    # Statistics and health monitoring
    
    async def get_client_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        uptime = time.time() - self.stats['start_time']
        
        cache_stats = {}
        if self.cache:
            cache_stats = {
                'cache_size': len(self.cache.cache),
                'cache_hit_ratio': (
                    self.stats['requests_cached'] / 
                    max(self.stats['requests_made'] + self.stats['requests_cached'], 1) * 100
                )
            }
        
        return {
            **self.stats,
            'uptime_seconds': uptime,
            'requests_per_second': self.stats['requests_made'] / max(uptime, 1),
            'success_rate': (
                (self.stats['requests_made'] - self.stats['requests_failed']) /
                max(self.stats['requests_made'], 1) * 100
            ),
            **cache_stats
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            start_time = time.time()
            await self.ping()
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                'status': 'healthy',
                'response_time_ms': response_time,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }