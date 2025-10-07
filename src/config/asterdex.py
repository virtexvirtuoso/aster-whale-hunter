"""
Centralized configuration for AsterDex endpoints.

Environment variables can override defaults:
- ASTERDEX_FAPI_BASE_URL
- ASTERDEX_WS_BASE_URL
"""

import os


ASTERDEX_FAPI_BASE_URL = os.getenv('ASTERDEX_FAPI_BASE_URL', 'https://fapi.asterdex.com')
ASTERDEX_WS_BASE_URL = os.getenv('ASTERDEX_WS_BASE_URL', 'wss://fstream.asterdex.com/ws')


