# Contributing to Aster Whale Hunter

First off, thank you for considering contributing to Aster Whale Hunter! 🎉

## Code of Conduct

Be respectful, inclusive, and collaborative. We're all here to build something great together.

## How Can I Contribute?

### 🐛 Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **Environment details** (OS, Python version, etc.)
- **Log output** if applicable

**Example:**
```markdown
## Bug: Alert deduplication not working

**Steps to Reproduce:**
1. Start bot with `python -m src.whale_hunter`
2. Trigger same whale alert twice
3. Observe duplicate Telegram messages

**Expected:** Second alert should be deduplicated
**Actual:** Both alerts sent

**Environment:**
- OS: Ubuntu 22.04
- Python: 3.12.1
- Version: v1.0.0

**Logs:**
[paste relevant logs]
```

### 💡 Suggesting Features

Feature requests are welcome! Please provide:

- **Clear use case** - Why is this feature needed?
- **Proposed solution** - How would it work?
- **Alternatives considered** - Other approaches you thought of
- **Additional context** - Screenshots, examples, etc.

### 🔧 Pull Requests

1. **Fork the repo** and create your branch from `main`
2. **Follow code style** - We use `black` for formatting
3. **Add tests** if you've added code
4. **Update documentation** if needed
5. **Ensure tests pass** before submitting
6. **Write clear commit messages**

**Branch naming:**
- `feature/your-feature-name`
- `bugfix/issue-description`
- `docs/what-you-changed`

**Commit message format:**
```
type: Short description (50 chars or less)

Longer explanation if needed. Wrap at 72 characters.

- Bullet points are okay
- Reference issues like #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### 📝 Code Style

We use:
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint
flake8 src/ tests/

# Type check
mypy src/
```

### ✅ Testing

All contributions should include tests:

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Test specific file
pytest tests/test_strategies/test_my_feature.py -v
```

**Test structure:**
```python
def test_feature_name():
    """Test that feature does X when Y happens"""
    # Arrange
    setup_test_data()

    # Act
    result = call_feature()

    # Assert
    assert result == expected_value
```

### 📚 Documentation

- **Docstrings** for all public classes/functions
- **Comments** for complex logic
- **README updates** for new features
- **Example code** when helpful

**Docstring format:**
```python
def my_function(param1: str, param2: int) -> bool:
    """
    One-line summary of what this does.

    More detailed explanation if needed. Can be multiple paragraphs.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When X happens
    """
```

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/aster-whale-hunter.git
cd aster-whale-hunter

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/aster-whale-hunter.git

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install black isort flake8 mypy pytest pytest-cov

# Install pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install
```

## Project Structure

```
src/
├── strategies/        # Detection strategy interface & examples
├── api/              # Exchange API clients
├── telegram/         # Telegram bot framework
├── database/         # Data persistence
├── config/           # Configuration management
├── core/             # Core engine
├── monitoring/       # Health & metrics
└── utils/            # Utilities

tests/
├── test_strategies/  # Strategy tests
├── test_api/        # API client tests
└── ...              # More test modules

examples/            # Example code
docs/               # Documentation
```

## Review Process

1. **Submit PR** with clear description
2. **Automated checks** run (tests, linting)
3. **Code review** by maintainers
4. **Address feedback** if any
5. **Merge** when approved!

We aim to review PRs within 48 hours.

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Thanked in the community 🙏

## Questions?

- **GitHub Discussions**: Ask questions
- **Issues**: Report bugs or request features
- **Telegram**: [@Aster_whale_hunter_bot](https://t.me/Aster_whale_hunter_bot)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing! 🚀**
