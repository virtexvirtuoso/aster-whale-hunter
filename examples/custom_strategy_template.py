"""
Custom Strategy Template

Copy this file to src/strategies/ and implement your own whale detection logic.

Steps to create your custom strategy:
1. Copy this file to src/strategies/my_custom_strategy.py
2. Rename the class to something descriptive (e.g., MyCustomStrategy)
3. Implement the analyze() method with your detection logic
4. Update get_required_data_fields() to specify what data you need
5. Add your strategy configuration to config.yaml
6. Register your strategy in the detection engine
"""

from typing import Dict, Any, Optional
import time
from src.strategies.base_strategy import BaseWhaleStrategy, WhaleSignal


class CustomStrategyTemplate(BaseWhaleStrategy):
    """
    Template for creating custom whale detection strategies.

    TODO: Add a description of what your strategy detects and how it works.

    Configuration:
        param1: Description of first parameter
        param2: Description of second parameter
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # TODO: Load your strategy-specific configuration
        self.param1 = config.get('param1', 'default_value')
        self.param2 = config.get('param2', 100)

        # TODO: Initialize any state variables your strategy needs
        self.state_variable = None

    async def analyze(self, market_data: Dict[str, Any]) -> Optional[WhaleSignal]:
        """
        Analyze market data and detect whale activity.

        Args:
            market_data: Dictionary containing market data:
                - symbol: str (e.g., "BTCUSDT")
                - price: float (current price)
                - volume_24h: float (24h volume)
                - trades: List[Dict] (recent trades)
                - orderbook: Dict (current orderbook with bids/asks)
                - timestamp: float (current timestamp)
                ... (additional fields depending on exchange)

        Returns:
            WhaleSignal if whale activity detected, None otherwise
        """
        # TODO: Extract the data you need from market_data
        symbol = market_data.get('symbol')
        price = market_data.get('price')
        trades = market_data.get('trades', [])

        # TODO: Implement your detection logic here
        # Example: Check if condition is met
        whale_detected = False  # Replace with your logic

        if whale_detected:
            # TODO: Calculate confidence score (0.0 to 1.0)
            confidence = 0.85  # Replace with your calculation

            # TODO: Calculate or extract the trade value
            trade_value = 1000000  # Replace with actual value

            # TODO: Choose appropriate signal type
            # Common types: "WHALE_BUY", "WHALE_SELL", "ORDERBOOK_IMBALANCE",
            #               "VOLUME_SPIKE", "PRICE_MOMENTUM", etc.
            signal_type = "MY_CUSTOM_SIGNAL"

            # TODO: Add any additional metadata you want to include in alerts
            metadata = {
                'your_metric_1': 'value1',
                'your_metric_2': 'value2',
                'strategy': self.name
            }

            return WhaleSignal(
                symbol=symbol,
                confidence=confidence,
                signal_type=signal_type,
                value=trade_value,
                metadata=metadata,
                timestamp=time.time()
            )

        return None

    def get_required_data_fields(self) -> list[str]:
        """
        Specify which data fields your strategy needs.

        Returns:
            List of required field names
        """
        # TODO: Update this list with the data fields your strategy needs
        return ['symbol', 'price', 'trades', 'orderbook']


# Example configuration for config.yaml
EXAMPLE_CONFIG = {
    'custom_strategy_template': {
        'enabled': True,
        'param1': 'value',
        'param2': 100
    }
}


# TODO: Add unit tests for your strategy
# See tests/ directory for examples
