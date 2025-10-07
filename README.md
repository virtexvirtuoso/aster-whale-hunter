# 🐋 Aster Whale Hunter

**Production-ready cryptocurrency whale detection framework with Telegram bot integration**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Aster Whale Hunter is a flexible, extensible framework for detecting large cryptocurrency trades ("whales") and sending real-time Telegram alerts. Built for AsterDex but adaptable to any exchange.

## ✨ What This Framework Provides

### 🏗️ **Complete Infrastructure** (Included)
- ✅ **Telegram Bot Framework** - Real-time alerts, admin commands, user management
- ✅ **Exchange API Clients** - AsterDex & Hyperliquid integration
- ✅ **Database Layer** - SQLite persistence with alert history
- ✅ **Configuration Management** - YAML-based, live-reloadable configs
- ✅ **Health Monitoring** - Built-in health server on port 8090
- ✅ **Logging System** - Structured logging with async support
- ✅ **Circuit Breaker** - Automatic failure detection and recovery
- ✅ **Rate Limiting** - Intelligent throttling to prevent spam
- ✅ **Alert Deduplication** - Prevent duplicate notifications

### 🎯 **Detection Strategies** (NOT Included - Build Your Own!)
This is a **framework**, not a complete solution. Detection strategies are intentionally excluded so you can build your own proprietary logic.

**What you need to implement:**
- Your whale detection algorithms
- Custom confidence scoring
- Signal fusion logic (if combining multiple strategies)
- Threshold calculations

**We provide:**
- `BaseWhaleStrategy` interface to implement
- Simple threshold example strategy
- Strategy template to get started
- Full documentation on creating strategies

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/aster-whale-hunter.git
cd aster-whale-hunter

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy example configuration
cp config.example.yaml config.yaml

# Edit configuration with your API keys
nano config.yaml

# Run the bot
python -m src.whale_hunter
```

---

## 📋 Requirements

- **Python 3.12+** (required)
- **AsterDex API credentials** (API key & secret)
- **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))

---

## ⚙️ Configuration

### 1. Environment Variables

```bash
export ASTERDX_API_KEY="your_api_key"
export ASTERDX_API_SECRET="your_api_secret"
export TELEGRAM_BOT_TOKEN="your_bot_token"
```

### 2. Configuration File (`config.yaml`)

```yaml
# Exchange Configuration
exchange:
  api_key: ${ASTERDX_API_KEY}
  api_secret: ${ASTERDX_API_SECRET}
  rate_limit: 1200
  timeout: 30

# Telegram Bot
telegram:
  bot_token: ${TELEGRAM_BOT_TOKEN}
  chat_id: "your_telegram_chat_id"
  admin_users:
    - 123456789  # Your Telegram user ID

# Whale Detection Settings
whale_detection:
  symbols:
    - "BTCUSDT"
    - "ETHUSDT"
    - "ASTERUSDT"
  max_alerts_per_hour: 10
  enable_dynamic_symbols: true

# Your Custom Strategies
strategies:
  my_custom_strategy:
    enabled: true
    # Your strategy-specific parameters
```

### 3. Get Your Telegram Chat ID

```bash
# Start your bot, send it a message, then run:
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
# Look for "chat":{"id": YOUR_CHAT_ID}
```

---

## 🎨 Creating Custom Detection Strategies

### Step 1: Copy the Template

```bash
cp examples/custom_strategy_template.py src/strategies/my_strategy.py
```

### Step 2: Implement Your Logic

```python
from typing import Dict, Any, Optional
from src.strategies.base_strategy import BaseWhaleStrategy, WhaleSignal

class MyWhaleStrategy(BaseWhaleStrategy):
    async def analyze(self, market_data: Dict[str, Any]) -> Optional[WhaleSignal]:
        # Your detection logic here
        if self._is_whale_detected(market_data):
            return WhaleSignal(
                symbol=market_data['symbol'],
                confidence=0.90,
                signal_type='MY_WHALE_SIGNAL',
                value=trade_value,
                metadata={'custom_data': 'value'},
                timestamp=market_data['timestamp']
            )
        return None

    def get_required_data_fields(self) -> list[str]:
        return ['symbol', 'trades', 'orderbook']
