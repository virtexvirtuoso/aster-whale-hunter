"""
AsterDex API Data Models
Defines data structures for market data, trades, and order book information.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class MarketTicker:
    """Market ticker data structure."""
    symbol: str
    price: Decimal
    price_change: Decimal
    price_change_percent: Decimal
    weighted_avg_price: Decimal
    prev_close_price: Decimal
    last_price: Decimal
    bid_price: Decimal
    ask_price: Decimal
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    volume: Decimal
    quote_volume: Decimal
    open_time: datetime
    close_time: datetime
    count: int
    timestamp: datetime

    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> 'MarketTicker':
        """Create MarketTicker from API response data."""
        return cls(
            symbol=data['symbol'],
            price=Decimal(str(data.get('lastPrice', '0'))),
            price_change=Decimal(str(data.get('priceChange', '0'))),
            price_change_percent=Decimal(str(data.get('priceChangePercent', '0'))),
            weighted_avg_price=Decimal(str(data.get('weightedAvgPrice', '0'))),
            prev_close_price=Decimal(str(data.get('prevClosePrice', '0'))),
            last_price=Decimal(str(data.get('lastPrice', '0'))),
            bid_price=Decimal(str(data.get('bidPrice', '0'))),
            ask_price=Decimal(str(data.get('askPrice', '0'))),
            open_price=Decimal(str(data.get('openPrice', '0'))),
            high_price=Decimal(str(data.get('highPrice', '0'))),
            low_price=Decimal(str(data.get('lowPrice', '0'))),
            volume=Decimal(str(data.get('volume', '0'))),
            quote_volume=Decimal(str(data.get('quoteVolume', '0'))),
            open_time=datetime.fromtimestamp(data.get('openTime', 0) / 1000),
            close_time=datetime.fromtimestamp(data.get('closeTime', 0) / 1000),
            count=data.get('count', 0),
            timestamp=datetime.utcnow()
        )


@dataclass
class OrderBookEntry:
    """Order book entry (bid/ask)."""
    price: Decimal
    quantity: Decimal

    @classmethod
    def from_list(cls, data: List[str]) -> 'OrderBookEntry':
        """Create from list format [price, quantity]."""
        return cls(
            price=Decimal(data[0]),
            quantity=Decimal(data[1])
        )


@dataclass
class OrderBook:
    """Order book data structure."""
    symbol: str
    bids: List[OrderBookEntry]
    asks: List[OrderBookEntry]
    last_update_id: int
    timestamp: datetime

    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> 'OrderBook':
        """Create OrderBook from API response data."""
        return cls(
            symbol=data.get('symbol', ''),
            bids=[OrderBookEntry.from_list(bid) for bid in data.get('bids', [])],
            asks=[OrderBookEntry.from_list(ask) for ask in data.get('asks', [])],
            last_update_id=data.get('lastUpdateId', 0),
            timestamp=datetime.utcnow()
        )

    def get_best_bid(self) -> Optional[OrderBookEntry]:
        """Get best bid price."""
        return self.bids[0] if self.bids else None

    def get_best_ask(self) -> Optional[OrderBookEntry]:
        """Get best ask price."""
        return self.asks[0] if self.asks else None

    def get_spread(self) -> Optional[Decimal]:
        """Get bid-ask spread."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid and best_ask:
            return best_ask.price - best_bid.price
        return None

    def get_spread_percentage(self) -> Optional[Decimal]:
        """Get bid-ask spread as percentage of mid price."""
        spread = self.get_spread()
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if spread and best_bid and best_ask:
            mid_price = (best_bid.price + best_ask.price) / 2
            return (spread / mid_price) * 100
        return None


