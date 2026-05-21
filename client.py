"""
Binance Futures Testnet REST API client.

Handles HMAC-SHA256 request signing, rate-limit awareness, and structured
error surfacing.  All network I/O is synchronous (requests library).
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from bot.logging_config import get_logger

logger = get_logger("client")

# ── Defaults ───────────────────────────────────────────────────────────────────

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_RECV_WINDOW = 5_000   # milliseconds
REQUEST_TIMEOUT = 10          # seconds


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error response."""

    def __init__(self, code: int, message: str, http_status: int = 0) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(f"[HTTP {http_status}] Binance error {code}: {message}")


class BinanceFuturesClient:
    """
    Thin wrapper around the Binance USDT-M Futures REST API.

    Responsibilities:
    - Sign every authenticated request with HMAC-SHA256
    - Log request parameters and raw responses
    - Raise BinanceAPIError for API-level errors
    - Raise requests.RequestException for network failures
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        recv_window: int = DEFAULT_RECV_WINDOW,
        timeout: int = REQUEST_TIMEOUT,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("API key must not be empty.")
        if not api_secret or not api_secret.strip():
            raise ValueError("API secret must not be empty.")

        self.api_key = api_key.strip()
        self._api_secret = api_secret.strip().encode()
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self.timeout = timeout

        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )

        logger.info(
            "BinanceFuturesClient initialised — base_url=%s recv_window=%sms",
            self.base_url,
            self.recv_window,
        )

    # ── Signing helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _timestamp() -> int:
        """Return current UTC timestamp in milliseconds."""
        return int(time.time() * 1000)

    def _sign(self, params: dict) -> dict:
        """Add timestamp + HMAC-SHA256 signature to *params* and return it."""
        params["timestamp"] = self._timestamp()
        params["recvWindow"] = self.recv_window

        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret,
            query_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        params["signature"] = signature
        return params

    # ── Low-level HTTP helpers ─────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        signed: bool = False,
    ) -> Any:
        """
        Send an HTTP request and return the parsed JSON response.

        Args:
            method:   HTTP method ('GET', 'POST', 'DELETE').
            endpoint: API endpoint path (e.g. '/fapi/v1/order').
            params:   Query / body parameters.
            signed:   Whether to add HMAC signature.

        Returns:
            Parsed JSON response (dict or list).

        Raises:
            BinanceAPIError: When the API returns a non-2xx or error payload.
            requests.RequestException: On network / timeout failures.
        """
        params = params or {}

        if signed:
            params = self._sign(params)

        url = f"{self.base_url}{endpoint}"

        # Log the outgoing request (mask secret fields)
        loggable = {k: v for k, v in params.items() if k != "signature"}
        logger.info("→ %s %s | params=%s", method.upper(), endpoint, loggable)

        try:
            if method.upper() in ("GET", "DELETE"):
                response = self._session.request(
                    method, url, params=params, timeout=self.timeout
                )
            else:
                response = self._session.request(
                    method, url, data=params, timeout=self.timeout
                )
        except requests.exceptions.Timeout:
            logger.error("Request timed out after %ss — %s %s", self.timeout, method, url)
            raise
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error — %s %s — %s", method, url, exc)
            raise

        logger.info(
            "← HTTP %s | %s %s | body=%s",
            response.status_code,
            method.upper(),
            endpoint,
            response.text[:500],   # truncate very large responses in log
        )

        # Parse JSON
        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response — status=%s body=%s", response.status_code, response.text)
            response.raise_for_status()
            raise

        # Binance error payload has 'code' (negative int) and 'msg'
        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            code = data.get("code", -1)
            msg = data.get("msg", "Unknown error")
            logger.error("Binance API error — code=%s msg=%s", code, msg)
            raise BinanceAPIError(code=code, message=msg, http_status=response.status_code)

        if not response.ok:
            logger.error("HTTP error — status=%s body=%s", response.status_code, response.text)
            response.raise_for_status()

        return data

    # ── Public API methods ─────────────────────────────────────────────────────

    def get_server_time(self) -> int:
        """Return Binance server time in milliseconds."""
        data = self._request("GET", "/fapi/v1/time")
        return data["serverTime"]

    def get_exchange_info(self) -> dict:
        """Return exchange information (trading pairs, filters, etc.)."""
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_account_balance(self) -> list[dict]:
        """Return futures account balance for all assets."""
        return self._request("GET", "/fapi/v2/balance", signed=True)

    def get_position_info(self, symbol: Optional[str] = None) -> list[dict]:
        """Return open position(s). Optionally filter by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v2/positionRisk", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> dict:
        """Fetch details of a specific order."""
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", params=params, signed=True)

    def get_open_orders(self, symbol: Optional[str] = None) -> list[dict]:
        """List all open orders. Optionally filter by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an existing open order."""
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("DELETE", "/fapi/v1/order", params=params, signed=True)

    def place_order(self, **kwargs) -> dict:
        """
        Place a new futures order.

        Keyword arguments are passed directly as API parameters.
        Required keys depend on order type — use orders.py helpers instead of
        calling this directly from user code.
        """
        return self._request("POST", "/fapi/v1/order", params=kwargs, signed=True)
