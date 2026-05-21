"""
Order placement logic for Binance USDT-M Futures Testnet.

Each public function:
1. Accepts validated parameters
2. Builds the correct API payload
3. Logs the request summary
4. Delegates to BinanceFuturesClient.place_order()
5. Returns a structured OrderResult dataclass

Supported order types:
  - MARKET
  - LIMIT
  - STOP_MARKET  (bonus order type)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.logging_config import get_logger

logger = get_logger("orders")


# ── Result dataclass ───────────────────────────────────────────────────────────


@dataclass
class OrderResult:
    """Structured representation of a Binance order response."""

    success: bool
    order_id: Optional[int] = None
    client_order_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    price: Optional[str] = None
    avg_price: Optional[str] = None
    orig_qty: Optional[str] = None
    executed_qty: Optional[str] = None
    time_in_force: Optional[str] = None
    raw_response: dict = field(default_factory=dict)
    error_code: Optional[int] = None
    error_message: Optional[str] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "OrderResult":
        """Parse the raw Binance API order response into an OrderResult."""
        return cls(
            success=True,
            order_id=data.get("orderId"),
            client_order_id=data.get("clientOrderId"),
            symbol=data.get("symbol"),
            side=data.get("side"),
            order_type=data.get("type"),
            status=data.get("status"),
            price=data.get("price"),
            avg_price=data.get("avgPrice"),
            orig_qty=data.get("origQty"),
            executed_qty=data.get("executedQty"),
            time_in_force=data.get("timeInForce"),
            raw_response=data,
        )

    @classmethod
    def from_error(cls, error: Exception) -> "OrderResult":
        """Create a failed OrderResult from an exception."""
        if isinstance(error, BinanceAPIError):
            return cls(
                success=False,
                error_code=error.code,
                error_message=error.message,
            )
        return cls(
            success=False,
            error_code=-1,
            error_message=str(error),
        )

    def display_summary(self) -> str:
        """Return a human-readable summary of the order result."""
        if not self.success:
            return (
                f"✗ ORDER FAILED\n"
                f"  Error Code   : {self.error_code}\n"
                f"  Error Message: {self.error_message}"
            )

        lines = [
            "✓ ORDER PLACED SUCCESSFULLY",
            f"  Order ID     : {self.order_id}",
            f"  Client OID   : {self.client_order_id}",
            f"  Symbol       : {self.symbol}",
            f"  Side         : {self.side}",
            f"  Type         : {self.order_type}",
            f"  Status       : {self.status}",
        ]

        if self.order_type not in ("MARKET", "STOP_MARKET"):
            lines.append(f"  Price        : {self.price}")

        if self.avg_price and float(self.avg_price or 0) > 0:
            lines.append(f"  Avg Price    : {self.avg_price}")

        lines += [
            f"  Orig Qty     : {self.orig_qty}",
            f"  Executed Qty : {self.executed_qty}",
        ]

        if self.time_in_force:
            lines.append(f"  Time-in-Force: {self.time_in_force}")

        return "\n".join(lines)


# ── Order placement helpers ────────────────────────────────────────────────────


def _log_order_request(label: str, params: dict) -> None:
    """Log the outgoing order summary at INFO level."""
    loggable = {k: v for k, v in params.items() if v is not None}
    logger.info("Placing %s order — %s", label, json.dumps(loggable))
    print(
        f"\n{'─' * 50}\n"
        f"  ORDER REQUEST SUMMARY ({label})\n"
        f"{'─' * 50}"
    )
    for key, value in loggable.items():
        print(f"  {key:<16}: {value}")
    print(f"{'─' * 50}")


def place_market_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    quantity: float,
    reduce_only: bool = False,
) -> OrderResult:
    """
    Place a MARKET order on Binance Futures.

    Args:
        client:      Authenticated BinanceFuturesClient.
        symbol:      Trading pair (e.g. 'BTCUSDT').
        side:        'BUY' or 'SELL'.
        quantity:    Number of contracts / coins.
        reduce_only: If True, order may only reduce an existing position.

    Returns:
        OrderResult with success flag and order details.
    """
    params: dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": quantity,
    }
    if reduce_only:
        params["reduceOnly"] = "true"

    _log_order_request("MARKET", params)

    try:
        response = client.place_order(**params)
        result = OrderResult.from_api_response(response)
        logger.info(
            "Market order placed — orderId=%s status=%s executedQty=%s",
            result.order_id,
            result.status,
            result.executed_qty,
        )
        return result

    except Exception as exc:
        logger.error("Market order failed — %s", exc, exc_info=True)
        return OrderResult.from_error(exc)


def place_limit_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    time_in_force: str = "GTC",
    reduce_only: bool = False,
) -> OrderResult:
    """
    Place a LIMIT order on Binance Futures.

    Args:
        client:        Authenticated BinanceFuturesClient.
        symbol:        Trading pair (e.g. 'BTCUSDT').
        side:          'BUY' or 'SELL'.
        quantity:      Number of contracts / coins.
        price:         Limit price.
        time_in_force: 'GTC' (default), 'IOC', or 'FOK'.
        reduce_only:   If True, order may only reduce an existing position.

    Returns:
        OrderResult with success flag and order details.
    """
    params: dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": "LIMIT",
        "quantity": quantity,
        "price": price,
        "timeInForce": time_in_force,
    }
    if reduce_only:
        params["reduceOnly"] = "true"

    _log_order_request("LIMIT", params)

    try:
        response = client.place_order(**params)
        result = OrderResult.from_api_response(response)
        logger.info(
            "Limit order placed — orderId=%s price=%s status=%s",
            result.order_id,
            result.price,
            result.status,
        )
        return result

    except Exception as exc:
        logger.error("Limit order failed — %s", exc, exc_info=True)
        return OrderResult.from_error(exc)


def place_stop_market_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    quantity: float,
    stop_price: float,
    reduce_only: bool = False,
    close_position: bool = False,
) -> OrderResult:
    """
    Place a STOP_MARKET order on Binance Futures.

    A STOP_MARKET order becomes a market order once *stop_price* is reached.
    Commonly used as a stop-loss.

    Args:
        client:         Authenticated BinanceFuturesClient.
        symbol:         Trading pair.
        side:           'BUY' or 'SELL'.
        quantity:       Number of contracts (ignored when close_position=True).
        stop_price:     Trigger price.
        reduce_only:    If True, order may only reduce an existing position.
        close_position: If True, closes the entire position when triggered.

    Returns:
        OrderResult with success flag and order details.
    """
    params: dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": "STOP_MARKET",
        "stopPrice": stop_price,
    }

    if close_position:
        params["closePosition"] = "true"
    else:
        params["quantity"] = quantity

    if reduce_only and not close_position:
        params["reduceOnly"] = "true"

    _log_order_request("STOP_MARKET", params)

    try:
        response = client.place_order(**params)
        result = OrderResult.from_api_response(response)
        logger.info(
            "Stop-market order placed — orderId=%s stopPrice=%s status=%s",
            result.order_id,
            stop_price,
            result.status,
        )
        return result

    except Exception as exc:
        logger.error("Stop-market order failed — %s", exc, exc_info=True)
        return OrderResult.from_error(exc)


# ── Dispatcher ─────────────────────────────────────────────────────────────────


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: str = "GTC",
    reduce_only: bool = False,
    close_position: bool = False,
) -> OrderResult:
    """
    Unified order dispatcher.

    Routes to the appropriate placement function based on *order_type*.
    """
    order_type = order_type.upper()

    if order_type == "MARKET":
        return place_market_order(
            client=client,
            symbol=symbol,
            side=side,
            quantity=quantity,
            reduce_only=reduce_only,
        )

    elif order_type == "LIMIT":
        if price is None:
            raise ValueError("Price is required for LIMIT orders.")
        return place_limit_order(
            client=client,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            time_in_force=time_in_force,
            reduce_only=reduce_only,
        )

    elif order_type == "STOP_MARKET":
        if stop_price is None:
            raise ValueError("Stop price is required for STOP_MARKET orders.")
        return place_stop_market_order(
            client=client,
            symbol=symbol,
            side=side,
            quantity=quantity,
            stop_price=stop_price,
            reduce_only=reduce_only,
            close_position=close_position,
        )

    else:
        raise ValueError(
            f"Unsupported order type '{order_type}'. "
            "Supported types: MARKET, LIMIT, STOP_MARKET."
        )