@dataclass
class Trade:
    """Individual trade data structure."""
    id: int
    symbol: str
    price: Decimal
    quantity: Decimal
    quote_quantity: Decimal
    timestamp: datetime
    is_buyer_maker: bool
    side: OrderSide

    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> 'Trade':
        """Create Trade from API response data."""
        return cls(
            id=data.get('id', 0),
            symbol=data.get('symbol', ''),
            price=Decimal(str(data.get('price', '0'))),
            quantity=Decimal(str(data.get('qty', '0'))),
            quote_quantity=Decimal(str(data.get('quoteQty', '0'))),
            timestamp=datetime.fromtimestamp(data.get('time', 0) / 1000),
            is_buyer_maker=data.get('isBuyerMaker', False),
            side=OrderSide.BUY if not data.get('isBuyerMaker', False) else OrderSide.SELL
        )

    def get_trade_value_usd(self) -> Decimal:
        """Get trade value in USD (assuming quote is in USD or USDT)."""
        return self.quote_quantity

    def is_whale_trade(self, threshold_usd: Decimal = Decimal('100000')) -> bool:
        """Check if this trade qualifies as a whale trade."""
        return self.get_trade_value_usd() >= threshold_usd


@dataclass
class Kline:
    """Candlestick/Kline data structure."""
    symbol: str
    open_time: datetime
    close_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    quote_volume: Decimal
    trades_count: int
    taker_buy_base_volume: Decimal
    taker_buy_quote_volume: Decimal

    @classmethod
    def from_api_data(cls, data: List[Any], symbol: str = '') -> 'Kline':
        """Create Kline from API response data (array format)."""
        return cls(
            symbol=symbol,
            open_time=datetime.fromtimestamp(data[0] / 1000),
            close_time=datetime.fromtimestamp(data[6] / 1000),
            open_price=Decimal(str(data[1])),
            high_price=Decimal(str(data[2])),
            low_price=Decimal(str(data[3])),
            close_price=Decimal(str(data[4])),
            volume=Decimal(str(data[5])),
            quote_volume=Decimal(str(data[7])),
            trades_count=int(data[8]),
            taker_buy_base_volume=Decimal(str(data[9])),
            taker_buy_quote_volume=Decimal(str(data[10]))
        )

    def get_price_change_percent(self) -> Decimal:
        """Get price change percentage."""
        if self.open_price == 0:
            return Decimal('0')
        return ((self.close_price - self.open_price) / self.open_price) * 100

    def get_body_size(self) -> Decimal:
        """Get candle body size (abs difference between open and close)."""
        return abs(self.close_price - self.open_price)

    def get_wick_size(self) -> Dict[str, Decimal]:
        """Get upper and lower wick sizes."""
        body_high = max(self.open_price, self.close_price)
        body_low = min(self.open_price, self.close_price)
        
        return {
            'upper_wick': self.high_price - body_high,
            'lower_wick': body_low - self.low_price
        }

    def is_bullish(self) -> bool:
        """Check if candle is bullish (close > open)."""
        return self.close_price > self.open_price


