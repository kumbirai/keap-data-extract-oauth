"""Checkpoint utilities for Revolut Merchant API sync."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from dateutil import parser as date_parser


# ------------------------------------------------------------------
# Entity key helpers
# ------------------------------------------------------------------

MERCHANT_ORDERS_ENTITY = "revolut_merchant_orders"
MERCHANT_CUSTOMERS_ENTITY = "revolut_merchant_customers"
MERCHANT_DISPUTES_ENTITY = "revolut_merchant_disputes"
MERCHANT_LOCATIONS_ENTITY = "revolut_merchant_locations"


# ------------------------------------------------------------------
# Timestamp parsing
# ------------------------------------------------------------------

def parse_iso_to_utc(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = date_parser.isoparse(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


# ------------------------------------------------------------------
# Window computation
# ------------------------------------------------------------------

def compute_window(
    *,
    update: bool,
    state: Dict[str, Any],
    lookback_days: int,
    initial_history_days: int,
    now: datetime,
) -> Tuple[datetime, datetime]:
    """
    Return (window_from, window_to) in UTC.

    Incremental: anchor window_from at last_run_at - lookback_days.
    Full: window_from = now - initial_history_days.
    window_to is always `now`.
    """
    window_to = now.astimezone(timezone.utc)
    lookback_delta = timedelta(days=lookback_days)
    initial_delta = timedelta(days=initial_history_days)

    if update:
        last_run = parse_iso_to_utc(state.get("last_run_at"))
        if last_run is not None:
            window_from = last_run - lookback_delta
            return window_from, window_to

    window_from = window_to - initial_delta
    return window_from, window_to


# ------------------------------------------------------------------
# Pagination helpers
# ------------------------------------------------------------------

def next_page_created_before(items: list, *, page_size: int) -> Optional[str]:
    """
    If the page is full (len == page_size), return ISO created_at of the last item
    to use as `created_before` for the next page request.
    Returns None when the page is the last page.
    """
    if len(items) < page_size:
        return None
    last = items[-1]
    if not isinstance(last, dict):
        return None
    ca = last.get("created_at")
    if ca is None:
        return None
    return str(ca)


# ------------------------------------------------------------------
# State merging
# ------------------------------------------------------------------

def merge_state(base: Optional[dict], partial: Dict[str, Any]) -> dict:
    out = deepcopy(base) if base else {}
    out.update(partial)
    return out
