from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import os
from functools import lru_cache
from datetime import datetime, timedelta
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from trading.client import BinanceClient
from config import BINANCE_API_KEY, BINANCE_SECRET_KEY, DEFAULT_SYMBOL

app = FastAPI(title="Binance Trading Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singleton client
_client = None

def get_client():
    global _client
    if _client is None:
        _client = BinanceClient()
        # Verify positions attribute exists
        if not hasattr(_client, 'positions'):
            raise RuntimeError("BinanceClient initialized without positions attribute")
    return _client

# Simple cache
cache = {}
CACHE_TTL = 2  # seconds

def get_cached(key):
    if key in cache:
        data, timestamp = cache[key]
        if datetime.now() - timestamp < timedelta(seconds=CACHE_TTL):
            return data
    return None

def set_cache(key, data):
    cache[key] = (data, datetime.now())

class OrderRequest(BaseModel):
    symbol: str = DEFAULT_SYMBOL
    side: str
    quantity: float
    price: Optional[float] = None
    order_type: str = "MARKET"

@app.get("/balance")
def get_balance():
    try:
        cached = get_cached("balance")
        if cached:
            return {"success": True, "balance": cached, "cached": True}
        client = get_client()
        balances = client.get_account_balance()
        set_cache("balance", balances)
        return {"success": True, "balance": balances}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/price/{symbol}")
def get_price(symbol: str):
    try:
        cache_key = f"price_{symbol}"
        cached = get_cached(cache_key)
        if cached:
            return {"symbol": symbol, "price": cached, "cached": True}
        client = get_client()
        price = client.get_current_price(symbol)
        set_cache(cache_key, price)
        return {"symbol": symbol, "price": price}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/order")
def place_order(order: OrderRequest):
    try:
        client = get_client()
        if order.order_type == "MARKET":
            result = client.place_market_order(order.symbol, order.side, order.quantity)
        elif order.order_type == "LIMIT":
            result = client.place_limit_order(order.symbol, order.side, order.quantity, order.price)
        # Invalidate cache so next fetch gets fresh data
        cache.pop("balance", None)
        cache.pop("orders", None)
        cache.pop(f"orders_all_{order.symbol}", None)
        cache.pop("positions", None)
        return {"success": True, "order": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/orders")
def get_open_orders(symbol: Optional[str] = None):
    """Get only open (unfilled) orders."""
    try:
        cached = get_cached("orders")
        if cached:
            return {"orders": cached, "cached": True}
        client = get_client()
        orders = client.get_open_orders(symbol)
        set_cache("orders", orders)
        return {"orders": orders}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/orders/all")
def get_all_orders(symbol: Optional[str] = None):
    """Get all orders including filled/cancelled."""
    try:
        sym = symbol or DEFAULT_SYMBOL
        cached = get_cached(f"orders_all_{sym}")
        if cached:
            return {"orders": cached, "cached": True}
        client = get_client()
        orders = client.get_all_orders(sym, limit=50)
        set_cache(f"orders_all_{sym}", orders)
        return {"orders": orders}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class CancelRequest(BaseModel):
    symbol: str
    order_id: int

@app.post("/orders/cancel")
def cancel_order_endpoint(req: CancelRequest):
    """Cancel an open order."""
    try:
        client = get_client()
        result = client.cancel_order(req.symbol, req.order_id)
        # Invalidate caches
        cache.pop("orders", None)
        cache.pop(f"orders_all_{req.symbol}", None)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/positions")
def get_positions():
    """Get all positions with non-zero size."""
    try:
        cached = get_cached("positions")
        if cached:
            return {"positions": cached, "cached": True}
        client = get_client()
        positions = client.client.futures_position_information()
        # Filter positions with non-zero amount
        active_positions = [
            p for p in positions 
            if float(p.get('positionAmt', 0)) != 0
        ]
        set_cache("positions", active_positions)
        return {"positions": active_positions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class ClosePositionRequest(BaseModel):
    symbol: str

@app.post("/reset-client")
def reset_client():
    """Reset the singleton client (useful after code changes)."""
    global _client
    _client = None
    return {"success": True, "message": "Client reset, will reinitialize on next request"}

@app.post("/positions/close")
def close_position_endpoint(req: ClosePositionRequest):
    """Close an open position with a market order."""
    try:
        client = get_client()
        result = client.positions.close_position(req.symbol)
        # Invalidate caches
        cache.pop("positions", None)
        cache.pop("balance", None)
        cache.pop(f"orders_all_{req.symbol}", None)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/account")
def get_account():
    """Get full account information including all balances."""
    try:
        cached = get_cached("account")
        if cached:
            return {"account": cached, "cached": True}
        client = get_client()
        account = client.client.futures_account()
        set_cache("account", account)
        return {"account": account}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/status")
def get_status():
    """Get combined status for faster initial load."""
    try:
        client = get_client()
        
        # Get all data in parallel using the client directly
        balance = get_cached("balance")
        orders = get_cached("orders")
        positions = get_cached("positions")
        price = get_cached(f"price_{DEFAULT_SYMBOL}")
        
        # Fetch missing data
        if not balance:
            balance = client.get_account_balance()
            set_cache("balance", balance)
        if not orders:
            orders = client.get_open_orders()
            set_cache("orders", orders)
        if not positions:
            positions = client.client.futures_position_information()
            positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
            set_cache("positions", positions)
        if not price:
            price = client.get_current_price(DEFAULT_SYMBOL)
            set_cache(f"price_{DEFAULT_SYMBOL}", price)
        
        return {
            "balance": balance,
            "orders": orders,
            "positions": positions,
            "price": price,
            "symbol": DEFAULT_SYMBOL
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
