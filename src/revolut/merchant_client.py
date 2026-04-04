"""HTTP client for Revolut Merchant API (Bearer token, no OAuth required)."""
import logging
import time
from typing import Any, Dict, List, Optional

import requests

from src.revolut.merchant_api_constants import (
    CUSTOMERS_PATH,
    CUSTOMER_PAYMENT_METHODS_PATH,
    DEFAULT_BACKOFF_INITIAL_SECONDS,
    DEFAULT_BACKOFF_MAX_SECONDS,
    DEFAULT_MAX_HTTP_ATTEMPTS,
    DISPUTES_PATH,
    LOCATIONS_PATH,
    ORDERS_PATH,
    ORDER_PAYMENTS_PATH,
)
from src.revolut.merchant_settings import RevolutMerchantSettings

logger = logging.getLogger(__name__)


class RevolutMerchantApiError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class RevolutMerchantClient:
    def __init__(self, settings: RevolutMerchantSettings):
        self._settings = settings
        self._headers = {
            "Authorization": f"Bearer {settings.api_key}",
            "Revolut-Api-Version": settings.api_version,
            "Content-Type": "application/json",
        }

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = f"{self._settings.api_base_url}{path}"
        delay = DEFAULT_BACKOFF_INITIAL_SECONDS
        last_exc: Optional[Exception] = None
        for attempt in range(DEFAULT_MAX_HTTP_ATTEMPTS):
            resp = requests.request(method, url, params=params, headers=self._headers, timeout=120)
            if resp.status_code == 429 or resp.status_code >= 500:
                last_exc = RevolutMerchantApiError(
                    f"HTTP {resp.status_code}",
                    status_code=resp.status_code,
                    body=resp.text,
                )
                logger.warning(
                    "Revolut Merchant HTTP %s, sleeping %.1fs (attempt %s) path=%s",
                    resp.status_code,
                    delay,
                    attempt + 1,
                    path,
                )
                time.sleep(delay)
                delay = min(delay * 2, DEFAULT_BACKOFF_MAX_SECONDS)
                continue
            if resp.status_code >= 400:
                logger.error(
                    "Revolut Merchant API error: status=%s path=%s body=%s",
                    resp.status_code,
                    path,
                    (resp.text or "")[:800],
                )
                raise RevolutMerchantApiError(
                    f"API request failed: HTTP {resp.status_code}",
                    status_code=resp.status_code,
                    body=resp.text,
                )
            if not resp.content:
                return None
            return resp.json()
        if last_exc:
            raise last_exc
        raise RevolutMerchantApiError("Revolut Merchant backoff exhausted")

    def _extract_list(self, data: Any, *keys: str) -> List[Dict[str, Any]]:
        if data is None:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in keys:
                inner = data.get(key)
                if isinstance(inner, list):
                    return inner
        return []

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def list_orders(
        self,
        *,
        from_iso: Optional[str] = None,
        created_before: Optional[str] = None,
        count: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if from_iso:
            params["from"] = from_iso
        if created_before:
            params["created_before"] = created_before
        if count is not None:
            params["count"] = count
        data = self._request_json("GET", ORDERS_PATH, params=params or None)
        return self._extract_list(data, "orders", "data", "results")

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        data = self._request_json("GET", f"{ORDERS_PATH}/{order_id}")
        if isinstance(data, dict):
            return data
        return None

    def get_order_payments(self, order_id: str) -> List[Dict[str, Any]]:
        path = ORDER_PAYMENTS_PATH.format(order_id=order_id)
        data = self._request_json("GET", path)
        return self._extract_list(data, "payments", "data", "results")

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------

    def list_customers(
        self,
        *,
        count: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if count is not None:
            params["count"] = count
        if cursor:
            params["cursor"] = cursor
        data = self._request_json("GET", CUSTOMERS_PATH, params=params or None)
        return self._extract_list(data, "customers", "data", "results")

    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        data = self._request_json("GET", f"{CUSTOMERS_PATH}/{customer_id}")
        if isinstance(data, dict):
            return data
        return None

    def get_customer_payment_methods(
        self,
        customer_id: str,
        *,
        only_merchant: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        path = CUSTOMER_PAYMENT_METHODS_PATH.format(customer_id=customer_id)
        params: Dict[str, Any] = {}
        if only_merchant is not None:
            params["only_merchant"] = str(only_merchant).lower()
        data = self._request_json("GET", path, params=params or None)
        return self._extract_list(data, "payment_methods", "paymentMethods", "data", "results")

    # ------------------------------------------------------------------
    # Disputes
    # ------------------------------------------------------------------

    def list_disputes(
        self,
        *,
        from_iso: Optional[str] = None,
        created_before: Optional[str] = None,
        count: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if from_iso:
            params["from"] = from_iso
        if created_before:
            params["created_before"] = created_before
        if count is not None:
            params["count"] = count
        data = self._request_json("GET", DISPUTES_PATH, params=params or None)
        return self._extract_list(data, "disputes", "data", "results")

    # ------------------------------------------------------------------
    # Locations
    # ------------------------------------------------------------------

    def list_locations(self) -> List[Dict[str, Any]]:
        data = self._request_json("GET", LOCATIONS_PATH)
        return self._extract_list(data, "locations", "data", "results")
