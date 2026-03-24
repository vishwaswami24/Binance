"""
Configuration settings for the Binance Trading Bot.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Binance API Configuration
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')
TESTNET = os.getenv('TESTNET', '1') == '1'

# URLs
BASE_URL = "https://testnet.binancefuture.com" if TESTNET else "https://fapi.binance.com"

# Trading Configuration
DEFAULT_SYMBOL = "BTCUSDT"
MIN_NOTIONAL = 5.0  # Minimum notional value for USDT-M futures
MAX_PRICE_PRECISION = 8
MAX_QUANTITY_PRECISION = 8

# Order Configuration
DEFAULT_TIME_IN_FORCE = "GTC"  # Good Till Cancel
DEFAULT_WORKING_TYPE = "CONTRACT_PRICE"

# Grid Strategy Configuration
GRID_DEFAULT_MIN_PRICE = 0.0
GRID_DEFAULT_MAX_PRICE = 0.0
GRID_DEFAULT_GRID_COUNT = 10
GRID_DEFAULT_QUANTITY = 0.0
GRID_DEFAULT_PRICE_PRECISION = 2

# TWAP Strategy Configuration
TWAP_DEFAULT_INTERVAL = 60  # seconds
TWAP_DEFAULT_TOTAL_INTERVALS = 10
TWAP_DEFAULT_QUANTITY_PER_INTERVAL = 0.0

# Logging Configuration
LOG_DIR = "logs"
LOG_FILE = "trading_bot.log"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Display Configuration
TABLE_FORMAT = "simple"