```

### Step 3: Register Your Strategy

Add to `config.yaml`:

```yaml
strategies:
  my_whale_strategy:
    enabled: true
    threshold: 1000000
    confidence_min: 0.7
```

---

## 📱 Telegram Commands

### Admin Commands

```
/status                    - Show system status
/health_check             - Run health diagnostics
/set_threshold <amount>   - Set minimum trade value
/set_confidence <0-1>     - Set confidence threshold
/add_symbol <SYMBOL>      - Add trading pair to monitor
/remove_symbol <SYMBOL>   - Remove trading pair
/get_config               - View current configuration
/help                     - Show all commands
```

### Market Commands

```
/top gainers              - Top gaining pairs (24h)
/top losers               - Top losing pairs (24h)
/top volume               - Highest volume pairs
/top volatile             - Most volatile pairs
```

---

## 🏗️ Project Structure

```
aster-whale-hunter/
├── src/
│   ├── api/                    # Exchange API clients
│   ├── telegram/               # Telegram bot framework
│   ├── database/               # Data persistence
│   ├── config/                 # Configuration management
│   ├── core/                   # Core engine & interfaces
│   ├── monitoring/             # Health checks & metrics
│   ├── utils/                  # Utilities
│   └── strategies/             # Strategy interface & examples
│       ├── base_strategy.py           # Base class to inherit
│       └── simple_threshold_example.py  # Example implementation
├── examples/
│   └── custom_strategy_template.py    # Template to copy
├── tests/                      # Test suite
├── docs/                       # Documentation
├── config.example.yaml         # Example configuration
├── requirements.txt            # Dependencies
└── README.md                   # This file
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Test your custom strategy
pytest tests/test_strategies/test_my_strategy.py -v
```

---

## 🔧 Advanced Features

### Health Monitoring (Port 8090)

```bash
# Health check
curl http://localhost:8090/health

# System metrics
curl http://localhost:8090/metrics

# System status
curl http://localhost:8090/status
```

### Circuit Breaker Protection

Automatic failure detection and recovery for API endpoints. Configure in `config.yaml`:

```yaml
circuit_breakers:
  api_endpoint:
    failure_threshold: 5
    timeout_seconds: 30
    recovery_threshold: 2
```

### Live Configuration Reload

Update settings without restarting via Telegram:

```
/set_threshold 2000000
/set_confidence 0.85
/add_symbol SOLUSDT
```

---

## 📊 Performance

### Expected Resource Usage
- **Memory**: ~50-150MB base + 5-10MB per symbol
- **CPU**: ~5-20% on modern systems
- **Network**: ~2-8MB/hour
- **Database Growth**: ~5-50MB/month

### Scaling Recommendations
- **< 10 symbols**: Single instance
- **10-20 symbols**: Optimal range
- **20-50 symbols**: Adjust rate limits
- **> 50 symbols**: Multiple instances with load balancing

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Ways to Contribute
- 🐛 Report bugs
- 💡 Suggest features
- 📝 Improve documentation
- 🔧 Submit pull requests
- ⭐ Star the repo!

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🛡️ Security

- **API Keys**: Store in environment variables, never commit
- **Telegram Bot**: Restrict admin commands to authorized users
- **Database**: Regular backups recommended
- **Network**: Use HTTPS/WSS connections only

---

## 💬 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/aster-whale-hunter/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/aster-whale-hunter/discussions)
- **Telegram**: [@Aster_whale_hunter_bot](https://t.me/Aster_whale_hunter_bot)

---

## 🌟 Show Your Support

If you find this project useful, please consider:
- ⭐ Starring the repository
- 🐛 Reporting bugs
- 💡 Suggesting features
- 📢 Sharing with others

---

## ⚠️ Disclaimer

This software is for educational and research purposes only. Cryptocurrency trading carries significant risk. Use at your own discretion.

---

**Built with ❤️ for the crypto community**

**Website**: [whalehunter.virtuosocrypto.com](https://whalehunter.virtuosocrypto.com)
