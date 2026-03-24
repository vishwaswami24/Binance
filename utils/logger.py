"""
Logger utility for the Binance Trading Bot.
Provides structured logging with file and console output.
"""
import logging
import os
from datetime import datetime
from config import LOG_DIR, LOG_FILE, LOG_FORMAT, LOG_DATE_FORMAT


class TradingLogger:
    """Custom logger for trading bot with structured logging."""
    
    def __init__(self, name: str = "BinanceTradingBot"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Avoid duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup logging handlers for file and console output."""
        # Create logs directory if it doesn't exist
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        
        log_path = os.path.join(LOG_DIR, LOG_FILE)
        
        # File handler - logs all levels
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        
        # Console handler - logs INFO and above
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            LOG_DATE_FORMAT
        )
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)
    
    def critical(self, message: str):
        """Log critical message."""
        self.logger.critical(message)
    
    def log_order(self, order_type: str, symbol: str, details: dict):
        """Log order placement with details."""
        details_str = " | ".join([f"{k}={v}" for k, v in details.items()])
        self.info(f"ORDER | {order_type} | {symbol} | {details_str}")
    
    def log_execution(self, order_id: str, status: str, details: dict):
        """Log order execution."""
        details_str = " | ".join([f"{k}={v}" for k, v in details.items()])
        self.info(f"EXECUTION | {order_id} | {status} | {details_str}")
    
    def log_error(self, error_type: str, message: str, details: dict = None):
        """Log error with optional details."""
        details_str = ""
        if details:
            details_str = " | " + " | ".join([f"{k}={v}" for k, v in details.items()])
        self.error(f"ERROR | {error_type} | {message}{details_str}")
    
    def log_strategy(self, strategy: str, action: str, details: dict):
        """Log strategy actions."""
        details_str = " | ".join([f"{k}={v}" for k, v in details.items()])
        self.info(f"STRATEGY | {strategy} | {action} | {details_str}")


# Default logger instance
logger = TradingLogger()


def get_logger(name: str = None) -> TradingLogger:
    """Get a logger instance with optional custom name."""
    if name:
        return TradingLogger(name)
    return logger
