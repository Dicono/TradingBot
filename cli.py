#!/usr/bin/env python3
"""
Binance Futures Testnet Trading Bot — CLI Entry Point.

Usage examples:
  # Market buy
  python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

  # Limit sell
  python cli.py order --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 3000

  # Stop-market (stop-loss)
  python cli.py order --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 60000

  # Check account balance
  python cli.py balance

  # List open orders
  python cli.py open-orders --symbol BTCUSDT

  # Cancel an order
  python cli.py cancel --symbol BTCUSDT --order-id 123456789

Environment variables (required for order/balance commands):
  BINANCE_API_KEY    — your Testnet API key
  BINANCE_API_SECRET — your Testnet API secret
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from typing import Optional

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.logging_config import setup_logging, get_logger
from bot.orders import place_order
from bot.validators import validate_order_params

# ── Setup ──────────────────────────────────────────────────────────────────────

setup_logging(log_level=os.getenv("LOG_LEVEL", "DEBUG"))
logger = get_logger("cli")

BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║      BINANCE FUTURES TESTNET  ·  TRADING BOT CLI         ║
╚══════════════════════════════════════════════════════════╝
"""

# ── Credential helper ──────────────────────────────────────────────────────────


def _get_client() -> BinanceFuturesClient:
    """
    Build a BinanceFuturesClient from environment variables.

    Reads:
      BINANCE_API_KEY    — testnet API key
      BINANCE_API_SECRET — testnet API secret
      BINANCE_BASE_URL   — optional override (defaults to testnet URL)
    """
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    base_url = os.getenv(
        "BINANCE_BASE_URL", "https://testnet.binancefuture.com"
    ).strip()

    if not api_key:
        _die(
            "BINANCE_API_KEY environment variable is not set.\n"
            "Export your Testnet API key before running:\n"
            "  export BINANCE_API_KEY=your_key_here"
        )
    if not api_secret:
        _die(
            "BINANCE_API_SECRET environment variable is not set.\n"
            "Export your Testnet API secret before running:\n"
            "  export BINANCE_API_SECRET=your_secret_here"
        )

    return BinanceFuturesClient(
        api_key=api_key,
        api_secret=api_secret,
        base_url=base_url,
    )


# ── Output helpers ─────────────────────────────────────────────────────────────


def _print_banner() -> None:
    print(BANNER)


def _die(message: str, code: int = 1) -> None:
    print(f"\n✗ ERROR: {message}\n", file=sys.stderr)
    logger.error("Fatal: %s", message)
    sys.exit(code)


def _section(title: str) -> None:
    print(f"\n{'═' * 52}")
    print(f"  {title}")
    print(f"{'═' * 52}")


# ── Sub-command handlers ───────────────────────────────────────────────────────


