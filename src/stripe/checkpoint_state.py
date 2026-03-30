"""Merge per-account Stripe sync state stored in extraction_state.checkpoint_json."""
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from dateutil import parser as date_parser


def account_key(stripe_account_id: Optional[str]) -> str:
    return stripe_account_id if stripe_account_id else "__platform__"


def get_account_state(checkpoint_root: Optional[dict], stripe_account_id: Optional[str]) -> dict:
    if not checkpoint_root:
        return {}
    accounts = checkpoint_root.get("accounts") or {}
    return dict(accounts.get(account_key(stripe_account_id)) or {})


def merge_account_state(
    checkpoint_root: Optional[dict],
    stripe_account_id: Optional[str],
    partial: Dict[str, Any],
) -> dict:
    root = deepcopy(checkpoint_root) if checkpoint_root else {}
    accounts = dict(root.get("accounts") or {})
    key = account_key(stripe_account_id)
    acc = dict(accounts.get(key) or {})
    acc.update(partial)
    accounts[key] = acc
    root["accounts"] = accounts
    return root


def resolve_created_gte(
    update: bool,
    acc_state: dict,
    last_loaded_iso: Optional[str],
    lookback_seconds: int,
) -> Optional[int]:
    if not update:
        return None
    wm = acc_state.get("max_created_unix")
    if wm is not None and int(wm) <= 0:
        wm = None
    if wm is None and last_loaded_iso:
        try:
            dt = date_parser.isoparse(last_loaded_iso.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            wm = int(dt.timestamp())
        except (ValueError, TypeError, OSError):
            wm = None
    if wm is None:
        return None
    return max(0, int(wm) - int(lookback_seconds))


def max_created_unix_from_objects(objects, attr: str = "created") -> int:
    m = 0
    for obj in objects:
        v = getattr(obj, attr, None)
        if v is not None:
            try:
                m = max(m, int(v))
            except (TypeError, ValueError):
                pass
    return m
