"""
TWAP (Time-Weighted Average Price) strategy implementation.
Splits large orders into smaller chunks over time.
"""
import time
from typing import Dict, List, Optional, Any
from trading.client import BinanceClient
from trading.orders import LimitOrder
from trading.validators import validate_twap_parameters
from utils.logger import logger


class TWAPStrategy:
    """
    TWAP Strategy implementation.
    
    Splits a large order into equal smaller orders executed at regular intervals.
    The goal is to get an average price closer to the market price while reducing
    market impact.
    """
    
    def __init__(self, client: BinanceClient):
        self.client = client
        self.limit_order = LimitOrder(client)
        self.is_running = False
        self.executed_orders = []
    
    def execute(self, symbol: str, side: str, total_quantity: float,
                intervals: int = 10, interval_seconds: int = 60,
                price_offset: float = 0.0, wait_for_fill: bool = False,
                price_precision: int = 2) -> Dict[str, Any]:
        """
        Execute a TWAP strategy.
        
        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            side: BUY or SELL
            total_quantity: Total quantity to trade
            intervals: Number of intervals (orders to place)
            interval_seconds: Seconds between each order
            price_offset: Offset from market price (positive = worse price)
            wait_for_fill: Whether to wait for each order to fill before placing next
            price_precision: Decimal precision for price
        
        Returns:
            Summary of executed orders
        """
        # Validate parameters
        is_valid, error = validate_twap_parameters(total_quantity, intervals, interval_seconds)
        if not is_valid:
            raise ValueError(f"TWAP validation failed: {error}")
        
        from trading.validators import validate_side, validate_symbol
        
        is_valid, error = validate_symbol(symbol)
        if not is_valid:
            raise ValueError(f"Symbol validation failed: {error}")
        
        is_valid, error = validate_side(side)
        if not is_valid:
            raise ValueError(f"Side validation failed: {error}")
        
        # Calculate quantity per order
        quantity_per_order = total_quantity / intervals
        
        logger.log_strategy("TWAP", "START", {
            'symbol': symbol,
            'side': side,
            'total_quantity': total_quantity,
            'intervals': intervals,
            'interval_seconds': interval_seconds,
            'quantity_per_order': quantity_per_order
        })
        
        self.is_running = True
        self.executed_orders = []
        
        start_time = time.time()
        
        try:
            for i in range(intervals):
                if not self.is_running:
                    logger.log_strategy("TWAP", "STOPPED", {
                        'interval': i + 1,
                        'total_intervals': intervals
                    })
                    break
                
                # Get current market price
                current_price = self.client.get_current_price(symbol)
                
                # Calculate order price with offset
                # For BUY: subtract offset (pay less), for SELL: add offset (get more)
                if side.upper() == 'BUY':
                    order_price = current_price - price_offset
                else:
                    order_price = current_price + price_offset
                
                # Round price to precision
                order_price = round(order_price, price_precision)
                
                logger.log_strategy("TWAP", "PLACE_ORDER", {
                    'interval': i + 1,
                    'quantity': quantity_per_order,
                    'price': order_price,
                    'market_price': current_price
                })
                
                try:
                    # Place the limit order
                    result = self.limit_order.execute(
                        symbol=symbol,
                        side=side,
                        quantity=quantity_per_order,
                        price=order_price,
                        time_in_force='GTC'
                    )
                    
                    order_info = {
                        'interval': i + 1,
                        'order_id': result.get('orderId'),
                        'price': order_price,
                        'quantity': quantity_per_order,
                        'status': 'PLACED',
                        'timestamp': time.time()
                    }
                    
                    self.executed_orders.append(order_info)
                    
                    logger.info(
                        f"TWAP Order {i+1}/{intervals}: "
                        f"{side} {quantity_per_order} {symbol} @ {order_price}"
                    )
                    
                    # Wait for fill if requested
                    if wait_for_fill:
                        order = self.limit_order.wait_for_fill(
                            symbol, result.get('orderId'), timeout=60
                        )
                        order_info['status'] = order.get('status', 'UNKNOWN')
                        order_info['filled_price'] = order.get('price')
                        logger.info(f"  Order filled: {order.get('status')}")
                    
                except Exception as e:
                    logger.log_error("TWAP_ORDER", str(e), {
                        'interval': i + 1,
                        'price': order_price,
                        'quantity': quantity_per_order
                    })
                    order_info = {
                        'interval': i + 1,
                        'status': 'FAILED',
                        'error': str(e)
                    }
                    self.executed_orders.append(order_info)
                
                # Wait for next interval (except after last order)
                if i < intervals - 1:
                    logger.debug(f"TWAP: Waiting {interval_seconds}s before next order")
                    time.sleep(interval_seconds)
        
        except KeyboardInterrupt:
            logger.warning("TWAP strategy interrupted by user")
            self.is_running = False
        
        except Exception as e:
            logger.log_error("TWAP_STRATEGY", str(e))
            raise
        
        finally:
            total_time = time.time() - start_time
            self.is_running = False
            
            # Calculate summary
            filled_orders = [o for o in self.executed_orders if o.get('status') == 'FILLED']
            summary = {
                'strategy': 'TWAP',
                'symbol': symbol,
                'side': side,
                'total_quantity': total_quantity,
                'intervals': intervals,
                'intervals_executed': len(self.executed_orders),
                'orders_filled': len(filled_orders),
                'total_time_seconds': round(total_time, 2),
                'orders': self.executed_orders
            }
            
            logger.log_strategy("TWAP", "COMPLETE", summary)
        
        return summary
    
    def stop(self):
        """Stop the running TWAP strategy."""
        logger.info("Stopping TWAP strategy...")
        self.is_running = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the TWAP strategy."""
        return {
            'is_running': self.is_running,
            'executed_orders': len(self.executed_orders),
            'orders': self.executed_orders
        }
    
    def get_average_price(self) -> Optional[float]:
        """Calculate average execution price from filled orders."""
        filled_orders = [
            o for o in self.executed_orders 
            if o.get('status') == 'FILLED' and o.get('price')
        ]
        
        if not filled_orders:
            return None
        
        total_price = sum(o['price'] * o.get('quantity', 0) for o in filled_orders)
        total_qty = sum(o.get('quantity', 0) for o in filled_orders)
        
        if total_qty == 0:
            return None
        
        return total_price / total_qty


def run_twap_demo(client: BinanceClient):
    """
    Demo function for TWAP strategy.
    
    Args:
        client: BinanceClient instance
    """
    from utils import formatters
    
    print("\n" + "="*60)
    print("TWAP Strategy Demo")
    print("="*60 + "\n")
    
    # Get inputs
    symbol = input("Enter symbol (default: BTCUSDT): ").strip() or "BTCUSDT"
    
    try:
        current_price = client.get_current_price(symbol)
        print(f"Current {symbol} price: {current_price}")
    except Exception as e:
        print(f"Error getting price: {e}")
        return
    
    side = input("Enter side (BUY/SELL): ").strip().upper()
    if side not in ['BUY', 'SELL']:
        print("Invalid side")
        return
    
    try:
        quantity = float(input("Enter total quantity: "))
        intervals = int(input("Enter number of intervals (default: 5): ") or "5")
        interval_seconds = int(input("Enter seconds between intervals (default: 10): ") or "10")
    except ValueError:
        print("Invalid numeric input")
        return
    
    print(f"\nTWAP Strategy Configuration:")
    print(f"  Symbol: {symbol}")
    print(f"  Side: {side}")
    print(f"  Total Quantity: {quantity}")
    print(f"  Intervals: {intervals}")
    print(f"  Interval: {interval_seconds}s")
    print(f"  Quantity per order: {quantity/intervals}")
    
    confirm = input("\nStart TWAP strategy? (y/n): ").strip().lower()
    if confirm != 'y':
        return
    
    # Run TWAP
    twap = TWAPStrategy(client)
    
    try:
        result = twap.execute(
            symbol=symbol,
            side=side,
            total_quantity=quantity,
            intervals=intervals,
            interval_seconds=interval_seconds,
            wait_for_fill=False
        )
        
        print("\n" + "="*60)
        print("TWAP Execution Summary")
        print("="*60)
        print(f"Total orders placed: {result['intervals_executed']}")
        print(f"Total time: {result['total_time_seconds']}s")
        
    except Exception as e:
        print(f"Error: {e}")
