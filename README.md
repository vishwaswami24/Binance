<div align="center">

# 📈 Binance Futures Trading Dashboard

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" />
  <img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" />
  <img src="https://img.shields.io/badge/Binance-F0B90B?style=for-the-badge&logo=binance&logoColor=black" />
</p>

A full-stack Binance Futures trading dashboard with real-time price data, order execution, position tracking, and automated trading strategies.

</div>

---
<img width="1897" height="930" alt="Screenshot 2026-03-25 124609" src="https://github.com/user-attachments/assets/5f22a025-4c38-422b-974f-84952d50dd99" />

## ✨ Features

- **Live Trading** — Market & Limit orders via Binance Futures Testnet
- **Real-time Data** — Live price feed, balance, and position updates
- **Position Tracking** — Monitor open positions, P&L, and liquidation prices
- **Order Management** — View and track open orders
- **Trading Strategies** — TWAP and Grid strategy automation
- **Dark / Light Theme** — Persistent theme with instant toggle
- **Wallet Overview** — USDT balance and account info

---

## 🗂️ Project Structure

```
Binanace/
├── backend/          # FastAPI REST API
│   └── app.py
├── frontend-next/    # Next.js 15 + Tailwind CSS v4
│   └── src/
├── trading/          # Binance API client & order logic
├── strategies/       # TWAP & Grid trading strategies
├── utils/            # Logger & formatters
├── config.py         # API keys & settings
└── main.py           # CLI entry point
```

---

## 🚀 Quick Start

### 1. Clone & Setup Python

```bash
git clone https://github.com/yourusername/binanace.git
cd binanace
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
```

Edit `.env` with your Binance **Testnet** credentials:

```env
BINANCE_API_KEY=your_testnet_api_key
BINANCE_SECRET_KEY=your_testnet_secret_key
TESTNET=True
```

> Get free testnet keys at: https://testnet.binancefuture.com

### 3. Start Backend

```bash
python -m uvicorn backend.app:app --reload --port 8000
```

API available at `http://localhost:8000`

### 4. Start Frontend

```bash
cd frontend-next
npm install
npm run dev
```

Dashboard available at `http://localhost:3000`

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/balance` | USDT futures balance |
| GET | `/price/{symbol}` | Live price for symbol |
| GET | `/orders` | Open orders |
| GET | `/positions` | Open positions |
| GET | `/account` | Account info |
| GET | `/status` | Combined status (fast load) |
| POST | `/order` | Place market/limit order |

---

## 🤖 CLI Usage

```bash
python main.py
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, React 19, TypeScript |
| Styling | Tailwind CSS v4, CSS Variables |
| State | Zustand with persistence |
| Backend | FastAPI, Python 3.x |
| API | Binance Futures Testnet |
| Charts | Recharts |

---

<div align="center">
  <sub>Built with ❤️ using Binance Futures Testnet</sub>
</div>
