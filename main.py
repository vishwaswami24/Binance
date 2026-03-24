#!/usr/bin/env python3
"""
Binance USDT-M Futures Trading Bot
CLI-based trading bot with support for multiple order types

Usage:
    python main.py
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, Optional
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

from config import (
    BINANCE_API_KEY, BINANCE_SECRET_KEY, TESTNET, DEFAULT_SYMBOL,
    DEFAULT_TIME_IN_FORCE, DEFAULT_WORKING_TYPE
)
from trading.client import BinanceClient
from trading.orders import OrderManager
from trading.advanced_orders import AdvancedOrderManager
from trading.validators import validate_api_keys
from strategies.twap import TWAPStrategy
from strategies.grid import GridStrategy
from utils.logger import logger
from utils import formatters


class TradingBot:
    """Main trading bot class with CLI interface."""
    
    def __init__(self):
        self.client: Optional[BinanceClient] = None
        self.order_manager: Optional[OrderManager] = None
        self.advanced_manager: Optional[AdvancedOrderManager] = None
        self.is_connected = False
    
    def initialize(self) -> bool:
        """Initialize the trading bot."""
        formatters.print_header("Binance USDT-M Futures Trading Bot")
        
        # Check API keys
        is_valid, error = validate_api_keys(BINANCE_API_KEY, BINANCE_SECRET_KEY)
        if not is_valid:
            formatters.print_error(f"API Configuration Error: {error}")
            formatters.print_info("Please configure your API keys in .env file")
            formatters.print_info("Copy .env.example to .env and add your credentials")
            return False
        
        try:
            # Initialize client
            self.client = BinanceClient()
            
            # Test connection
            if self.client.ping():
                formatters.print_success("Connected to Binance Futures API")
                if TESTNET:
                    formatters.print_warning("Using TESTNET")
                else:
                    formatters.print_warning("Using PRODUCTION")
                
                # Initialize order managers
                self.order_manager = OrderManager(self.client)
                self.advanced_manager = AdvancedOrderManager(self.client)
                
                self.is_connected = True
                return True
            else:
                formatters.print_error("Failed to connect to Binance")
                return False
                
        except Exception as e:
            formatters.print_error(f"Initialization failed: {str(e)}")
            logger.log_error("INIT", str(e))
            return False
    
    def get_balance(self):
        """Display account balance."""
        try:
            balances = self.client.get_account_balance()
            if balances:
                formatters.print_balance(balances[0])
            else:
                formatters.print_warning("No balance information available")
        except Exception as e:
            formatters.print_error(f"Failed to get balance: {str(e)}")
    
    def get_current_price(self, symbol: str = None):
        """Display current price for a symbol."""
        symbol = symbol or DEFAULT_SYMBOL
        try:
            ticker = self.client.get_ticker(symbol)
            formatters.print_ticker(ticker)
        except Exception as e:
            formatters.print_error(f"Failed to get price: {str(e)}")
    
    def place_market_order(self):
        """Place a market order."""
        formatters.print_header("Place Market Order")
        
        symbol = input(f"Symbol (default: {DEFAULT_SYMBOL}): ").strip() or DEFAULT_SYMBOL
        side = input("Side (BUY/SELL): ").strip().upper()
        
        if side not in ['BUY', 'SELL']:
            formatters.print_error("Invalid side")
            return
        
        try:
            quantity = float(input("Quantity: "))
        except ValueError:
            formatters.print_error("Invalid quantity")
            return
        
        # Show current price for reference
        try:
            current_price = self.client.get_current_price(symbol)
            notional = quantity * current_price
            print(f"\nCurrent Price: {current_price}")
            print(f"Estimated Notional: {notional} USDT")
        except:
            pass
        
        confirm = input("\nConfirm order? (y/n): ").strip().lower()
        if confirm != 'y':
            formatters.print_info("Order cancelled")
            return
        
        try:
            result = self.order_manager.place_market_order(symbol, side, quantity)
            formatters.print_success(f"Market order placed: {result.get('orderId')}")
            formatters.print_order_details(result)
        except Exception as e:
            formatters.print_error(f"Order failed: {str(e)}")
    
    def place_limit_order(self):
        """Place a limit order."""
        formatters.print_header("Place Limit Order")
        
        symbol = input(f"Symbol (default: {DEFAULT_SYMBOL}): ").strip() or DEFAULT_SYMBOL
        side = input("Side (BUY/SELL): ").strip().upper()
        
        if side not in ['BUY', 'SELL']:
            formatters.print_error("Invalid side")
            return
        
        try:
            quantity = float(input("Quantity: "))
            price = float(input("Limit Price: "))
        except ValueError:
            formatters.print_error("Invalid input")
            return
        
        # Show current price for reference
        try:
            current_price = self.client.get_current_price(symbol)
            print(f"\nCurrent Price: {current_price}")
            print(f"Your Price: {price}")
            print(f"Price Difference: {((price - current_price) / current_price * 100):+.2f}%")
        except:
            pass
        
        tif = input("Time in Force (GTC/IOC/FOK, default: GTC): ").strip().upper() or "GTC"
        
        confirm = input("\nConfirm order? (y/n): ").strip().lower()
        if confirm != 'y':
            formatters.print_info("Order cancelled")
            return
        
        try:
            result = self.order_manager.place_limit_order(symbol, side, quantity, price, tif)
            formatters.print_success(f"Limit order placed: {result.get('orderId')}")
            formatters.print_order_details(result)
        except Exception as e:
            formatters.print_error(f"Order failed: {str(e)}")
    
    def place_stop_limit_order(self):
        """Place a stop-limit order."""
        formatters.print_header("Place Stop-Limit Order")
        
        symbol = input(f"Symbol (default: {DEFAULT_SYMBOL}): ").strip() or DEFAULT_SYMBOL
        side = input("Side (BUY/SELL): ").strip().upper()
        
        if side not in ['BUY', 'SELL']:
            formatters.print_error("Invalid side")
            return
        
        try:
            quantity = float(input("Quantity: "))
            stop_price = float(input("Stop Price: "))
            limit_price = float(input("Limit Price: "))
        except ValueError:
            formatters.print_error("Invalid input")
            return
        
        print(f"\nStop Price: {stop_price}")
        print(f"Limit Price: {limit_price}")
        
        if side == 'BUY':
            if stop_price < limit_price:
                formatters.print_warning("For BUY: Stop price should be >= Limit price")
        else:
            if stop_price > limit_price:
                formatters.print_warning("For SELL: Stop price should be <= Limit price")
        
        tif = input("Time in Force (GTC/IOC/FOK, default: GTC): ").strip().upper() or "GTC"
        
        confirm = input("\nConfirm order? (y/n): ").strip().lower()
        if confirm != 'y':
            formatters.print_info("Order cancelled")
            return
        
        try:
            result = self.advanced_manager.place_stop_limit_order(
                symbol, side, quantity, stop_price, limit_price, tif
            )
            formatters.print_success(f"Stop-Limit order placed: {result.get('orderId')}")
            formatters.print_order_details(result)
        except Exception as e:
            formatters.print_error(f"Order failed: {str(e)}")
    
    def place_oco_order(self):
        """Place an OCO (One-Cancels-the-Other) order."""
        formatters.print_header("Place OCO Order")
        
        symbol = input(f"Symbol (default: {DEFAULT_SYMBOL}): ").strip() or DEFAULT_SYMBOL
        side = input("Side (BUY/SELL): ").strip().upper()
        
        if side not in ['BUY', 'SELL']:
            formatters.print_error("Invalid side")
            return
        
        try:
            quantity = float(input("Total Quantity: "))
            take_profit_price = float(input("Take Profit Price: "))
            stop_loss_price = float(input("Stop Loss Price: "))
        except ValueError:
            formatters.print_error("Invalid input")
            return
        
        print(f"\nTake Profit Price: {take_profit_price}")
        print(f"Stop Loss Price: {stop_loss_price}")
        
        # Validate the prices
        if side == 'SELL':
            if take_profit_price <= stop_loss_price:
                formatters.print_error("For SELL: Take profit must be > Stop loss")
                return
        else:
            if take_profit_price >= stop_loss_price:
                formatters.print_error("For BUY: Take profit must be < Stop loss")
                return
        
        confirm = input("\nConfirm order? (y/n): ").strip().lower()
        if confirm != 'y':
            formatters.print_info("Order cancelled")
            return
        
        try:
            result = self.advanced_manager.place_oco_order(
                symbol, side, quantity, take_profit_price, stop_loss_price
            )
            formatters.print_success(f"OCO order placed")
            if 'orderReports' in result:
                for order in result['orderReports']:
                    print(f"  Order ID: {order.get('orderId')}")
                    print(f"  Type: {order.get('type')}")
                    print(f"  Price: {order.get('price')}")
        except Exception as e:
            formatters.print_error(f"Order failed: {str(e)}")
    
    def run_twap(self):
        """Run TWAP strategy."""
        formatters.print_header("TWAP Strategy")
        
        symbol = input(f"Symbol (default: {DEFAULT_SYMBOL}): ").strip() or DEFAULT_SYMBOL
        side = input("Side (BUY/SELL): ").strip().upper()
        
        if side not in ['BUY', 'SELL']:
            formatters.print_error("Invalid side")
            return
        
        try:
            quantity = float(input("Total Quantity: "))
            intervals = int(input("Number of intervals (default: 10): ") or "10")
            interval_seconds = int(input("Seconds between intervals (default: 60): ") or "60")
        except ValueError:
            formatters.print_error("Invalid input")
            return
        
        # Show configuration
        try:
            current_price = self.client.get_current_price(symbol)
            print(f"\nCurrent Price: {current_price}")
            print(f"Quantity per interval: {quantity / intervals}")
            print(f"Total intervals: {intervals}")
            print(f"Estimated total time: {intervals * interval_seconds}s")
        except:
            pass
        
        confirm = input("\nStart TWAP? (y/n): ").strip().lower()
        if confirm != 'y':
            formatters.print_info("Cancelled")
            return
        
        formatters.print_info("Starting TWAP strategy... Press Ctrl+C to stop")
        
        try:
            twap = TWAPStrategy(self.client)
            result = twap.execute(
                symbol=symbol,
                side=side,
                total_quantity=quantity,
                intervals=intervals,
                interval_seconds=interval_seconds,
                wait_for_fill=False
            )
            
            formatters.print_success("TWAP Strategy Complete")
            print(f"Orders placed: {result['intervals_executed']}")
            print(f"Total time: {result['total_time_seconds']}s")
            
        except Exception as e:
            formatters.print_error(f"TWAP failed: {str(e)}")
    
    def run_grid(self):
        """Run Grid trading strategy."""
        formatters.print_header("Grid Trading Strategy")
        
        symbol = input(f"Symbol (default: {DEFAULT_SYMBOL}): ").strip() or DEFAULT_SYMBOL
        
        try:
            current_price = self.client.get_current_price(symbol)
            print(f"Current Price: {current_price}")
            
            min_price = float(input(f"Min price (default: {current_price * 0.95:.2f}): ") 
                            or str(current_price * 0.95))
            max_price = float(input(f"Max price (default: {current_price * 1.05:.2f}): ") 
                            or str(current_price * 1.05))
            grid_count = int(input("Grid count (default: 5): ") or "5")
            quantity = float(input("Quantity per grid: "))
        except ValueError:
            formatters.print_error("Invalid input")
            return
        
        runtime = int(input("Runtime in seconds (default: 60): ") or "60")
        
        if min_price >= max_price:
            formatters.print_error("Min price must be less than max price")
            return
        
        print(f"\nPrice Step: {(max_price - min_price) / (grid_count - 1):.4f}")
        
        confirm = input("\nStart Grid? (y/n): ").strip().lower()
        if confirm != 'y':
            formatters.print_info("Cancelled")
            return
        
        formatters.print_info("Starting Grid strategy... Press Ctrl+C to stop")
        
        grid = None
        try:
            grid = GridStrategy(self.client)
            result = grid.execute(
                symbol=symbol,
                min_price=min_price,
                max_price=max_price,
                grid_count=grid_count,
                quantity_per_grid=quantity,
                max_runtime=runtime
            )
            
            formatters.print_success("Grid Strategy Complete")
            print(f"Orders placed: {result['orders_placed']}")
            print(f"Orders filled: {result['orders_filled']}")
            
        except Exception as e:
            formatters.print_error(f"Grid failed: {str(e)}")
        
        finally:
            if grid:
                grid.stop()
                grid.cancel_all_grid_orders(symbol)
    
    def view_open_orders(self):
        """View open orders."""
        formatters.print_header("Open Orders")
        
        symbol = input(f"Symbol (optional, leave empty for all): ").strip()
        
        try:
            orders = self.order_manager.get_open_orders(symbol if symbol else None)
            if orders:
                formatters.print_order_table(orders)
            else:
                formatters.print_warning("No open orders")
        except Exception as e:
            formatters.print_error(f"Failed to get orders: {str(e)}")
    
    def cancel_order(self):
        """Cancel an order."""
        formatters.print_header("Cancel Order")
        
        symbol = input(f"Symbol: ").strip()
        if not symbol:
            formatters.print_error("Symbol is required")
            return
        
        try:
            order_id = int(input("Order ID: "))
        except ValueError:
            formatters.print_error("Invalid order ID")
            return
        
        confirm = input(f"Cancel order {order_id}? (y/n): ").strip().lower()
        if confirm != 'y':
            formatters.print_info("Cancelled")
            return
        
        try:
            result = self.order_manager.cancel_order(symbol, order_id=order_id)
            formatters.print_success(f"Order {order_id} cancelled")
        except Exception as e:
            formatters.print_error(f"Cancellation failed: {str(e)}")
    
    def cancel_all_orders(self):
        """Cancel all orders for a symbol."""
        formatters.print_header("Cancel All Orders")
        
        symbol = input(f"Symbol: ").strip()
        if not symbol:
            formatters.print_error("Symbol is required")
            return
        
        confirm = input(f"Cancel ALL orders for {symbol}? (y/n): ").strip().lower()
        if confirm != 'y':
            formatters.print_info("Cancelled")
            return
        
        try:
            result = self.order_manager.cancel_all_orders(symbol)
            formatters.print_success(f"All orders cancelled for {symbol}")
        except Exception as e:
            formatters.print_error(f"Cancellation failed: {str(e)}")
    
    def run(self):
        """Main run loop."""
        if not self.initialize():
            return
        
        menu_options = [
            ("1", "View Account Balance"),
            ("2", "View Current Price"),
            ("3", "Place Market Order"),
            ("4", "Place Limit Order"),
            ("5", "Place Stop-Limit Order"),
            ("6", "Place OCO Order"),
            ("7", "Run TWAP Strategy"),
            ("8", "Run Grid Strategy"),
            ("9", "View Open Orders"),
            ("10", "Cancel Order"),
            ("11", "Cancel All Orders"),
            ("12", "Set Leverage"),
            ("q", "Quit"),
        ]
        
        while True:
            formatters.print_menu(menu_options)
            
            choice = input(f"{Fore.CYAN}Enter your choice: {Style.RESET_ALL}").strip().lower()
            
            if choice == 'q' or choice == 'quit':
                formatters.print_info("Goodbye!")
                break
            
            try:
                if choice == '1':
                    self.get_balance()
                elif choice == '2':
                    symbol = input(f"Symbol (default: {DEFAULT_SYMBOL}): ").strip() or DEFAULT_SYMBOL
                    self.get_current_price(symbol)
                elif choice == '3':
                    self.place_market_order()
                elif choice == '4':
                    self.place_limit_order()
                elif choice == '5':
                    self.place_stop_limit_order()
                elif choice == '6':
                    self.place_oco_order()
                elif choice == '7':
                    self.run_twap()
                elif choice == '8':
                    self.run_grid()
                elif choice == '9':
                    self.view_open_orders()
                elif choice == '10':
                    self.cancel_order()
                elif choice == '11':
                    self.cancel_all_orders()
                elif choice == '12':
                    self.set_leverage()
                else:
                    formatters.print_warning("Invalid choice")
            except KeyboardInterrupt:
                formatters.print_info("\nInterrupted. Press 'q' to quit.")
            except Exception as e:
                formatters.print_error(f"Error: {str(e)}")
                logger.log_error("MENU", str(e))
    
    def set_leverage(self):
        """Set leverage for a symbol."""
        formatters.print_header("Set Leverage")
        
        symbol = input(f"Symbol (default: {DEFAULT_SYMBOL}): ").strip() or DEFAULT_SYMBOL
        
        try:
            leverage = int(input("Leverage (1-125): "))
        except ValueError:
            formatters.print_error("Invalid leverage")
            return
        
        if leverage < 1 or leverage > 125:
            formatters.print_error("Leverage must be between 1 and 125")
            return
        
        confirm = input(f"Set leverage to {leverage}x for {symbol}? (y/n): ").strip().lower()
        if confirm != 'y':
            formatters.print_info("Cancelled")
            return
        
        try:
            result = self.client.set_leverage(symbol, leverage)
            formatters.print_success(f"Leverage set to {leverage}x")
        except Exception as e:
            formatters.print_error(f"Failed: {str(e)}")


def main():
    """Main entry point."""
    bot = TradingBot()
    bot.run()


if __name__ == "__main__":
    main()
