"""
Binance API Client wrapper for the Trading Bot.
Handles all communication with Binance Futures API.
"""
from typing import Dict, List, Optional, Any
from binance.client import Client
from binance.exceptions import BinanceAPIException
from config import BINANCE_API_KEY, BINANCE_SECRET_KEY, TESTNET, DEFAULT_SYMBOL
from utils.logger import logger
from utils import formatters
from trading.retry import with_retry


class BinanceClient:
    """Wrapper class for Binance Futures API client."""
    
    # URLs handled by python-binance testnet param

    
    def __init__(self, api_key: str = None, secret_key: str = None, testnet: bool = None):
        """
        Initialize Binance client.
        
        Args:
            api_key: Binance API key (optional, uses config if not provided)
            secret_key: Binance API secret (optional, uses config if not provided)
            testnet: Whether to use testnet (optional, uses config if not provided)
        """
        self.api_key = api_key or BINANCE_API_KEY
        self.secret_key = secret_key or BINANCE_SECRET_KEY
        self.testnet = testnet if testnet is not None else TESTNET
        
        # Set base URL based on testnet setting
        try:
            self.client = Client(self.api_key, self.secret_key, testnet=self.testnet)
            logger.info(f"Binance client initialized (testnet={self.testnet})")
        except Exception as e:

            logger.log_error("CLIENT_INIT", f"Failed to initialize client: {str(e)}")
            raise
        
        # Initialize position manager
        from trading.positions import PositionManager
        self.positions = PositionManager(self)
    
    @with_retry()
    def get_server_time(self) -> Dict[str, Any]:
        """Get server time."""
        try:
            return self.client.futures_time()
        except BinanceAPIException as e:
            logger.log_error("GET_TIME", f"API error: {e.message}")
            raise
    
    @with_retry()
    def get_account_balance(self) -> List[Dict[str, Any]]:
        """Get account balance for USDT."""
        try:
            balance = self.client.futures_account_balance()
            # Filter for USDT
            usdt_balance = [b for b in balance if b['asset'] == 'USDT']
            logger.info(f"Retrieved balance: {usdt_balance}")
            return usdt_balance
        except BinanceAPIException as e:
            logger.log_error("GET_BALANCE", f"API error: {e.message}")
            raise
    
    @with_retry()
    def get_position_info(self, symbol: str = DEFAULT_SYMBOL) -> Dict[str, Any]:
        """Get position information for a symbol."""
        try:
            position = self.client.futures_position_information(symbol=symbol)
            if position:
                logger.info(f"Retrieved position for {symbol}: {position[0]}")
                return position[0]
            return {}
        except BinanceAPIException as e:
            logger.log_error("GET_POSITION", f"API error: {e.message}")
            raise
    
    @with_retry()
    def get_symbol_info(self, symbol: str = DEFAULT_SYMBOL) -> Dict[str, Any]:
        """Get symbol information (precision, limits, etc.)."""
        try:
            info = self.client.futures_exchange_info(symbol=symbol)
            if info and 'symbols' in info and len(info['symbols']) > 0:
                symbol_info = info['symbols'][0]
                logger.debug(f"Retrieved symbol info for {symbol}")
                return symbol_info
            return {}
        except BinanceAPIException as e:
            logger.log_error("GET_SYMBOL_INFO", f"API error: {e.message}")
            raise
    
    @with_retry()
    def get_current_price(self, symbol: str = DEFAULT_SYMBOL) -> float:
        """Get current market price for a symbol."""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            logger.debug(f"Current price for {symbol}: {price}")
            return price
        except BinanceAPIException as e:
            logger.log_error("GET_PRICE", f"API error: {e.message}")
            raise
    
    @with_retry()
    def get_order_book(self, symbol: str = DEFAULT_SYMBOL, limit: int = 20) -> Dict[str, Any]:
        """Get order book for a symbol."""
        try:
            depth = self.client.futures_order_book(symbol=symbol, limit=limit)
            logger.debug(f"Retrieved order book for {symbol}")
            return depth
        except BinanceAPIException as e:
            logger.log_error("GET_ORDER_BOOK", f"API error: {e.message}")
            raise
    
    @with_retry()
    def get_klines(self, symbol: str = DEFAULT_SYMBOL, interval: str = '1m', 
                   limit: int = 100) -> List[List[Any]]:
        """Get candlestick/kline data."""
        try:
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            logger.debug(f"Retrieved {len(klines)} klines for {symbol}")
            return klines
        except BinanceAPIException as e:
            logger.log_error("GET_KLINES", f"API error: {e.message}")
            raise
    
    @with_retry()
    def get_ticker(self, symbol: str = DEFAULT_SYMBOL) -> Dict[str, Any]:
        """Get 24hr ticker for a symbol."""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            logger.debug(f"Retrieved ticker for {symbol}")
            return ticker
        except BinanceAPIException as e:
            logger.log_error("GET_TICKER", f"API error: {e.message}")
            raise
    
    @with_retry()
    def place_order(self, symbol: str, side: str, order_type: str, 
                    quantity: float, price: float = None, 
                    stop_price: float = None, time_in_force: str = 'GTC',
                    reduce_only: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Place an order on Binance Futures.
        
        Args:
            symbol: Trading pair symbol
            side: BUY or SELL
            order_type: MARKET, LIMIT, STOP, TAKE_PROFIT, etc.
            quantity: Order quantity
            price: Limit price (for LIMIT orders)
            stop_price: Stop price (for STOP orders)
            time_in_force: GTC, IOC, FOK
            reduce_only: Reduce only flag
            **kwargs: Additional parameters
        
        Returns:
            Order response from Binance
        """
        try:
            params = {
                'symbol': symbol,
                'side': side.upper(),
                'type': order_type.upper(),
                'quantity': quantity,
                'reduceOnly': reduce_only
            }
            
            # Add price for limit orders
            if order_type.upper() in ['LIMIT', 'STOP', 'TAKE_PROFIT']:
                if price is None:
                    raise ValueError(f"Price is required for {order_type} orders")
                params['price'] = price
                params['timeInForce'] = time_in_force.upper()
            
            # Add stop price for stop orders
            if order_type.upper() in ['STOP', 'STOP_MARKET', 'TAKE_PROFIT', 'TAKE_PROFIT_MARKET']:
                if stop_price is None:
                    raise ValueError(f"Stop price is required for {order_type} orders")
                params['stopPrice'] = stop_price
            
            # Add any additional parameters
            params.update(kwargs)
            
            logger.log_order(order_type, symbol, {
                'side': side,
                'quantity': quantity,
                'price': price,
                'stop_price': stop_price
            })
            
            order = self.client.futures_create_order(**params)
            
            logger.log_execution(
                str(order.get('orderId', 'N/A')),
                order.get('status', 'NEW'),
                {'price': order.get('price'), 'qty': order.get('executedQty')}
            )
            
            return order
            
        except BinanceAPIException as e:
            logger.log_error("PLACE_ORDER", f"API error: {e.message}", {
                'symbol': symbol,
                'type': order_type,
                'side': side
            })
            raise
        except Exception as e:
            logger.log_error("PLACE_ORDER", f"Unexpected error: {str(e)}", {
                'symbol': symbol,
                'type': order_type
            })
            raise
    
    @with_retry()
    def place_market_order(self, symbol: str, side: str, quantity: float,
                          reduce_only: bool = False) -> Dict[str, Any]:
        """Place a market order."""
        return self.place_order(
            symbol=symbol,
            side=side,
            order_type='MARKET',
            quantity=quantity,
            reduce_only=reduce_only
        )
    
    @with_retry()
    def place_limit_order(self, symbol: str, side: str, quantity: float,
                         price: float, time_in_force: str = 'GTC',
                         reduce_only: bool = False) -> Dict[str, Any]:
        """Place a limit order."""
        return self.place_order(
            symbol=symbol,
            side=side,
            order_type='LIMIT',
            quantity=quantity,
            price=price,
            time_in_force=time_in_force,
            reduce_only=reduce_only
        )
    
    @with_retry()
    def place_stop_limit_order(self, symbol: str, side: str, quantity: float,
                              stop_price: float, limit_price: float,
                              time_in_force: str = 'GTC') -> Dict[str, Any]:
        """Place a stop-limit order."""
        return self.place_order(
            symbol=symbol,
            side=side,
            order_type='STOP',
            quantity=quantity,
            price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force
        )
    
    @with_retry()
    def place_oco_order(self, symbol: str, side: str, quantity: float,
                       limit_price: float, stop_price: float,
                       list_client_order_id: str = None) -> Dict[str, Any]:
        """
        Place an OCO (One-Cancels-the-Other) order.
        
        Args:
            symbol: Trading pair symbol
            side: BUY or SELL
            quantity: Total quantity
            limit_price: Take-profit limit price
            stop_price: Stop-loss trigger price
            list_client_order_id: Client order ID for the OCO
        
        Returns:
            OCO order response
        """
        try:
            params = {
                'symbol': symbol,
                'side': side.upper(),
                'quantity': quantity,
                'price': limit_price,
                'stopPrice': stop_price,
                'stopLimitTimeInForce': 'GTC'
            }
            
            if list_client_order_id:
                params['listClientOrderId'] = list_client_order_id
            
            logger.log_order("OCO", symbol, {
                'side': side,
                'quantity': quantity,
                'limit_price': limit_price,
                'stop_price': stop_price
            })
            
            order = self.client.futures_create_oco_order(**params)
            
            logger.info(f"OCO order placed: {order.get('listClientOrderId', 'N/A')}")
            
            return order
            
        except BinanceAPIException as e:
            logger.log_error("PLACE_OCO", f"API error: {e.message}")
            raise
        except Exception as e:
            logger.log_error("PLACE_OCO", f"Unexpected error: {str(e)}")
            raise
    
    @with_retry()
    def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get open orders."""
        try:
            orders = self.client.futures_get_open_orders(symbol=symbol)
            logger.info(f"Retrieved {len(orders)} open orders")
            return orders
        except BinanceAPIException as e:
            logger.log_error("GET_OPEN_ORDERS", f"API error: {e.message}")
            raise
    
    @with_retry()
    def get_all_orders(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all orders for a symbol."""
        try:
            orders = self.client.futures_get_all_orders(symbol=symbol, limit=limit)
            logger.info(f"Retrieved {len(orders)} orders for {symbol}")
            return orders
        except BinanceAPIException as e:
            logger.log_error("GET_ALL_ORDERS", f"API error: {e.message}")
            raise
    
    @with_retry()
    def cancel_order(self, symbol: str, order_id: int = None, 
                    client_order_id: str = None) -> Dict[str, Any]:
        """Cancel an order."""
        try:
            params = {'symbol': symbol}
            
            if order_id:
                params['orderId'] = order_id
            elif client_order_id:
                params['clientOrderId'] = client_order_id
            else:
                raise ValueError("Either order_id or client_order_id is required")
            
            logger.info(f"Cancelling order: {order_id or client_order_id}")
            
            result = self.client.futures_cancel_order(**params)
            
            logger.info(f"Order cancelled: {result.get('orderId')}")
            
            return result
            
        except BinanceAPIException as e:
            logger.log_error("CANCEL_ORDER", f"API error: {e.message}")
            raise
    
    @with_retry()
    def cancel_all_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """Cancel all open orders for a symbol."""
        try:
            result = self.client.futures_cancel_all_open_orders(symbol=symbol)
            logger.info(f"Cancelled all orders for {symbol}")
            return result
        except BinanceAPIException as e:
            logger.log_error("CANCEL_ALL", f"API error: {e.message}")
            raise
    
    @with_retry()
    def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Set leverage for a symbol."""
        try:
            result = self.client.futures_change_leverage(
                symbol=symbol,
                leverage=leverage
            )
            logger.info(f"Leverage set to {leverage}x for {symbol}")
            return result
        except BinanceAPIException as e:
            logger.log_error("SET_LEVERAGE", f"API error: {e.message}")
            raise
    
    @with_retry()
    def set_margin_type(self, symbol: str, margin_type: str) -> Dict[str, Any]:
        """Set margin type (ISOLATED or CROSSED)."""
        try:
            result = self.client.futures_change_margin_type(
                symbol=symbol,
                marginType=margin_type.upper()
            )
            logger.info(f"Margin type set to {margin_type} for {symbol}")
            return result
        except BinanceAPIException as e:
            logger.log_error("SET_MARGIN_TYPE", f"API error: {e.message}")
            raise
    
    @with_retry()
    def get_order(self, symbol: str, order_id: int = None,
                 client_order_id: str = None) -> Dict[str, Any]:
        """Get order details."""
        try:
            params = {'symbol': symbol}
            
            if order_id:
                params['orderId'] = order_id
            elif client_order_id:
                params['clientOrderId'] = client_order_id
            else:
                raise ValueError("Either order_id or client_order_id is required")
            
            order = self.client.futures_get_order(**params)
            return order
            
        except BinanceAPIException as e:
            logger.log_error("GET_ORDER", f"API error: {e.message}")
            raise
    
    def ping(self) -> bool:
        """Test connectivity to the API."""
        try:
            self.client.ping()
            return True
        except Exception:
            return False


def create_client(api_key: str = None, secret_key: str = None, 
                 testnet: bool = None) -> BinanceClient:
    """
    Factory function to create a Binance client.
    
    Args:
        api_key: Binance API key
        secret_key: Binance API secret
        testnet: Whether to use testnet
    
    Returns:
        BinanceClient instance
    """
    return BinanceClient(api_key, secret_key, testnet)
