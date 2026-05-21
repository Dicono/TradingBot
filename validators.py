"""
Input validation for trading bot CLI parameters.
All validators raise ValueError with clear messages on failure.
"""

from __future__ import annotations

from typing import Optional

from bot.logging_config import get_logger

logger = get_logger("validators")

# ── Constants ──────────────────────────────────────────────────────────────────

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}
VALID_TIME_IN_FORCE = {"GTC", "IOC", "FOK", "GTX"}

# Reasonable guard-rails for quantity and price
MIN_QUANTITY = 0.000001
MAX_QUANTITY = 1_000_000
MIN_PRICE = 0.000001
MAX_PRICE = 10_000_000


# ── Individual field validators ────────────────────────────────────────────────


def validate_symbol(symbol: str) -> str:
    """
    Normalise and validate a trading symbol.

    Rules:
    - Non-empty string
    - Uppercase letters + digits only
    - Must end with 'USDT' for USDT-M futures

    Returns the uppercased symbol.
    """
    if not symbol or not symbol.strip():
        raise ValueError("Symbol must not be empty.")

    symbol = symbol.strip().upper()

    if not symbol.isalnum():
        raise ValueError(
            f"Symbol '{symbol}' contains invalid characters. "
            "Only alphanumeric characters are allowed (e.g. BTCUSDT)."
        )

    if not symbol.endswith("USDT"):
        raise ValueError(
            f"Symbol '{symbol}' does not end with 'USDT'. "
            "Only USDT-M perpetual futures are supported (e.g. BTCUSDT, ETHUSDT)."
        )

    logger.debug("Symbol validated: %s", symbol)
    return symbol


def validate_side(side: str) -> str:
    """
    Validate order side (BUY / SELL).

    Returns the uppercased side string.
    """
    if not side or not side.strip():
        raise ValueError("Side must not be empty.")

    side = side.strip().upper()

    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )

    logger.debug("Side validated: %s", side)
    return side


def validate_order_type(order_type: str) -> str:
    """
    Validate order type (MARKET / LIMIT / STOP_MARKET).

    Returns the uppercased order-type string.
    """
    if not order_type or not order_type.strip():
        raise ValueError("Order type must not be empty.")

    order_type = order_type.strip().upper()

    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )

    logger.debug("Order type validated: %s", order_type)
    return order_type


def validate_quantity(quantity: float | str) -> float:
    """
    Validate order quantity.

    - Must be convertible to float
    - Must be positive and within reasonable bounds

    Returns the quantity as a float.
    """
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValueError(
            f"Quantity '{quantity}' is not a valid number."
        )

    if qty <= 0:
        raise ValueError(f"Quantity must be positive, got {qty}.")

    if qty < MIN_QUANTITY:
        raise ValueError(
            f"Quantity {qty} is below the minimum allowed value of {MIN_QUANTITY}."
        )

    if qty > MAX_QUANTITY:
        raise ValueError(
            f"Quantity {qty} exceeds the maximum allowed value of {MAX_QUANTITY}."
        )

    logger.debug("Quantity validated: %s", qty)
    return qty


def validate_price(price: Optional[float | str], order_type: str) -> Optional[float]:
    """
    Validate order price.

    - For LIMIT and STOP_MARKET orders, price is mandatory.
    - For MARKET orders, price must be None / omitted.

    Returns the price as a float, or None for market orders.
    """
    order_type = order_type.strip().upper()

    if order_type in ("MARKET", "STOP_MARKET"):
        if price is not None:
            logger.warning(
                "Price '%s' supplied for %s order — it will be ignored.", price, order_type
            )
        return None

    # LIMIT requires a price
    if price is None:
        raise ValueError(
            f"Price is required for '{order_type}' orders but was not provided."
        )

    try:
        p = float(price)
    except (TypeError, ValueError):
        raise ValueError(f"Price '{price}' is not a valid number.")

    if p <= 0:
        raise ValueError(f"Price must be positive, got {p}.")

    if p < MIN_PRICE:
        raise ValueError(
            f"Price {p} is below the minimum allowed value of {MIN_PRICE}."
        )

    if p > MAX_PRICE:
        raise ValueError(
            f"Price {p} exceeds the maximum allowed value of {MAX_PRICE}."
        )

    logger.debug("Price validated: %s", p)
    return p


def validate_stop_price(
    stop_price: Optional[float | str], order_type: str
) -> Optional[float]:
    """
    Validate stop price for STOP_MARKET orders.

    Returns the stop price as a float, or None when not applicable.
    """
    order_type = order_type.strip().upper()

    if order_type != "STOP_MARKET":
        return None

    if stop_price is None:
        raise ValueError("Stop price is required for STOP_MARKET orders.")

    try:
        sp = float(stop_price)
    except (TypeError, ValueError):
        raise ValueError(f"Stop price '{stop_price}' is not a valid number.")

    if sp <= 0:
        raise ValueError(f"Stop price must be positive, got {sp}.")

    logger.debug("Stop price validated: %s", sp)
    return sp


# ── Composite validator ────────────────────────────────────────────────────────


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float | str,
    price: Optional[float | str] = None,
    stop_price: Optional[float | str] = None,
) -> dict:
    """
    Run all field validators and return a clean, typed parameter dict.

    Raises ValueError with a descriptive message if any field is invalid.
    """
    errors: list[str] = []

    # Validate each field independently to collect all errors at once
    clean: dict = {}

    try:
        clean["symbol"] = validate_symbol(symbol)
    except ValueError as exc:
        errors.append(str(exc))

    try:
        clean["side"] = validate_side(side)
    except ValueError as exc:
        errors.append(str(exc))

    try:
        clean["order_type"] = validate_order_type(order_type)
    except ValueError as exc:
        errors.append(str(exc))

    try:
        clean["quantity"] = validate_quantity(quantity)
    except ValueError as exc:
        errors.append(str(exc))

    # Price / stop-price validation depends on order_type being valid
    resolved_type = clean.get("order_type", order_type)

    try:
        clean["price"] = validate_price(price, resolved_type)
    except ValueError as exc:
        errors.append(str(exc))

    try:
        clean["stop_price"] = validate_stop_price(stop_price, resolved_type)
    except ValueError as exc:
        errors.append(str(exc))

    if errors:
        joined = "\n  • ".join(errors)
        raise ValueError(f"Validation failed:\n  • {joined}")

    logger.info(
        "All parameters validated — symbol=%s side=%s type=%s qty=%s price=%s",
        clean["symbol"],
        clean["side"],
        clean["order_type"],
        clean["quantity"],
        clean.get("price"),
    )
    return clean
