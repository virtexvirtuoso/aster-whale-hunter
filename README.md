# 🐋 Aster Whale Hunter

<div align="center">

**Production-Ready Cryptocurrency Whale Detection Framework**

[![License: MIT](https://img.shields.io/github/license/virtexvirtuoso/aster-whale-hunter)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Stars](https://img.shields.io/github/stars/virtexvirtuoso/aster-whale-hunter?style=social)](https://github.com/virtexvirtuoso/aster-whale-hunter)
[![GitHub Issues](https://img.shields.io/github/issues/virtexvirtuoso/aster-whale-hunter)](https://github.com/virtexvirtuoso/aster-whale-hunter/issues)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/virtexvirtuoso/aster-whale-hunter/pulls)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[**Website**](https://whalehunter.virtuosocrypto.com) • [**Documentation**](https://github.com/virtexvirtuoso/aster-whale-hunter/wiki) • [**Telegram Bot**](https://t.me/Aster_whale_hunter_bot) • [**Report Bug**](https://github.com/virtexvirtuoso/aster-whale-hunter/issues) • [**Request Feature**](https://github.com/virtexvirtuoso/aster-whale-hunter/discussions)

</div>

---

## 🎯 What is Aster Whale Hunter?

Aster Whale Hunter is a **professional-grade framework** for building cryptocurrency whale detection systems. It provides all the infrastructure you need to monitor large trades, analyze market movements, and deliver real-time alerts - while letting you implement your own proprietary detection strategies.

Think of it as the **Rails for whale detection** - we handle the boring stuff (APIs, databases, notifications, monitoring) so you can focus on what makes your detection unique.

### 🏆 Key Differentiators

- **Framework, Not a Black Box**: Full control over detection logic
- **Production-Ready**: Battle-tested with circuit breakers, rate limiting, and health monitoring
- **Real-Time Telegram Integration**: Instant alerts with rich formatting and admin controls
- **Multi-Exchange Support**: Built for AsterDex, extensible to any exchange
- **Enterprise-Grade Resilience**: Automatic failure recovery, alert deduplication, async processing

---

## 🚀 Live Demo & Screenshots

### 📱 See It In Action

Visit our [**website**](https://whalehunter.virtuosocrypto.com) to see:
- 📸 **3 Real Telegram Alert Examples** showing different whale detection scenarios
- 🎬 **Live detection demonstrations**
- 📊 **Performance metrics and statistics**

### 🤖 Try The Bot

Experience the framework yourself: [@Aster_whale_hunter_bot](https://t.me/Aster_whale_hunter_bot)

---

## ⚡ Quick Start

Get up and running in under 5 minutes:

```bash
# 1. Clone the repository
git clone https://github.com/virtexvirtuoso/aster-whale-hunter.git
cd aster-whale-hunter

# 2. Set up Python environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your bot
cp config.example.yaml config.yaml
# Edit config.yaml with your API keys

# 5. Run!
python -m src.whale_hunter
```

**That's it!** Your bot is now running. Send `/help` to your Telegram bot to see available commands.

---

## 🏗️ Architecture: Framework vs. Strategies

### 📦 What's Included (The Framework)

We provide **complete, production-ready infrastructure**:

#### **Core Systems**
- ✅ **Telegram Bot Engine** - Full bot framework with command handling
- ✅ **Exchange Connectors** - AsterDex & Hyperliquid API clients
- ✅ **Database Layer** - SQLite with models and migration support
- ✅ **Alert Management** - Deduplication, rate limiting, formatting
- ✅ **Health Monitoring** - HTTP server (port 8090) with metrics
- ✅ **Circuit Breakers** - Automatic failure detection and recovery
- ✅ **Async Task Manager** - Concurrent processing with backpressure
- ✅ **Configuration System** - YAML-based with live reload
- ✅ **Logging Framework** - Structured, async-safe logging
- ✅ **Session Management** - Connection pooling and lifecycle
- ✅ **Retry Logic** - Exponential backoff with jitter

#### **Telegram Features**
- 📨 Real-time alert delivery
- 👤 User management and permissions
- 🎛️ Admin command interface
- 📊 Market data commands
- ⚙️ Live configuration updates
- 🔔 Alert history and statistics

### 🎨 What You Build (Detection Strategies)

This is where **your innovation happens**:

```python
# Your proprietary detection logic goes here
class MyWhaleStrategy(BaseWhaleStrategy):
    async def analyze(self, market_data: Dict[str, Any]) -> Optional[WhaleSignal]:
        # Your secret sauce for detecting whales
        # - Machine learning models
        # - Statistical analysis
        # - Pattern recognition
        # - Cross-exchange arbitrage detection
        # - Order flow analysis
        # - Whatever makes your detection unique!
```

**Examples of strategies you might build:**
- 🎯 **Volume Spike Detection** - Identify unusual trading volume patterns
- 📊 **Order Book Imbalance** - Detect large walls and hidden orders
- 🔄 **Cross-Exchange Arbitrage** - Track whale movements across exchanges
- 🤖 **ML-Based Pattern Recognition** - Use AI to identify whale behavior
- 📈 **Technical Indicator Fusion** - Combine multiple signals for high confidence
- 🌊 **Liquidity Flow Analysis** - Track smart money movements

---

## ✨ Features

### 🔥 Production-Ready Infrastructure

| Feature | Description |
|---------|------------|
| **🚦 Circuit Breakers** | Automatic API failure detection and recovery |
| **⚡ Async Processing** | High-performance concurrent task execution |
| **🔄 Live Config Reload** | Update settings without downtime |
| **📊 Health Monitoring** | Real-time system metrics and status |
| **🛡️ Rate Limiting** | Intelligent throttling to prevent spam |
| **🔍 Alert Deduplication** | Prevents duplicate notifications |
| **💾 Persistent Storage** | SQLite database with automatic backups |
| **📝 Structured Logging** | Comprehensive logging with rotation |

### 🤖 Telegram Bot Capabilities

#### **Admin Commands**
```
/status              - System health and statistics
/health_check        - Run full diagnostics
/set_threshold       - Adjust detection thresholds
/set_confidence      - Configure confidence levels
/add_symbol          - Add trading pairs to monitor
/remove_symbol       - Remove trading pairs
/get_config          - View current configuration
/pause_alerts        - Temporarily disable alerts
/resume_alerts       - Re-enable alerts
```

#### **Market Analysis**
```
/top gainers         - Top gaining pairs (24h)
/top losers          - Top losing pairs (24h)
/top volume          - Highest volume pairs
/top volatile        - Most volatile pairs
/market_summary      - Overall market statistics
```

---

## 🔧 Configuration

### Basic Setup

```yaml
# config.yaml
exchange:
  name: "asterdex"
  api_key: ${ASTERDX_API_KEY}      # From environment
  api_secret: ${ASTERDX_API_SECRET}
  rate_limit: 1200
  timeout: 30

telegram:
  bot_token: ${TELEGRAM_BOT_TOKEN}
  chat_id: "-1001234567890"        # Your group/channel ID
  admin_users:
    - 123456789                     # Your Telegram user ID
  alert_format: "rich"              # rich/simple/json

whale_detection:
  symbols:
    - "BTCUSDT"
    - "ETHUSDT"
    - "ASTERUSDT"
  check_interval: 5                 # seconds
  lookback_period: 300              # seconds

monitoring:
  health_check_port: 8090
  metrics_enabled: true
  log_level: "INFO"
```

### Advanced Features

```yaml
# Circuit breaker configuration
circuit_breakers:
  api_calls:
    failure_threshold: 5
    recovery_timeout: 60
    half_open_requests: 2

# Alert management
alerts:
  max_per_hour: 20
  max_per_symbol: 5
  cooldown_minutes: 10
  deduplication_window: 300

# Strategy configuration (your custom strategies)
strategies:
  my_volume_strategy:
    enabled: true
    min_volume: 1000000
    spike_multiplier: 3.0

  my_ml_strategy:
    enabled: true
    model_path: "./models/whale_detector.pkl"
    confidence_threshold: 0.85
```

---

## 🎓 Creating Your Own Strategies

### Step 1: Use the Template

```bash
cp examples/custom_strategy_template.py src/strategies/my_strategy.py
```

### Step 2: Implement Your Logic

```python
from typing import Dict, Any, Optional
from src.strategies.base_strategy import BaseWhaleStrategy, WhaleSignal

class MyVolumeWhaleStrategy(BaseWhaleStrategy):
    """Detect whales based on volume anomalies"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.volume_threshold = config.get('volume_threshold', 1000000)
        self.spike_factor = config.get('spike_factor', 3.0)

    async def analyze(self, market_data: Dict[str, Any]) -> Optional[WhaleSignal]:
        """Analyze market data for whale activity"""

        # Your detection logic
        current_volume = market_data['volume']
        avg_volume = market_data['avg_volume_24h']

        if current_volume > avg_volume * self.spike_factor:
            # Calculate confidence based on your criteria
            confidence = min(current_volume / (avg_volume * 5), 1.0)

            return WhaleSignal(
                symbol=market_data['symbol'],
                confidence=confidence,
                signal_type='VOLUME_SPIKE',
                value=current_volume,
                metadata={
                    'spike_ratio': current_volume / avg_volume,
                    'usd_value': current_volume * market_data['price']
                },
                timestamp=market_data['timestamp']
            )

        return None

    def get_required_data_fields(self) -> list[str]:
        """Specify what data your strategy needs"""
        return ['symbol', 'volume', 'avg_volume_24h', 'price', 'timestamp']
```

### Step 3: Register in Config

```yaml
strategies:
  my_volume_whale:
    enabled: true
    volume_threshold: 1000000
    spike_factor: 3.0
```

### Step 4: Test Your Strategy

```bash
# Run unit tests
pytest tests/test_strategies/test_my_strategy.py -v

# Run integration test with live data
python -m src.test_runner --strategy my_volume_whale --symbol BTCUSDT
```

---

## 📈 Performance & Scaling

### Resource Requirements

| Symbols | Memory | CPU | Network | Recommended Setup |
|---------|--------|-----|---------|-------------------|
| 1-10 | 50-100 MB | 5-10% | 2-4 MB/hr | Single instance |
| 10-25 | 100-200 MB | 10-20% | 4-8 MB/hr | Single instance (optimal) |
| 25-50 | 200-400 MB | 20-30% | 8-15 MB/hr | Adjust rate limits |
| 50+ | 400+ MB | 30%+ | 15+ MB/hr | Multiple instances |

### Optimization Tips

- **Use async strategies** for I/O-bound operations
- **Cache frequently accessed data** to reduce API calls
- **Batch database writes** for better performance
- **Enable compression** for Telegram messages
- **Use circuit breakers** to prevent cascade failures

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test categories
pytest tests/unit/ -v              # Unit tests only
pytest tests/integration/ -v       # Integration tests
pytest tests/strategies/ -v        # Strategy tests

# Live testing with mock data
python -m src.test_runner --mock-mode

# Performance testing
python -m src.performance_test --duration 3600
```

---

## 🌟 Community & Support

### 🤝 Get Help

- **📖 Documentation**: [GitHub Wiki](https://github.com/virtexvirtuoso/aster-whale-hunter/wiki)
- **💬 Discussions**: [GitHub Discussions](https://github.com/virtexvirtuoso/aster-whale-hunter/discussions)
- **🐛 Bug Reports**: [GitHub Issues](https://github.com/virtexvirtuoso/aster-whale-hunter/issues)
- **🤖 Telegram Bot**: [@Aster_whale_hunter_bot](https://t.me/Aster_whale_hunter_bot)
- **🌐 Website**: [whalehunter.virtuosocrypto.com](https://whalehunter.virtuosocrypto.com)

### 🎯 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Ways to contribute:**
- 🐛 Report bugs and issues
- 💡 Suggest new features
- 📝 Improve documentation
- 🔧 Submit pull requests
- 🌟 Star the repository
- 📢 Share with others

### 📣 Stay Updated

- Watch the repository for updates
- Join our [Telegram community](https://t.me/Aster_whale_hunter_bot)
- Follow development on [GitHub](https://github.com/virtexvirtuoso/aster-whale-hunter)

---

## 🗺️ Roadmap

### ✅ Current Features (v1.0)
- AsterDex integration
- Telegram bot framework
- Basic strategy interface
- Health monitoring
- Circuit breakers

### 🚧 In Development (v1.1)
- [ ] WebSocket support for real-time data
- [ ] Multiple exchange support (Binance, Bybit)
- [ ] Advanced strategy templates
- [ ] Web dashboard interface
- [ ] Docker containerization

### 🔮 Future Plans (v2.0)
- [ ] Machine learning strategy builder
- [ ] Multi-chain support (BSC, Polygon)
- [ ] DEX integration (Uniswap, PancakeSwap)
- [ ] Cloud deployment templates
- [ ] Strategy marketplace

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🛡️ Security

### Best Practices

- **Never commit API keys** - Use environment variables
- **Restrict bot access** - Configure admin users in Telegram
- **Regular backups** - Database is in `data/whale_hunter.db`
- **Monitor logs** - Check `logs/` directory for issues
- **Update regularly** - Keep dependencies current

### Reporting Security Issues

Please report security vulnerabilities to [GitHub Security Advisories](https://github.com/virtexvirtuoso/aster-whale-hunter/security/advisories/new)

---

## ⚠️ Disclaimer

This software is provided for educational and research purposes only. Cryptocurrency trading carries significant risk. The authors are not responsible for any financial losses incurred through the use of this software.

---

## 🙏 Acknowledgments

- Built for the [AsterDex](https://asterdex.com) ecosystem
- Inspired by the crypto community's need for transparency
- Special thanks to all contributors and testers

---

<div align="center">

**Built with ❤️ for the Crypto Community**

[**Website**](https://whalehunter.virtuosocrypto.com) • [**GitHub**](https://github.com/virtexvirtuoso/aster-whale-hunter) • [**Telegram**](https://t.me/Aster_whale_hunter_bot)

⭐ **Star us on GitHub** to show your support!

</div>