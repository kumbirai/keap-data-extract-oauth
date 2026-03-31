"""
Checkpoint payload for Revolut transaction sync (one extraction_state row per account).

entity_type: revolut_transactions:{account_uuid}
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from dateutil import parser as date_parser


def transactions_entity_key(account_id: str) -> str:
    return f"revolut_transactions:{account_id}"


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


def compute_transaction_window(
    *,
    update: bool,
    state: Dict[str, Any],
    lookback_days: int,
    initial_history_days: int,
    now: datetime,
) -> Tuple[datetime, datetime]:
    """
    Return (window_from, window_to) inclusive range in UTC.

    Incremental runs anchor `from` using last_max_created_at minus lookback; full runs use
    initial_history_days. window_to is always `now`.
    """
    window_to = now.astimezone(timezone.utc)
    lookback_delta = timedelta(days=lookback_days)
    initial_delta = timedelta(days=initial_history_days)

    if update:
        last_max = parse_iso_to_utc(state.get("last_max_created_at"))
        if last_max is not None:
            window_from = last_max - lookback_delta
            return window_from, window_to

    window_from = window_to - initial_delta
    return window_from, window_to


def next_pagination_to(items: list, *, count: int) -> Optional[str]:
    """
    If the page is full, return ISO `created_at` of the last row (oldest in page, reverse chrono)
    for the next request's `to` parameter.
    """
    if len(items) < count:
        return None
    last = items[-1]
    if not isinstance(last, dict):
        return None
    ca = last.get("created_at")
    if ca is None:
        return None
    return str(ca)


def merge_state(base: Optional[dict], partial: Dict[str, Any]) -> dict:
    out = deepcopy(base) if base else {}
    out.update(partial)
    return out


def max_created_iso(existing: Optional[str], items: list) -> Optional[str]:
    best = parse_iso_to_utc(existing)
    for row in items:
        if not isinstance(row, dict):
            continue
        dt = parse_iso_to_utc(str(row.get("created_at") or ""))
        if dt is None:
            continue
        if best is None or dt > best:
            best = dt
    return best.isoformat().replace("+00:00", "Z") if best else existing
