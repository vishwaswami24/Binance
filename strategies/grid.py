"""
Grid trading strategy implementation.
Places automated buy/sell orders within a price range.
"""
import time
from typing import Dict, List, Optional, Any
from trading.client import BinanceClient
from trading.orders import LimitOrder
from trading.validators import validate_grid_parameters
from utils.logger import logger


class GridStrategy:
    """
    Grid trading strategy implementation.
    
    Places buy orders at the lower end of the price range and sell orders
    at the higher end. When price moves, orders are filled and new orders
    are placed to maintain the grid.
    """
    
    def __init__(self, client: BinanceClient):
        self.client = client
        self.limit_order = LimitOrder(client)
        self.is_running = False
        self.grid_orders = []
        self.filled_orders = []
        self.total_profit = 0.0
    
    def execute(self, symbol: str, min_price: float, max_price: float,
                grid_count: int, quantity_per_grid: float,
                price_precision: int = 2, max_runtime: int = 3600,
                check_interval: int = 5) -> Dict[str, Any]:
        """
        Execute a Grid trading strategy.
        
        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            min_price: Minimum price for the grid
            max_price: Maximum price for the grid
            grid_count: Number of grid levels
            quantity_per_grid: Quantity per grid level
            price_precision: Decimal precision for price
            max_runtime: Maximum runtime in seconds
            check_interval: Seconds between price checks
        
        Returns:
            Summary of grid execution
        """
        # Validate parameters
        is_valid, error = validate_grid_parameters(
            min_price, max_price, grid_count, quantity_per_grid
        )
        if not is_valid:
            raise ValueError(f"Grid validation failed: {error}")
        
        from trading.validators import validate_symbol
        is_valid, error = validate_symbol(symbol)
        if not is_valid:
            raise ValueError(f"Symbol validation failed: {error}")
        
        # Calculate grid step
        price_step = (max_price - min_price) / (grid_count - 1)
        
        logger.log_strategy("GRID", "START", {
            'symbol': symbol,
            'min_price': min_price,
            'max_price': max_price,
            'grid_count': grid_count,
            'price_step': price_step,
            'quantity_per_grid': quantity_per_grid
        })
        
        self.is_running = True
        self.grid_orders = []
        self.filled_orders = []
        self.total_profit = 0.0
        
        start_time = time.time()
        
        try:
            # Place initial grid orders
            self._place_initial_grid(
                symbol, min_price, max_price, grid_count, 
                quantity_per_grid, price_step, price_precision
            )
            
            # Monitor and maintain grid
            while self.is_running and (time.time() - start_time) < max_runtime:
                current_price = self.client.get_current_price(symbol)
                
                # Check if price is out of range
                if current_price < min_price or current_price > max_price:
                    logger.warning(
                        f"Price {current_price} is out of grid range "
                        f"[{min_price}, {max_price}]"
                    )
                    # Could add logic here to pause or adjust
                
                # Check filled orders and replace
                self._check_and_replace_filled_orders(
                    symbol, min_price, max_price, grid_count,
                    quantity_per_grid, price_step, price_precision
                )
                
                # Log status
                logger.debug(
                    f"Grid status: Price={current_price}, "
                    f"Active orders={len(self.grid_orders)}, "
                    f"Filled={len(self.filled_orders)}"
                )
                
                time.sleep(check_interval)
        
        except KeyboardInterrupt:
            logger.warning("Grid strategy interrupted by user")
        
        except Exception as e:
            logger.log_error("GRID_STRATEGY", str(e))
            raise
        
        finally:
            total_time = time.time() - start_time
            self.is_running = False
            
            summary = {
                'strategy': 'GRID',
                'symbol': symbol,
                'min_price': min_price,
                'max_price': max_price,
                'grid_count': grid_count,
                'total_time_seconds': round(total_time, 2),
                'orders_placed': len(self.grid_orders),
                'orders_filled': len(self.filled_orders),
                'total_profit': self.total_profit,
                'filled_orders': self.filled_orders
            }
            
            logger.log_strategy("GRID", "COMPLETE", summary)
        
        return summary
    
    def _place_initial_grid(self, symbol: str, min_price: float, max_price: float,
                           grid_count: int, quantity_per_grid: float,
                           price_step: float, price_precision: int):
        """Place initial grid of orders."""
        logger.info(f"Placing {grid_count} grid orders...")
        
        for i in range(grid_count):
            if not self.is_running:
                break
            
            grid_price = min_price + (i * price_step)
            grid_price = round(grid_price, price_precision)
            
            # Place SELL orders (above current price will fill first)
            # Place BUY orders (below current price will fill first)
            # Strategy: Place both sides
            
            # For simplicity, we'll alternate: even = BUY, odd = SELL
            # This creates a neutral grid
            side = 'BUY' if i % 2 == 0 else 'SELL'
            
            try:
                result = self.limit_order.execute(
                    symbol=symbol,
                    side=side,
                    quantity=quantity_per_grid,
                    price=grid_price,
                    time_in_force='GTC'
                )
                
                order_info = {
                    'grid_level': i,
                    'order_id': result.get('orderId'),
                    'side': side,
                    'price': grid_price,
                    'quantity': quantity_per_grid,
                    'status': 'PLACED'
                }
                
                self.grid_orders.append(order_info)
                
                logger.info(
                    f"Grid {i+1}/{grid_count}: {side} {quantity_per_grid} "
                    f"{symbol} @ {grid_price}"
                )
                
            except Exception as e:
                logger.log_error("GRID_PLACE", str(e), {
                    'grid_level': i,
                    'price': grid_price
                })
    
    def _check_and_replace_filled_orders(self, symbol: str, min_price: float,
                                         max_price: float, grid_count: int,
                                         quantity_per_grid: float,
                                         price_step: float, price_precision: int):
        """Check for filled orders and replace them."""
        # Get current grid prices
        current_price = self.client.get_current_price(symbol)
        
        # Find which grid level is closest to current price (for reference)
        current_level = int((current_price - min_price) / price_step)
        
        # Check each order
        orders_to_remove = []
        
        for order_info in self.grid_orders:
            try:
                order = self.client.get_order(
                    symbol, order_id=order_info['order_id']
                )
                status = order.get('status', '').upper()
                
                if status == 'FILLED':
                    logger.info(
                        f"Grid order filled: {order_info['side']} "
                        f"{order_info['quantity']} @ {order_info['price']}"
                    )
                    
                    # Record filled order
                    self.filled_orders.append({
                        **order_info,
                        'fill_price': order.get('price'),
                        'fill_time': time.time()
                    })
                    
                    # Calculate profit (for SELL fills, we make profit when price goes up)
                    if order_info['side'] == 'SELL':
                        # Simple profit calculation (can be enhanced)
                        pass
                    
                    orders_to_remove.append(order_info)
                    
                    # Place replacement order at the same level
                    grid_price = min_price + (order_info['grid_level'] * price_step)
                    grid_price = round(grid_price, price_precision)
                    
                    try:
                        result = self.limit_order.execute(
                            symbol=symbol,
                            side=order_info['side'],
                            quantity=quantity_per_grid,
                            price=grid_price,
                            time_in_force='GTC'
                        )
                        
                        new_order_info = {
                            'grid_level': order_info['grid_level'],
                            'order_id': result.get('orderId'),
                            'side': order_info['side'],
                            'price': grid_price,
                            'quantity': quantity_per_grid,
                            'status': 'PLACED'
                        }
                        
                        self.grid_orders.append(new_order_info)
                        
                    except Exception as e:
                        logger.log_error("GRID_REPLACE", str(e))
                
                elif status in ['CANCELLED', 'EXPIRED', 'REJECTED']:
                    logger.warning(f"Grid order {order_info['order_id']} {status}")
                    orders_to_remove.append(order_info)
            
            except Exception as e:
                logger.log_error("GRID_CHECK", str(e))
        
        # Remove filled/cancelled orders from active list
        for order_info in orders_to_remove:
            if order_info in self.grid_orders:
                self.grid_orders.remove(order_info)
    
    def stop(self):
        """Stop the running grid strategy."""
        logger.info("Stopping Grid strategy...")
        self.is_running = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the grid strategy."""
        return {
            'is_running': self.is_running,
            'active_orders': len(self.grid_orders),
            'filled_orders': len(self.filled_orders),
            'total_profit': self.total_profit,
            'orders': self.grid_orders
        }
    
    def cancel_all_grid_orders(self, symbol: str) -> int:
        """
        Cancel all grid orders.
        
        Returns:
            Number of orders cancelled
        """
        count = 0
        for order_info in self.grid_orders:
            try:
                self.client.cancel_order(symbol, order_id=order_info['order_id'])
                count += 1
            except Exception as e:
                logger.log_error("GRID_CANCEL", str(e), {
                    'order_id': order_info['order_id']
                })
        
        self.grid_orders.clear()
        logger.info(f"Cancelled {count} grid orders")
        return count


def run_grid_demo(client: BinanceClient):
    """
    Demo function for Grid strategy.
    
    Args:
        client: BinanceClient instance
    """
    print("\n" + "="*60)
    print("Grid Trading Strategy Demo")
    print("="*60 + "\n")
    
    # Get inputs
    symbol = input("Enter symbol (default: BTCUSDT): ").strip() or "BTCUSDT"
    
    try:
        current_price = client.get_current_price(symbol)
        print(f"Current {symbol} price: {current_price}")
    except Exception as e:
        print(f"Error getting price: {e}")
        return
    
    try:
        min_price = float(input(f"Enter min price (default: {current_price * 0.95:.2f}): ") 
                         or str(current_price * 0.95))
        max_price = float(input(f"Enter max price (default: {current_price * 1.05:.2f}): ") 
                         or str(current_price * 1.05))
        grid_count = int(input("Enter grid count (default: 5): ") or "5")
        quantity = float(input("Enter quantity per grid: "))
        runtime = int(input("Enter runtime in seconds (default: 60): ") or "60")
    except ValueError:
        print("Invalid numeric input")
        return
    
    if min_price >= max_price:
        print("Min price must be less than max price")
        return
    
    print(f"\nGrid Strategy Configuration:")
    print(f"  Symbol: {symbol}")
    print(f"  Price Range: {min_price} - {max_price}")
    print(f"  Grid Count: {grid_count}")
    print(f"  Price Step: {(max_price - min_price) / (grid_count - 1):.4f}")
    print(f"  Quantity per grid: {quantity}")
    print(f"  Runtime: {runtime}s")
    
    confirm = input("\nStart Grid strategy? (y/n): ").strip().lower()
    if confirm != 'y':
        return
    
    # Run Grid
    grid = GridStrategy(client)
    
    try:
        result = grid.execute(
            symbol=symbol,
            min_price=min_price,
            max_price=max_price,
            grid_count=grid_count,
            quantity_per_grid=quantity,
            price_precision=2,
            max_runtime=runtime
        )
        
        print("\n" + "="*60)
        print("Grid Execution Summary")
        print("="*60)
        print(f"Total time: {result['total_time_seconds']}s")
        print(f"Orders placed: {result['orders_placed']}")
        print(f"Orders filled: {result['orders_filled']}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Cleanup: cancel remaining orders
        if grid.get_status()['is_running']:
            grid.stop()
        cancel_count = grid.cancel_all_grid_orders(symbol)
        print(f"\nCancelled {cancel_count} remaining grid orders")
