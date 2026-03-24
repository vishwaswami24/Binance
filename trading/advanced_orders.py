"""
Advanced order implementations for the Binance Trading Bot.
Handles Stop-Limit and OCO orders.
"""
from typing import Dict, Optional, Any, List
import time
from trading.client import BinanceClient
from trading.validators import (
    validate_symbol, validate_quantity, validate_price,
    validate_side, validate_notional, validate_stop_price
)
from utils.logger import logger


class StopLimitOrder:
    """Stop-Limit order implementation."""
    
    def __init__(self, client: BinanceClient):
        self.client = client
    
    def execute(self, symbol: str, side: str, quantity: float,
                stop_price: float, limit_price: float,
                time_in_force: str = 'GTC') -> Dict[str, Any]:
        """
        Execute a stop-limit order.
        
        Args:
            symbol: Trading pair symbol
            side: BUY or SELL
            quantity: Order quantity
            stop_price: Price at which order triggers
            limit_price: Price for the limit order when triggered
            time_in_force: GTC, IOC, FOK
        
        Returns:
            Order response from Binance
        """
        # Validate basic parameters
        from trading.validators import validate_time_in_force
        
        is_valid, error = validate_symbol(symbol)
        if not is_valid:
            raise ValueError(f"Symbol validation failed: {error}")
        
        is_valid, error = validate_side(side)
        if not is_valid:
            raise ValueError(f"Side validation failed: {error}")
        
        is_valid, error = validate_quantity(quantity)
        if not is_valid:
            raise ValueError(f"Quantity validation failed: {error}")
        
        is_valid, error = validate_price(limit_price)
        if not is_valid:
            raise ValueError(f"Limit price validation failed: {error}")
        
        is_valid, error = validate_stop_price(stop_price, limit_price, side)
        if not is_valid:
            raise ValueError(f"Stop price validation failed: {error}")
        
        is_valid, error = validate_time_in_force(time_in_force)
        if not is_valid:
            raise ValueError(f"Time in force validation failed: {error}")
        
        logger.info(f"Executing STOP-LIMIT order: {side} {quantity} {symbol}")
        logger.info(f"  Stop Price: {stop_price}, Limit Price: {limit_price}")
        
        result = self.client.place_stop_limit_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            stop_price=stop_price,
            limit_price=limit_price,
            time_in_force=time_in_force
        )
        
        logger.info(f"Stop-Limit order placed: {result.get('orderId')}")
        
        return result
    
    def wait_for_trigger(self, symbol: str, order_id: int, timeout: int = 300,
                        check_interval: float = 2.0) -> Dict[str, Any]:
        """
        Wait for a stop-limit order to be triggered.
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to check
            timeout: Maximum time to wait in seconds
            check_interval: Time between checks in seconds
        
        Returns:
            Order status
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            order = self.client.get_order(symbol, order_id=order_id)
            status = order.get('status', '').upper()
            
            if status in ['FILLED', 'PARTIALLY_FILLED']:
                logger.info(f"Stop-Limit order {order_id} triggered/filled")
                return order
            elif status in ['CANCELLED', 'EXPIRED', 'REJECTED']:
                logger.warning(f"Stop-Limit order {order_id} status: {status}")
                return order
            
            time.sleep(check_interval)
        
        logger.warning(f"Stop-Limit order {order_id} trigger timeout after {timeout}s")
        return self.client.get_order(symbol, order_id=order_id)


class OCOOrder:
    """OCO (One-Cancels-the-Other) order implementation."""
    
    def __init__(self, client: BinanceClient):
        self.client = client
    
    def execute(self, symbol: str, side: str, quantity: float,
                limit_price: float, stop_price: float,
                list_client_order_id: str = None) -> Dict[str, Any]:
        """
        Execute an OCO order.
        
        An OCO order places a limit order and a stop-limit order simultaneously.
        When one is triggered, the other is automatically cancelled.
        
        Args:
            symbol: Trading pair symbol
            side: BUY or SELL
            quantity: Total quantity (split between both orders)
            limit_price: Take-profit limit price
            stop_price: Stop-loss trigger price
            list_client_order_id: Optional client order ID for the OCO
        
        Returns:
            OCO order response from Binance
        """
        # Validate parameters
        is_valid, error = validate_symbol(symbol)
        if not is_valid:
            raise ValueError(f"Symbol validation failed: {error}")
        
        is_valid, error = validate_side(side)
        if not is_valid:
            raise ValueError(f"Side validation failed: {error}")
        
        is_valid, error = validate_quantity(quantity)
        if not is_valid:
            raise ValueError(f"Quantity validation failed: {error}")
        
        is_valid, error = validate_price(limit_price)
        if not is_valid:
            raise ValueError(f"Limit price validation failed: {error}")
        
        is_valid, error = validate_price(stop_price)
        if not is_valid:
            raise ValueError(f"Stop price validation failed: {error}")
        
        # For OCO, stop price should be on the opposite side of limit price
        # For SELL: limit_price > stop_price (take profit higher, stop loss lower)
        # For BUY: limit_price < stop_price (take profit lower, stop loss higher)
        side_upper = side.upper()
        if side_upper == 'SELL':
            if limit_price <= stop_price:
                raise ValueError(
                    "For SELL OCO: limit_price must be > stop_price "
                    f"(got limit={limit_price}, stop={stop_price})"
                )
        else:  # BUY
            if limit_price >= stop_price:
                raise ValueError(
                    "For BUY OCO: limit_price must be < stop_price "
                    f"(got limit={limit_price}, stop={stop_price})"
                )
        
        logger.info(f"Executing OCO order: {side} {quantity} {symbol}")
        logger.info(f"  Limit Price (Take Profit): {limit_price}")
        logger.info(f"  Stop Price (Stop Loss): {stop_price}")
        
        result = self.client.place_oco_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
            list_client_order_id=list_client_order_id
        )
        
        order_list_id = result.get('listClientOrderId', 'N/A')
        logger.info(f"OCO order placed: {order_list_id}")
        
        # Log the individual orders
        if 'orders' in result:
            for order in result['orders']:
                logger.info(f"  OCO sub-order: {order.get('orderId')} @ {order.get('price')}")
        
        return result
    
    def get_oco_status(self, symbol: str, order_list_id: str = None) -> Dict[str, Any]:
        """
        Get OCO order status.
        
        Args:
            symbol: Trading pair symbol
            order_list_id: The OCO order list ID
        
        Returns:
            OCO order details
        """
        try:
            # Get all orders for the symbol and filter for OCO orders
            orders = self.client.get_all_orders(symbol)
            
            # Look for orders with same list client order ID
            oco_orders = [o for o in orders if o.get('orderListId')]
            
            return {
                'order_list_id': order_list_id,
                'orders': oco_orders,
                'status': 'ACTIVE' if oco_orders else 'COMPLETED'
            }
        except Exception as e:
            logger.log_error("GET_OCO_STATUS", str(e))
            raise


class AdvancedOrderManager:
    """Manager for advanced order types."""
    
    def __init__(self, client: BinanceClient):
        self.client = client
        self.stop_limit = StopLimitOrder(client)
        self.oco = OCOOrder(client)
    
    def place_stop_limit_order(self, symbol: str, side: str, quantity: float,
                              stop_price: float, limit_price: float,
                              time_in_force: str = 'GTC') -> Dict[str, Any]:
        """Place a stop-limit order."""
        return self.stop_limit.execute(
            symbol, side, quantity, stop_price, limit_price, time_in_force
        )
    
    def place_oco_order(self, symbol: str, side: str, quantity: float,
                       limit_price: float, stop_price: float,
                       list_client_order_id: str = None) -> Dict[str, Any]:
        """Place an OCO order."""
        return self.oco.execute(
            symbol, side, quantity, limit_price, stop_price, list_client_order_id
        )
    
    def wait_for_stop_trigger(self, symbol: str, order_id: int,
                             timeout: int = 300) -> Dict[str, Any]:
        """Wait for stop-limit order to trigger."""
        return self.stop_limit.wait_for_trigger(symbol, order_id, timeout)
