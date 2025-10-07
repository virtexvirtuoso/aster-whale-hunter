"""
Simple Threshold Strategy - Example Implementation

This is a basic example strategy that demonstrates how to implement
the BaseWhaleStrategy interface. It detects whale trades based on a
simple USD value threshold.

This is meant as a learning example - you should implement more sophisticated
detection logic for production use.
"""

from typing import Dict, Any, Optional
import time
from .base_strategy import BaseWhaleStrategy, WhaleSignal


class SimpleThresholdStrategy(BaseWhaleStrategy):
    """
    Simple example strategy that detects whale trades based on USD value threshold.

    Configuration:
        min_trade_value: Minimum trade value in USD to trigger alert (default: 100000)
        confidence_threshold: Minimum confidence score (default: 0.7)
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.min_trade_value = config.get('min_trade_value', 100000)
        self.confidence_threshold = config.get('confidence_threshold', 0.7)

    async def analyze(self, market_data: Dict[str, Any]) -> Optional[WhaleSignal]:
        """
        Analyze market data for large trades.

        Args:
            market_data: Market data containing:
                - symbol: Trading pair (e.g., "BTCUSDT")
                - trades: List of recent trades
                - Each trade: {'price': float, 'quantity': float, 'side': str, 'timestamp': float}

        Returns:
            WhaleSignal if large trade detected, None otherwise
        """
        symbol = market_data.get('symbol')
        trades = market_data.get('trades', [])

        if not symbol or not trades:
            return None

        # Analyze recent trades for whale activity
        for trade in trades:
            trade_value = trade.get('price', 0) * trade.get('quantity', 0)

            if trade_value >= self.min_trade_value:
                # Calculate confidence based on trade size
                # Simple linear scaling: $100K = 0.7, $1M+ = 1.0
                confidence = min(1.0, 0.7 + (trade_value / 3000000))

                if confidence >= self.confidence_threshold:
                    signal_type = "WHALE_BUY" if trade.get('side') == 'buy' else "WHALE_SELL"

                    return WhaleSignal(
                        symbol=symbol,
                        confidence=confidence,
                        signal_type=signal_type,
                        value=trade_value,
                        metadata={
                            'price': trade.get('price'),
                            'quantity': trade.get('quantity'),
                            'side': trade.get('side'),
                            'strategy': self.name
                        },
                        timestamp=trade.get('timestamp', time.time())
                    )

        return None

    def get_required_data_fields(self) -> list[str]:
        """This strategy requires trade data"""
        return ['symbol', 'trades']


# Example configuration
EXAMPLE_CONFIG = {
    'enabled': True,
    'min_trade_value': 100000,  # $100K minimum
    'confidence_threshold': 0.7
}
