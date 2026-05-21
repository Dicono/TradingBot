# Binance Futures Testnet — Trading Bot

A clean, well-structured Python CLI application for placing orders on the **Binance USDT-M Futures Testnet**.  
Supports **MARKET**, **LIMIT**, and **STOP_MARKET** orders with full input validation, structured logging, and clear error handling.

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [CLI Reference](#cli-reference)
- [Examples](#examples)
- [Logging](#logging)
- [Error Handling](#error-handling)
- [Assumptions](#assumptions)

---

## Features

| Feature | Details |
|---|---|
| Order types | MARKET, LIMIT, STOP_MARKET |
| Sides | BUY, SELL |
| Validation | Symbol, side, type, quantity, price — all validated before any network call |
| Logging | Structured rotating log file (`logs/trading_bot.log`) with timestamps, levels, and module names |
| Error handling | Catches API errors, network failures, and invalid input separately |
| Architecture | Layered: `client.py` (HTTP) → `orders.py` (logic) → `cli.py` (user interface) |
| Bonus | STOP_MARKET order type, `balance`, `positions`, `open-orders`, and `cancel` commands |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST API wrapper (signing, HTTP)
│   ├── orders.py          # Order placement logic + OrderResult dataclass
│   ├── validators.py      # Input validation (raises ValueError with clear messages)
│   └── logging_config.py  # Rotating file + console logger setup
├── cli.py                 # CLI entry point (argparse sub-commands)
├── logs/
│   └── trading_bot.log    # Rotating log file (created on first run)
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Prerequisites

- Python 3.9 or higher
- A **Binance Futures Testnet** account

### 2. Get Testnet API Credentials

1. Go to [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in with your GitHub account
3. Navigate to **API Key** → **Generate Key**
4. Copy your **API Key** and **Secret Key** — the secret is shown only once

### 3. Clone / Download

```bash
git clone https://github.com/your-username/trading-bot.git
cd trading_bot
```

### 4. Create a Virtual Environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate       # Linux / macOS
.venv\Scripts\activate          # Windows PowerShell
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

Set your credentials as environment variables before running the bot.

**Linux / macOS:**
```bash
export BINANCE_API_KEY="your_testnet_api_key_here"
export BINANCE_API_SECRET="your_testnet_api_secret_here"
```

**Windows (PowerShell):**
```powershell
$env:BINANCE_API_KEY="your_testnet_api_key_here"
$env:BINANCE_API_SECRET="your_testnet_api_secret_here"
```

**Optional — using a `.env` file:**

Create a `.env` file in the project root:
```
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

Then load it before running (requires `python-dotenv`, included in `requirements.txt`):
```bash
# In your shell session
export $(cat .env | xargs)
```

> **Never commit your `.env` file or API credentials to version control.**

**Optional environment variables:**

| Variable | Default | Description |
|---|---|---|
| `BINANCE_API_KEY` | *(required)* | Testnet API key |
| `BINANCE_API_SECRET` | *(required)* | Testnet API secret |
| `BINANCE_BASE_URL` | `https://testnet.binancefuture.com` | API base URL |
| `LOG_LEVEL` | `DEBUG` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Running the Bot

All commands follow this pattern:

```
python cli.py <command> [options]
```

To see all available commands:
```bash
python cli.py --help
```

To see options for a specific command:
```bash
python cli.py order --help
```

---

## CLI Reference

### `order` — Place a new order

```
python cli.py order --symbol SYMBOL --side SIDE --type TYPE --quantity QTY [options]
```

| Argument | Required | Description |
|---|---|---|
| `--symbol` | ✓ | Trading pair (e.g. `BTCUSDT`, `ETHUSDT`) |
| `--side` | ✓ | `BUY` or `SELL` |
| `--type` | ✓ | `MARKET`, `LIMIT`, or `STOP_MARKET` |
| `--quantity` | ✓ | Number of contracts |
| `--price` | LIMIT only | Limit price |
| `--stop-price` | STOP_MARKET only | Trigger price |
| `--tif` | optional | Time-in-force: `GTC` (default), `IOC`, `FOK` |
| `--reduce-only` | optional | Only reduce an existing position |

### `balance` — Show account balances

```
python cli.py balance
```

### `positions` — Show open positions

```
python cli.py positions [--symbol SYMBOL]
```

### `open-orders` — List open orders

```
python cli.py open-orders [--symbol SYMBOL]
```

### `cancel` — Cancel an open order

```
python cli.py cancel --symbol SYMBOL --order-id ORDER_ID
```

---

## Examples

### Place a MARKET order (buy 0.001 BTC)

```bash
python cli.py order \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.001
```

**Output:**
```
╔══════════════════════════════════════════════════════════╗
║      BINANCE FUTURES TESTNET  ·  TRADING BOT CLI         ║
╚══════════════════════════════════════════════════════════╝

──────────────────────────────────────────────────
  ORDER REQUEST SUMMARY (MARKET)
──────────────────────────────────────────────────
  symbol          : BTCUSDT
  side            : BUY
  type            : MARKET
  quantity        : 0.001
──────────────────────────────────────────────────

════════════════════════════════════════════════════
  ORDER RESULT
════════════════════════════════════════════════════
✓ ORDER PLACED SUCCESSFULLY
  Order ID     : 8389765432
  Client OID   : xJ7kqR2mNpL9oT3vW4yA
  Symbol       : BTCUSDT
  Side         : BUY
  Type         : MARKET
  Status       : FILLED
  Avg Price    : 62345.10000
  Orig Qty     : 0.001
  Executed Qty : 0.001

✓ Done.
```

---

### Place a LIMIT order (sell 0.001 BTC at $65,000)

```bash
python cli.py order \
  --symbol BTCUSDT \
  --side SELL \
  --type LIMIT \
  --quantity 0.001 \
  --price 65000
```

---

### Place a STOP_MARKET order (stop-loss at $60,000)

```bash
python cli.py order \
  --symbol BTCUSDT \
  --side SELL \
  --type STOP_MARKET \
  --quantity 0.001 \
  --stop-price 60000
```

---

### Check account balance

```bash
python cli.py balance
```

---

### List open orders for BTCUSDT

```bash
python cli.py open-orders --symbol BTCUSDT
```

---

### Cancel an order

```bash
python cli.py cancel --symbol BTCUSDT --order-id 8389771209
```

---

### Set log level to WARNING (quieter logs)

```bash
LOG_LEVEL=WARNING python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

---

## Logging

All activity is logged to **`logs/trading_bot.log`** with the following format:

```
TIMESTAMP | LEVEL    | MODULE               | MESSAGE
2025-05-08 09:12:03 | INFO     | trading_bot.client          | → POST /fapi/v1/order | params={...}
2025-05-08 09:12:03 | INFO     | trading_bot.client          | ← HTTP 200 | POST /fapi/v1/order | body={...}
2025-05-08 09:12:03 | INFO     | trading_bot.orders          | Market order placed — orderId=8389765432 status=FILLED
```

- **Console** shows `WARNING` and above only (to keep CLI output clean)
- **Log file** records everything from `DEBUG` level upward (configurable via `LOG_LEVEL`)
- Log files rotate at **10 MB**, keeping up to **5 backups**
- API signatures are **never** logged (only the non-sensitive parameters)

---

## Error Handling

The bot handles three categories of errors:

| Category | Example | Behaviour |
|---|---|---|
| **Input validation** | Invalid side, missing price for LIMIT | Prints all validation errors, exits before any network call |
| **API errors** | Invalid symbol (`-1121`), insufficient balance | Prints Binance error code + message, logs full details |
| **Network failures** | Timeout, connection refused | Prints descriptive message, logs exception with traceback |

**Example — validation error:**
```
✗ ERROR: Validation failed:
  • Price is required for 'LIMIT' orders but was not provided.
```

**Example — API error:**
```
✗ ORDER FAILED
  Error Code   : -1121
  Error Message: Invalid symbol.
```

---

## Assumptions

1. **USDT-M Futures only** — the bot targets the `/fapi/` endpoints. Spot or COIN-M futures are not supported.
2. **Credentials via environment variables** — no credential prompts or config files are used for security.
3. **Single-leg orders only** — bracket / OCO orders are not implemented (STOP_MARKET is the bonus order type).
4. **Testnet URL** — `https://testnet.binancefuture.com`. Switching to mainnet requires setting `BINANCE_BASE_URL=https://fapi.binance.com` (⚠ real funds).
5. **Quantity precision** — the bot does not enforce symbol-specific lot-size filters. Binance will reject orders that violate these filters with error `-1111`. Check [exchange info](https://testnet.binancefuture.com/fapi/v1/exchangeInfo) for exact step sizes.
6. **No position mode check** — the bot uses `positionSide=BOTH` (one-way mode) by default. Hedge mode requires `positionSide=LONG/SHORT`.
