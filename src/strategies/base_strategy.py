"""
Base Strategy Interface for Whale Detection

This module provides the abstract base class that all detection strategies must implement.
Create your own custom strategies by inheriting from BaseWhaleStrategy.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class WhaleSignal:
    """Represents a whale detection signal"""
    symbol: str
    confidence: float  # 0.0 to 1.0
    signal_type: str  # e.g., "WHALE_BUY", "WHALE_SELL", "ORDERBOOK_IMBALANCE"
    value: float  # Trade value in USD
    metadata: Dict[str, Any]  # Additional strategy-specific data
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary for logging/alerting"""
        return {
            'symbol': self.symbol,
            'confidence': self.confidence,
            'signal_type': self.signal_type,
            'value': self.value,
            'metadata': self.metadata,
            'timestamp': self.timestamp
        }


class BaseWhaleStrategy(ABC):
    """
    Abstract base class for all whale detection strategies.

    Implement this interface to create custom detection strategies.

    Example:
        class MyCustomStrategy(BaseWhaleStrategy):
            def __init__(self, config: Dict[str, Any]):
                super().__init__(config)
                self.my_threshold = config.get('my_threshold', 1000000)

            async def analyze(self, market_data: Dict[str, Any]) -> Optional[WhaleSignal]:
                # Your detection logic here
                if self._is_whale_detected(market_data):
                    return WhaleSignal(
                        symbol=market_data['symbol'],
                        confidence=0.85,
                        signal_type='MY_CUSTOM_SIGNAL',
                        value=market_data['trade_value'],
                        metadata={'custom_field': 'value'},
                        timestamp=market_data['timestamp']
                    )
                return None
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the strategy with configuration.

        Args:
            config: Strategy configuration dictionary
        """
        self.config = config
        self.name = self.__class__.__name__
        self.enabled = config.get('enabled', True)

    @abstractmethod
    async def analyze(self, market_data: Dict[str, Any]) -> Optional[WhaleSignal]:
        """
        Analyze market data and return a whale signal if detected.

        Args:
            market_data: Dictionary containing market data with keys like:
                - symbol: str
                - price: float
                - volume: float
                - timestamp: float
                - trades: List[Dict] (recent trades)
                - orderbook: Dict (current orderbook snapshot)
                - ... (additional exchange-specific data)

        Returns:
            WhaleSignal if whale activity detected, None otherwise
        """
        pass

    @abstractmethod
    def get_required_data_fields(self) -> list[str]:
        """
        Return list of required market data fields for this strategy.

        Returns:
            List of field names this strategy needs (e.g., ['trades', 'orderbook'])
        """
        pass

    def is_enabled(self) -> bool:
        """Check if strategy is enabled"""
        return self.enabled

    def get_name(self) -> str:
        """Get strategy name"""
        return self.name
