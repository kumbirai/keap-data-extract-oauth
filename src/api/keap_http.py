"""Shared Keap CRM HTTP response handling for v1 and v2 API surfaces."""
import logging
from typing import Any, Callable, Dict, Optional

import requests

from .exceptions import (
    KeapAPIError,
    KeapAuthenticationError,
    KeapBadRequestError,
    KeapForbiddenError,
    KeapNotFoundError,
    KeapQuotaExhaustedError,
    KeapRateLimitError,
    KeapServerError,
)

logger = logging.getLogger(__name__)


def safe_int_parse(value: Any, default: int = 0) -> int:
    if not value or str(value).strip() == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def has_meaningful_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _log_success_payload_structure(data: Any) -> None:
    if isinstance(data, dict):
        logger.info("API Response is a dict with keys: %s", list(data.keys()))
        for key, value in data.items():
            if isinstance(value, list):
                logger.info("API Response '%s' contains %d items", key, len(value))
            elif isinstance(value, dict):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("API Response '%s' is a dict with %d keys", key, len(value))
    elif isinstance(data, list):
        logger.info("API Response is a list with %d items", len(data))
    else:
        logger.info("API Response type: %s", type(data))


def handle_keap_response(
    response: requests.Response,
    *,
    token_manager: Any,
    client_id: str,
    refresh_headers: Callable[[], None],
) -> Dict[str, Any]:
    """Parse JSON body on success; map HTTP errors to Keap exceptions (shared v1/v2)."""
    quota_headers = {
        "x-keap-product-quota-limit": response.headers.get("x-keap-product-quota-limit"),
        "x-keap-product-quota-time-unit": response.headers.get("x-keap-product-quota-time-unit"),
        "x-keap-product-quota-interval": response.headers.get("x-keap-product-quota-interval"),
        "x-keap-product-quota-available": response.headers.get("x-keap-product-quota-available"),
        "x-keap-product-quota-used": response.headers.get("x-keap-product-quota-used"),
        "x-keap-product-quota-expiry-time": response.headers.get("x-keap-product-quota-expiry-time"),
    }
    throttle_headers = {
        "x-keap-product-throttle-limit": response.headers.get("x-keap-product-throttle-limit"),
        "x-keap-product-throttle-time-unit": response.headers.get("x-keap-product-throttle-time-unit"),
        "x-keap-product-throttle-interval": response.headers.get("x-keap-product-throttle-interval"),
        "x-keap-product-throttle-available": response.headers.get("x-keap-product-throttle-available"),
        "x-keap-product-throttle-used": response.headers.get("x-keap-product-throttle-used"),
    }
    tenant_headers = {
        "x-keap-tenant-id": response.headers.get("x-keap-tenant-id"),
        "x-keap-tenant-throttle-limit": response.headers.get("x-keap-tenant-throttle-limit"),
        "x-keap-tenant-throttle-time-unit": response.headers.get("x-keap-tenant-throttle-time-unit"),
        "x-keap-tenant-throttle-interval": response.headers.get("x-keap-tenant-throttle-interval"),
        "x-keap-tenant-throttle-available": response.headers.get("x-keap-tenant-throttle-available"),
        "x-keap-tenant-throttle-used": response.headers.get("x-keap-tenant-throttle-used"),
    }

    logger.debug("Quota Headers: %s", quota_headers)
    logger.debug("Throttle Headers: %s", throttle_headers)
    logger.debug("Tenant Headers: %s", tenant_headers)

    if logger.isEnabledFor(logging.DEBUG):
        for header_name, header_value in response.headers.items():
            if "keap" in header_name.lower():
                logger.debug("  %s: %r", header_name, header_value)

    try:
        response.raise_for_status()
        data = response.json()
        _log_success_payload_structure(data)
        logger.debug("Full API Response: %s", data)
        return data
    except requests.exceptions.HTTPError as e:
        status_code = response.status_code
        logger.error("HTTP Error: %s - %s", status_code, e)
        logger.error("Response content: %s", response.text)

        if status_code == 401:
            logger.warning("Received 401, attempting to refresh token...")
            if token_manager.refresh_access_token(client_id):
                logger.info("Token refreshed, updating headers...")
                refresh_headers()
                raise KeapAuthenticationError("Token expired, please retry the request") from e
            raise KeapAuthenticationError(
                "Invalid token or authentication failed. Please re-authorize."
            ) from e
        if status_code == 403:
            logger.error(
                "Keap API returned 403 Forbidden for %s — check OAuth scopes in the Keap "
                "developer console for this resource.",
                response.url,
            )
            raise KeapForbiddenError(
                f"Access forbidden (403). Missing or insufficient OAuth scope for: {response.url}"
            ) from e
        if status_code == 404:
            raise KeapNotFoundError(f"Resource not found: {response.url}") from e
        if status_code == 400:
            raise KeapBadRequestError(f"Bad request (400): {response.url} — {response.text}") from e
        if status_code == 429:
            logger.info(
                "Rate limit exceeded. Headers: Quota=%s, Throttle=%s, Tenant=%s",
                quota_headers,
                throttle_headers,
                tenant_headers,
            )
            quota_available_raw = quota_headers.get("x-keap-product-quota-available")
            throttle_available_raw = throttle_headers.get("x-keap-product-throttle-available")
            tenant_available_raw = tenant_headers.get("x-keap-tenant-throttle-available")
            quota_available = safe_int_parse(quota_available_raw)
            throttle_available = safe_int_parse(throttle_available_raw)
            tenant_available = safe_int_parse(tenant_available_raw)

            if (
                has_meaningful_value(quota_available_raw)
                and quota_available == 0
                and quota_headers.get("x-keap-product-quota-time-unit", "").lower() == "day"
            ):
                quota_limit = quota_headers.get("x-keap-product-quota-limit", "unknown")
                quota_used = quota_headers.get("x-keap-product-quota-used", "unknown")
                logger.error(
                    "Daily API quota exhausted. Quota limit: %s, Used: %s.",
                    quota_limit,
                    quota_used,
                )
                raise KeapQuotaExhaustedError(
                    f"Daily API quota exhausted (limit: {quota_limit}, used: {quota_used}). "
                    "Quota will reset at midnight GMT."
                ) from e

            if (
                (
                    quota_headers.get("x-keap-product-quota-available") is None
                    or quota_headers.get("x-keap-product-quota-available") == ""
                )
                and throttle_available == 0
            ):
                logger.warning(
                    "Quota headers missing/empty; throttle limit hit. Treating as product throttle."
                )
                limit_type = "product throttle"
                limit_value = safe_int_parse(throttle_headers.get("x-keap-product-throttle-limit"))
            elif (
                (
                    quota_headers.get("x-keap-product-quota-available") is None
                    or quota_headers.get("x-keap-product-quota-available") == ""
                )
                and tenant_available == 0
            ):
                logger.warning(
                    "Quota headers missing/empty; tenant throttle hit. Treating as tenant throttle."
                )
                limit_type = "tenant throttle"
                limit_value = safe_int_parse(tenant_headers.get("x-keap-tenant-throttle-limit"))
            elif has_meaningful_value(throttle_available_raw) and throttle_available == 0:
                limit_type = "product throttle"
                limit_value = safe_int_parse(throttle_headers.get("x-keap-product-throttle-limit"))
            elif has_meaningful_value(tenant_available_raw) and tenant_available == 0:
                limit_type = "tenant throttle"
                limit_value = safe_int_parse(tenant_headers.get("x-keap-tenant-throttle-limit"))
            else:
                limit_type = "unknown"
                limit_value = 0

            all_headers = {**quota_headers, **throttle_headers, **tenant_headers}
            raise KeapRateLimitError(
                f"Rate limit exceeded ({limit_type}, limit: {limit_value}). "
                "Will retry after throttle period.",
                response_headers=all_headers,
            ) from e
        if status_code >= 500:
            raise KeapServerError(f"Server error: {e}") from e
        raise KeapAPIError(f"API request failed: {e}") from e
    except requests.exceptions.JSONDecodeError as e:
        logger.error("JSON Decode Error: %s", e)
        logger.error("Response content: %s", response.text)
        raise KeapAPIError(f"Failed to parse JSON response: {e}") from e
    except requests.exceptions.RequestException as e:
        logger.error("Request Error: %s", e)
        raise KeapAPIError(f"Request failed: {e}") from e
