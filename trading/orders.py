"""
Order execution classes for the Binance Trading Bot.
Handles Market and Limit orders.
"""
from typing import Dict, Optional, Any, List
from trading.client import BinanceClient
from trading.validators import (
    validate_symbol, validate_quantity, validate_price,
    validate_side, validate_notional, validate_order_type
)
from utils.logger import logger


class Order:
    """Base class for orders."""
    
    def __init__(self, client: BinanceClient):
        self.client = client
    
    def validate(self, symbol: str, quantity: float, price: float = None,
                 side: str = 'BUY') -> tuple[bool, Optional[str]]:
        """
        Validate order parameters.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        is_valid, error = validate_symbol(symbol)
        if not is_valid:
            return False, error
        
        is_valid, error = validate_side(side)
        if not is_valid:
            return False, error
        
        is_valid, error = validate_quantity(quantity)
        if not is_valid:
            return False, error
        
        if price is not None:
            is_valid, error = validate_price(price)
            if not is_valid:
                return False, error
            
            # Validate notional value
            is_valid, error = validate_notional(symbol, quantity, price)
            if not is_valid:
                return False, error
        
        return True, None


class MarketOrder(Order):
    """Market order implementation."""
    
    def execute(self, symbol: str, side: str, quantity: float,
                reduce_only: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Execute a market order.
        
        Args:
            symbol: Trading pair symbol
            side: BUY or SELL
            quantity: Order quantity
            reduce_only: Whether to only reduce position
            **kwargs: Additional parameters
        
        Returns:
            Order response from Binance
        """
        # Validate order
        is_valid, error = self.validate(symbol, quantity, side=side)
        if not is_valid:
            raise ValueError(f"Order validation failed: {error}")
        
        logger.info(f"Executing MARKET order: {side} {quantity} {symbol}")
        
        result = self.client.place_market_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            reduce_only=reduce_only
        )
        
        logger.info(f"Market order executed: {result.get('orderId')}")
        
        return result
    
    def get_current_price(self, symbol: str) -> float:
        """Get current market price for a symbol."""
        return self.client.get_current_price(symbol)


class LimitOrder(Order):
    """Limit order implementation."""
    
    def execute(self, symbol: str, side: str, quantity: float, price: float,
                time_in_force: str = 'GTC', reduce_only: bool = False,
                **kwargs) -> Dict[str, Any]:
        """
        Execute a limit order.
        
        Args:
            symbol: Trading pair symbol
            side: BUY or SELL
            quantity: Order quantity
            price: Limit price
            time_in_force: GTC, IOC, FOK
            reduce_only: Whether to only reduce position
            **kwargs: Additional parameters
        
        Returns:
            Order response from Binance
        """
        # Validate order
        is_valid, error = self.validate(symbol, quantity, price, side)
        if not is_valid:
            raise ValueError(f"Order validation failed: {error}")
        
        # Validate time in force
        from trading.validators import validate_time_in_force
        is_valid, error = validate_time_in_force(time_in_force)
        if not is_valid:
            raise ValueError(f"Time in force validation failed: {error}")
        
        logger.info(f"Executing LIMIT order: {side} {quantity} {symbol} @ {price}")
        
        result = self.client.place_limit_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            time_in_force=time_in_force,
            reduce_only=reduce_only
        )
        
        logger.info(f"Limit order placed: {result.get('orderId')} @ {price}")
        
        return result
    
    def wait_for_fill(self, symbol: str, order_id: int, timeout: int = 30,
                     check_interval: float = 1.0) -> Dict[str, Any]:
        """
        Wait for a limit order to be filled.
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to check
            timeout: Maximum time to wait in seconds
            check_interval: Time between checks in seconds
        
        Returns:
            Filled order details
        """
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            order = self.client.get_order(symbol, order_id=order_id)
            status = order.get('status', '').upper()
            
            if status == 'FILLED':
                logger.info(f"Order {order_id} filled")
                return order
            elif status in ['CANCELLED', 'EXPIRED', 'REJECTED']:
                logger.warning(f"Order {order_id} status: {status}")
                return order
            
            time.sleep(check_interval)
        
        logger.warning(f"Order {order_id} fill timeout after {timeout}s")
        return self.client.get_order(symbol, order_id=order_id)


class OrderManager:
    """Manager for handling multiple orders."""
    
    def __init__(self, client: BinanceClient):
        self.client = client
        self.market_order = MarketOrder(client)
        self.limit_order = LimitOrder(client)
    
    def get_market_price(self, symbol: str) -> float:
        """Get current market price."""
        return self.market_order.get_current_price(symbol)
    
    def place_market_order(self, symbol: str, side: str, quantity: float,
                          reduce_only: bool = False) -> Dict[str, Any]:
        """Place a market order."""
        return self.market_order.execute(symbol, side, quantity, reduce_only)
    
    def place_limit_order(self, symbol: str, side: str, quantity: float,
                         price: float, time_in_force: str = 'GTC',
                         reduce_only: bool = False) -> Dict[str, Any]:
        """Place a limit order."""
        return self.limit_order.execute(
            symbol, side, quantity, price, time_in_force, reduce_only
        )
    
    def get_open_orders(self, symbol: str = None) -> list:
        """Get all open orders."""
        return self.client.get_open_orders(symbol)
    
    def cancel_order(self, symbol: str, order_id: int = None,
                    client_order_id: str = None) -> Dict[str, Any]:
        """Cancel an order."""
        return self.client.cancel_order(symbol, order_id, client_order_id)
    
    def cancel_all_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """Cancel all open orders for a symbol."""
        return self.client.cancel_all_orders(symbol)
    
    def get_order_status(self, symbol: str, order_id: int = None,
                         client_order_id: str = None) -> Dict[str, Any]:
        """Get order status."""
        return self.client.get_order(symbol, order_id, client_order_id)


