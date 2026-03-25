# Documentation

## Table of Contents

- [Order Types](#order-types)
- [Trading Strategies](#trading-strategies)
- [Backend API](#backend-api)
- [Frontend Architecture](#frontend-architecture)
- [Configuration](#configuration)
- [Validation Rules](#validation-rules)
- [Logging](#logging)
- [Disclaimer](#disclaimer)

---

## Order Types

### Market Order
Executes immediately at the current best available price.

```python
# Usage via CLI
# Select: 3. Place Market Order
# Required: symbol, side (BUY/SELL), quantity
```

### Limit Order
Executes only at your specified price or better. Order stays open until filled or cancelled.

```python
# Select: 4. Place Limit Order
# Required: symbol, side, quantity, price
```

### Stop-Limit Order
Triggers a limit order when the stop price is reached.

```
Symbol:      BTCUSDT
Side:        BUY
Quantity:    0.01
Stop Price:  45000   ← triggers when market hits this
Limit Price: 45100   ← actual order price
```

### OCO Order (One-Cancels-the-Other)
Places a take-profit and stop-loss simultaneously. When one fills, the other is cancelled automatically.

```
For a LONG position:
  Take Profit: 46000  ← sell to lock in gains
  Stop Loss:   44000  ← sell to cut losses
```

---

## Trading Strategies

### TWAP (Time-Weighted Average Price)
Splits a large order into smaller chunks executed at regular intervals. Reduces slippage and market impact.

| Parameter | Description |
|-----------|-------------|
| Total Quantity | Full amount to trade |
| Intervals | How many sub-orders to place |
| Interval Seconds | Time gap between each sub-order |

**Example:** Buy 1 BTC over 10 minutes → 10 × 0.1 BTC every 60 seconds.

### Grid Trading
Places buy and sell orders at evenly spaced price levels within a range. Profits automatically from price oscillations.

| Parameter | Description |
|-----------|-------------|
| Min Price | Lower bound of the grid range |
| Max Price | Upper bound of the grid range |
| Grid Count | Number of price levels |
| Quantity per Grid | Amount traded at each level |

**Example:** Range $40,000–$50,000 with 10 grids → buy/sell orders every $1,000.

---

## Backend API

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/balance` | USDT futures wallet balance |
| GET | `/price/{symbol}` | Live market price for a symbol |
| GET | `/orders` | All open orders |
| GET | `/positions` | All open positions with P&L |
| GET | `/account` | Account info (leverage, margin type) |
| GET | `/status` | Combined snapshot (fast initial load) |
| POST | `/order` | Place a market or limit order |

### POST `/order` Payload

```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "quantity": 0.001,
  "order_type": "MARKET"
}
```

For limit orders, also include `"price": 45000`.

### Caching

The backend uses an in-memory cache with a 2-second TTL to reduce API load. Cache is automatically invalidated when an order is placed.

---

## Frontend Architecture

Built with **Next.js 15**, **React 19**, **TypeScript**, and **Tailwind CSS v4**.

### State Management (Zustand)

All trading data lives in a single Zustand store (`useTradingStore`):

| Field | Type | Description |
|-------|------|-------------|
| `balance` | `string` | USDT balance |
| `symbol` | `string` | Active trading pair |
| `livePrice` | `number` | Current market price |
| `openOrders` | `number` | Count of open orders |
| `orders` | `any[]` | Full orders list |
| `positions` | `any[]` | Open positions |

### Polling

| Interval | What updates |
|----------|-------------|
| Every 5s | Live price |
| Every 15s | Balance + orders + positions |
| On order placed | Immediate refresh of all three |

### Pages

| Route | Description |
|-------|-------------|
| `/` | Home / landing |
| `/dashboard` | Overview stats + Quick Trade form |
| `/orders` | Order history with BUY/SELL filter |
| `/positions` | Open positions with P&L |
| `/wallet` | Balance breakdown |
| `/settings` | Theme toggle + account info |

---

## Configuration

Edit `.env` in the project root:

```env
BINANCE_API_KEY=your_testnet_api_key
BINANCE_SECRET_KEY=your_testnet_secret_key
TESTNET=True
```

Get free testnet credentials at: https://testnet.binancefuture.com

---

## Validation Rules

Orders are validated before being sent to Binance:

| Rule | Requirement |
|------|-------------|
| Symbol | Must end with `USDT` |
| Quantity | Minimum `0.001` |
| Price | Must be a positive number |
| Notional value | Minimum `5 USDT` |
| Stop price | Must be between limit price and market price |

---

## Logging

Logs are written to `logs/trading_bot.log`:

```
2024-01-15 10:30:00 | INFO | BinanceTradingBot | ORDER | LIMIT | BTCUSDT | side=BUY | qty=0.01 | price=45000.0
2024-01-15 10:30:01 | INFO | BinanceTradingBot | EXECUTION | 123456789 | FILLED | price=45000.0 | qty=0.01
```

---

## Disclaimer

> **WARNING:** Trading futures involves substantial financial risk.
> - Always test on testnet before using real funds
> - Start with minimum quantities
> - Understand each strategy fully before enabling it
> - Monitor positions actively
> - Set stop-losses on all trades
>
> The authors are not responsible for any financial losses incurred through use of this software.
