"""
Input validators for the Binance Trading Bot.
Validates trading inputs before order execution.
"""
from typing import Optional, Tuple
from config import MIN_NOTIONAL, DEFAULT_SYMBOL
from utils.logger import logger


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_symbol(symbol: str) -> Tuple[bool, Optional[str]]:
    """
    Validate trading symbol.
    
    Args:
        symbol: Trading pair symbol (e.g., BTCUSDT)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not symbol:
        return False, "Symbol cannot be empty"
    
    symbol = symbol.upper().strip()
    
    # Check if symbol ends with USDT (USDT-M futures)
    if not symbol.endswith('USDT'):
        return False, "Only USDT-M futures are supported (symbol must end with USDT)"
    
    # Basic length check
    if len(symbol) < 6 or len(symbol) > 12:
        return False, "Invalid symbol format"
    
    return True, None


def validate_quantity(quantity: float, min_qty: float = 0.001) -> Tuple[bool, Optional[str]]:
    """
    Validate order quantity.
    
    Args:
        quantity: Order quantity
        min_qty: Minimum allowed quantity
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if quantity is None:
        return False, "Quantity is required"
    
    try:
        quantity = float(quantity)
    except (ValueError, TypeError):
        return False, "Quantity must be a valid number"
    
    if quantity <= 0:
        return False, "Quantity must be greater than 0"
    
    if quantity < min_qty:
        return False, f"Quantity must be at least {min_qty}"
    
    return True, None


def validate_price(price: float, min_price: float = 0.01) -> Tuple[bool, Optional[str]]:
    """
    Validate order price.
    
    Args:
        price: Order price
        min_price: Minimum allowed price
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if price is None:
        return False, "Price is required"
    
    try:
        price = float(price)
    except (ValueError, TypeError):
        return False, "Price must be a valid number"
    
    if price <= 0:
        return False, "Price must be greater than 0"
    
    if price < min_price:
        return False, f"Price must be at least {min_price}"
    
    return True, None


def validate_stop_price(stop_price: float, limit_price: float = None, 
                        side: str = 'BUY') -> Tuple[bool, Optional[str]]:
    """
    Validate stop price for stop-limit orders.
    
    Args:
        stop_price: Stop price
        limit_price: Limit price (for comparison)
        side: Order side (BUY or SELL)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    is_valid, error = validate_price(stop_price)
    if not is_valid:
        return False, f"Invalid stop price: {error}"
    
    if limit_price is not None:
        # For BUY orders: stop price should be >= limit price
        # For SELL orders: stop price should be <= limit price
        if side.upper() == 'BUY':
            if stop_price < limit_price:
                return False, "For BUY orders, stop price should be >= limit price"
        else:
            if stop_price > limit_price:
                return False, "For SELL orders, stop price should be <= limit price"
    
    return True, None


def validate_notional(symbol: str, quantity: float, price: float) -> Tuple[bool, Optional[str]]:
    """
    Validate order notional value meets minimum requirements.
    
    Args:
        symbol: Trading pair symbol
        quantity: Order quantity
        price: Order price
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    notional = float(quantity) * float(price)
    
    if notional < MIN_NOTIONAL:
        return False, f"Order notional must be at least {MIN_NOTIONAL} USDT"
    
    return True, None


def validate_side(side: str) -> Tuple[bool, Optional[str]]:
    """
    Validate order side.
    
    Args:
        side: Order side (BUY or SELL)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not side:
        return False, "Side is required"
    
    side = side.upper().strip()
    
    if side not in ['BUY', 'SELL']:
        return False, "Side must be either BUY or SELL"
    
    return True, None


def validate_order_type(order_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validate order type.
    
    Args:
        order_type: Order type (MARKET, LIMIT, STOP, STOP_MARKET, TAKE_PROFIT, etc.)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_types = [
        'MARKET', 'LIMIT', 'STOP', 'STOP_MARKET', 
        'TAKE_PROFIT', 'TAKE_PROFIT_MARKET', 'TRAILING_STOP_MARKET'
    ]
    
    if not order_type:
        return False, "Order type is required"
    
    order_type = order_type.upper().strip()
    
    if order_type not in valid_types:
        return False, f"Invalid order type. Must be one of: {', '.join(valid_types)}"
    
    return True, None


def validate_time_in_force(tif: str) -> Tuple[bool, Optional[str]]:
    """
    Validate time in force.
    
    Args:
        tif: Time in force (GTC, IOC, FOK)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_tif = ['GTC', 'IOC', 'FOK']
    
    if not tif:
        return True, None  # Optional field
    
    tif = tif.upper().strip()
    
    if tif not in valid_tif:
        return False, f"Time in force must be one of: {', '.join(valid_tif)}"
    
    return True, None


def validate_leverage(leverage: int) -> Tuple[bool, Optional[str]]:
    """
    Validate leverage value.
    
    Args:
        leverage: Leverage value (1-125)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if leverage is None:
        return True, None
    
    try:
        leverage = int(leverage)
    except (ValueError, TypeError):
        return False, "Leverage must be a valid integer"
    
    if leverage < 1 or leverage > 125:
        return False, "Leverage must be between 1 and 125"
    
    return True, None


def validate_grid_parameters(min_price: float, max_price: float, 
                             grid_count: int, quantity: float) -> Tuple[bool, Optional[str]]:
    """
    Validate grid trading parameters.
    
    Args:
        min_price: Minimum price for grid
        max_price: Maximum price for grid
        grid_count: Number of grid levels
        quantity: Quantity per grid level
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate prices
    is_valid, error = validate_price(min_price)
    if not is_valid:
        return False, f"Invalid min_price: {error}"
    
    is_valid, error = validate_price(max_price)
    if not is_valid:
        return False, f"Invalid max_price: {error}"
    
    if min_price >= max_price:
        return False, "Min price must be less than max price"
    
    # Validate grid count
    if grid_count < 2:
        return False, "Grid count must be at least 2"
    
    if grid_count > 100:
        return False, "Grid count cannot exceed 100"
    
    # Validate quantity
    is_valid, error = validate_quantity(quantity)
    if not is_valid:
        return False, f"Invalid quantity: {error}"
    
    return True, None


def validate_twap_parameters(quantity: float, intervals: int, 
                             interval_seconds: int) -> Tuple[bool, Optional[str]]:
    """
    Validate TWAP strategy parameters.
    
    Args:
        quantity: Total order quantity
        intervals: Number of intervals
        interval_seconds: Seconds between intervals
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate quantity
    is_valid, error = validate_quantity(quantity)
    if not is_valid:
        return False, f"Invalid quantity: {error}"
    
    # Validate intervals
    if intervals < 1:
        return False, "Intervals must be at least 1"
    
    if intervals > 100:
        return False, "Intervals cannot exceed 100"
    
    # Validate interval seconds
    if interval_seconds < 1:
        return False, "Interval seconds must be at least 1"
    
    if interval_seconds > 3600:
        return False, "Interval seconds cannot exceed 3600 (1 hour)"
    
    return True, None


def validate_api_keys(api_key: str, secret_key: str) -> Tuple[bool, Optional[str]]:
    """
    Validate API credentials are provided.
    
    Args:
        api_key: Binance API key
        secret_key: Binance API secret
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not api_key or api_key == 'your_api_key_here':
        return False, "API key is not configured"
    
    if not secret_key or secret_key == 'your_secret_key_here':
        return False, "API secret is not configured"
    
    return True, None