@dataclass
class ExchangeInfo:
    """Exchange information structure."""
    timezone: str
    server_time: datetime
    futures_type: str
    rate_limits: List[Dict[str, Any]]
    symbols: List[Dict[str, Any]]

    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> 'ExchangeInfo':
        """Create ExchangeInfo from API response data."""
        return cls(
            timezone=data.get('timezone', 'UTC'),
            server_time=datetime.fromtimestamp(data.get('serverTime', 0) / 1000),
            futures_type=data.get('futuresType', 'U_MARGINED'),
            rate_limits=data.get('rateLimits', []),
            symbols=data.get('symbols', [])
        )

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get information for a specific symbol."""
        for sym_info in self.symbols:
            if sym_info.get('symbol') == symbol:
                return sym_info
        return None

    def get_active_symbols(self) -> List[str]:
        """Get list of active trading symbols."""
        active_symbols = []
        for sym_info in self.symbols:
            if sym_info.get('status') == 'TRADING':
                active_symbols.append(sym_info.get('symbol'))
        return active_symbols


@dataclass
class PremiumIndex:
    """Mark Price and Funding Rate snapshot (premium index)."""
    symbol: str
    mark_price: Decimal
    index_price: Decimal
    estimated_settle_price: Decimal
    last_funding_rate: Decimal
    next_funding_time: datetime
    interest_rate: Decimal
    time: datetime

    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> 'PremiumIndex':
        return cls(
            symbol=data.get('symbol', ''),
            mark_price=Decimal(str(data.get('markPrice', '0'))),
            index_price=Decimal(str(data.get('indexPrice', '0'))),
            estimated_settle_price=Decimal(str(data.get('estimatedSettlePrice', '0'))),
            last_funding_rate=Decimal(str(data.get('lastFundingRate', '0'))),
            next_funding_time=datetime.fromtimestamp(data.get('nextFundingTime', 0) / 1000),
            interest_rate=Decimal(str(data.get('interestRate', '0'))),
            time=datetime.fromtimestamp(data.get('time', 0) / 1000)
        )


@dataclass
class FundingRateEntry:
    """Funding rate history entry."""
    symbol: str
    funding_rate: Decimal
    funding_time: datetime

    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> 'FundingRateEntry':
        return cls(
            symbol=data.get('symbol', ''),
            funding_rate=Decimal(str(data.get('fundingRate', '0'))),
            funding_time=datetime.fromtimestamp(data.get('fundingTime', 0) / 1000)
        )


@dataclass
class AggTrade:
    """Compressed/Aggregate trade item."""
    aggregate_trade_id: int
    price: Decimal
    quantity: Decimal
    first_trade_id: int
    last_trade_id: int
    timestamp: datetime
    is_buyer_maker: bool

    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> 'AggTrade':
        return cls(
            aggregate_trade_id=int(data.get('a', 0)),
            price=Decimal(str(data.get('p', '0'))),
            quantity=Decimal(str(data.get('q', '0'))),
            first_trade_id=int(data.get('f', 0)),
            last_trade_id=int(data.get('l', 0)),
            timestamp=datetime.fromtimestamp(data.get('T', 0) / 1000),
            is_buyer_maker=bool(data.get('m', False))
        )


@dataclass
class MarketAnalysis:
    """Market analysis data structure for whale detection."""
    symbol: str
    timestamp: datetime
    
    # Price metrics
    current_price: Decimal
    price_change_24h: Decimal
    price_change_percent_24h: Decimal
    
    # Volume metrics
    current_volume: Decimal
    volume_24h: Decimal
    volume_change_percent: Decimal
    avg_volume_24h: Decimal
    
    # Order book metrics
    bid_ask_spread: Optional[Decimal]
    order_book_depth: Dict[str, Decimal]
    
    # Whale activity indicators
    large_trades_count: int
    whale_trade_volume: Decimal
    whale_trade_percentage: Decimal
    
    # Market anomalies
    anomaly_score: Decimal
    manipulation_indicators: Dict[str, float]
    
    # Technical indicators (optional)
    rsi: Optional[float] = None
    ma_20: Optional[Decimal] = None
    ma_50: Optional[Decimal] = None
    bollinger_upper: Optional[Decimal] = None
    bollinger_lower: Optional[Decimal] = None


@dataclass
class WhaleAlert:
    """Whale alert data structure."""
    alert_id: str
    alert_type: str
    severity: AlertSeverity
    symbol: str
    exchange: str
    timestamp: datetime
    
    # Alert-specific data
    trade_data: Optional[Trade] = None
    market_analysis: Optional[MarketAnalysis] = None
    
    # Alert metadata
    confidence_score: float
    message: str
    additional_data: Dict[str, Any]
    
    # Alert state
    is_sent: bool = False
    delivery_channels: List[str] = None
    
    def __post_init__(self):
        if self.delivery_channels is None:
            self.delivery_channels = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert whale alert to dictionary for storage/transmission."""
        return {
            'alert_id': self.alert_id,
            'alert_type': self.alert_type,
            'severity': self.severity.value,
            'symbol': self.symbol,
            'exchange': self.exchange,
            'timestamp': self.timestamp.isoformat(),
            'trade_data': self.trade_data.__dict__ if self.trade_data else None,
            'confidence_score': self.confidence_score,
            'message': self.message,
            'additional_data': self.additional_data,
            'is_sent': self.is_sent,
            'delivery_channels': self.delivery_channels
        }