def cmd_order(args: argparse.Namespace) -> None:
    """Handle the 'order' sub-command."""
    _print_banner()

    # Validate all inputs before touching the network
    try:
        clean = validate_order_params(
            symbol=args.symbol,
            side=args.side,
            order_type=args.type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as exc:
        _die(str(exc))

    logger.info(
        "CLI order command — %s %s %s qty=%s price=%s stop=%s",
        clean["symbol"],
        clean["side"],
        clean["order_type"],
        clean["quantity"],
        clean.get("price"),
        clean.get("stop_price"),
    )

    client = _get_client()

    result = place_order(
        client=client,
        symbol=clean["symbol"],
        side=clean["side"],
        order_type=clean["order_type"],
        quantity=clean["quantity"],
        price=clean.get("price"),
        stop_price=clean.get("stop_price"),
        time_in_force=args.time_in_force or "GTC",
        reduce_only=args.reduce_only,
    )

    _section("ORDER RESULT")
    print(result.display_summary())

    if result.success:
        logger.info("Order placed successfully — orderId=%s", result.order_id)
        print("\n✓ Done.\n")
        sys.exit(0)
    else:
        logger.error(
            "Order failed — code=%s msg=%s", result.error_code, result.error_message
        )
        sys.exit(1)


def cmd_balance(args: argparse.Namespace) -> None:
    """Handle the 'balance' sub-command."""
    _print_banner()
    client = _get_client()

    try:
        balances = client.get_account_balance()
    except BinanceAPIError as exc:
        _die(f"API error fetching balance — {exc}")
    except Exception as exc:
        _die(f"Network error fetching balance — {exc}")

    _section("ACCOUNT BALANCE")

    non_zero = [b for b in balances if float(b.get("balance", 0)) != 0]

    if not non_zero:
        print("  No non-zero balances found.")
    else:
        print(f"  {'Asset':<10} {'Balance':>18} {'Available':>18}")
        print(f"  {'-'*10} {'-'*18} {'-'*18}")
        for b in non_zero:
            print(
                f"  {b['asset']:<10} "
                f"{float(b['balance']):>18.8f} "
                f"{float(b.get('availableBalance', 0)):>18.8f}"
            )
    print()


def cmd_open_orders(args: argparse.Namespace) -> None:
    """Handle the 'open-orders' sub-command."""
    _print_banner()
    client = _get_client()

    symbol: Optional[str] = args.symbol.upper() if args.symbol else None

    try:
        orders = client.get_open_orders(symbol=symbol)
    except BinanceAPIError as exc:
        _die(f"API error fetching open orders — {exc}")
    except Exception as exc:
        _die(f"Network error fetching open orders — {exc}")

    title = f"OPEN ORDERS" + (f" — {symbol}" if symbol else "")
    _section(title)

    if not orders:
        print("  No open orders.\n")
        return

    print(f"  {'Order ID':<15} {'Symbol':<12} {'Side':<6} {'Type':<14} {'Price':>12} {'Qty':>10}")
    print(f"  {'-'*15} {'-'*12} {'-'*6} {'-'*14} {'-'*12} {'-'*10}")
    for o in orders:
        print(
            f"  {o['orderId']:<15} "
            f"{o['symbol']:<12} "
            f"{o['side']:<6} "
            f"{o['type']:<14} "
            f"{float(o.get('price', 0)):>12.4f} "
            f"{float(o.get('origQty', 0)):>10.6f}"
        )
    print()


def cmd_cancel(args: argparse.Namespace) -> None:
    """Handle the 'cancel' sub-command."""
    _print_banner()
    client = _get_client()

    symbol = args.symbol.upper()
    order_id = args.order_id

    print(f"\n  Cancelling order {order_id} on {symbol} …")
    logger.info("Cancelling order — symbol=%s orderId=%s", symbol, order_id)

    try:
        result = client.cancel_order(symbol=symbol, order_id=order_id)
    except BinanceAPIError as exc:
        _die(f"API error cancelling order — {exc}")
    except Exception as exc:
        _die(f"Network error cancelling order — {exc}")

    _section("CANCEL RESULT")
    print(f"  Order ID : {result.get('orderId')}")
    print(f"  Symbol   : {result.get('symbol')}")
    print(f"  Status   : {result.get('status')}")
    print(f"\n✓ Order cancelled.\n")
    logger.info("Order cancelled — orderId=%s status=%s", result.get("orderId"), result.get("status"))


def cmd_positions(args: argparse.Namespace) -> None:
    """Handle the 'positions' sub-command."""
    _print_banner()
    client = _get_client()

    symbol: Optional[str] = args.symbol.upper() if args.symbol else None

    try:
        positions = client.get_position_info(symbol=symbol)
    except BinanceAPIError as exc:
        _die(f"API error fetching positions — {exc}")
    except Exception as exc:
        _die(f"Network error fetching positions — {exc}")

    title = "POSITIONS" + (f" — {symbol}" if symbol else "")
    _section(title)

    open_pos = [p for p in positions if float(p.get("positionAmt", 0)) != 0]

    if not open_pos:
        print("  No open positions.\n")
        return

    print(f"  {'Symbol':<12} {'Side':<6} {'Size':>12} {'Entry Price':>14} {'Unrealised PnL':>16}")
    print(f"  {'-'*12} {'-'*6} {'-'*12} {'-'*14} {'-'*16}")
    for p in open_pos:
        amt = float(p.get("positionAmt", 0))
        side = "LONG" if amt > 0 else "SHORT"
        print(
            f"  {p['symbol']:<12} "
            f"{side:<6} "
            f"{abs(amt):>12.6f} "
            f"{float(p.get('entryPrice', 0)):>14.4f} "
            f"{float(p.get('unRealizedProfit', 0)):>16.4f}"
        )
    print()


# ── Argument parser ────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description=textwrap.dedent(
            """\
            Binance USDT-M Futures Testnet — Trading Bot CLI

            Credentials are read from environment variables:
              BINANCE_API_KEY    — your Testnet API key
              BINANCE_API_SECRET — your Testnet API secret
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # ── order ──────────────────────────────────────────────────────────────────
    order_p = sub.add_parser(
        "order",
        help="Place a new futures order",
        description="Place a MARKET, LIMIT, or STOP_MARKET futures order.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Examples:
              python cli.py order --symbol BTCUSDT --side BUY  --type MARKET     --quantity 0.001
              python cli.py order --symbol BTCUSDT --side SELL --type LIMIT       --quantity 0.001 --price 70000
              python cli.py order --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 60000
            """
        ),
    )
    order_p.add_argument("--symbol",      required=True,  help="Trading pair, e.g. BTCUSDT")
    order_p.add_argument("--side",        required=True,  help="BUY or SELL")
    order_p.add_argument("--type",        required=True,  dest="type", help="MARKET | LIMIT | STOP_MARKET")
    order_p.add_argument("--quantity",    required=True,  type=float, help="Order quantity")
    order_p.add_argument("--price",       required=False, type=float, default=None, help="Limit price (required for LIMIT)")
    order_p.add_argument("--stop-price",  required=False, type=float, default=None, dest="stop_price", help="Stop trigger price (required for STOP_MARKET)")
    order_p.add_argument("--tif",         required=False, default="GTC", dest="time_in_force",
                         choices=["GTC", "IOC", "FOK", "GTX"],
                         help="Time-in-force for LIMIT orders (default: GTC)")
    order_p.add_argument("--reduce-only", action="store_true", default=False, dest="reduce_only",
                         help="Only reduce an existing position")
    order_p.set_defaults(func=cmd_order)

    # ── balance ────────────────────────────────────────────────────────────────
    balance_p = sub.add_parser("balance", help="Show account balance")
    balance_p.set_defaults(func=cmd_balance)

    # ── open-orders ────────────────────────────────────────────────────────────
    oo_p = sub.add_parser("open-orders", help="List open orders")
    oo_p.add_argument("--symbol", required=False, default=None, help="Filter by symbol")
    oo_p.set_defaults(func=cmd_open_orders)

    # ── cancel ─────────────────────────────────────────────────────────────────
    cancel_p = sub.add_parser("cancel", help="Cancel an open order")
    cancel_p.add_argument("--symbol",   required=True, help="Trading pair, e.g. BTCUSDT")
    cancel_p.add_argument("--order-id", required=True, type=int, dest="order_id", help="Order ID to cancel")
    cancel_p.set_defaults(func=cmd_cancel)

    # ── positions ──────────────────────────────────────────────────────────────
    pos_p = sub.add_parser("positions", help="Show open futures positions")
    pos_p.add_argument("--symbol", required=False, default=None, help="Filter by symbol")
    pos_p.set_defaults(func=cmd_positions)

    return parser


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.\n")
        logger.info("CLI interrupted by user (KeyboardInterrupt)")
        sys.exit(130)


if __name__ == "__main__":
    main()
