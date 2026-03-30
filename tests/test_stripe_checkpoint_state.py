"""Tests for Stripe checkpoint / watermark helpers."""
from datetime import datetime, timezone

from src.stripe.checkpoint_state import (
    account_key,
    get_account_state,
    merge_account_state,
    resolve_created_gte,
)


def test_account_key_platform():
    assert account_key(None) == "__platform__"
    assert account_key("") == "__platform__"


def test_account_key_connected():
    assert account_key("acct_123") == "acct_123"


def test_merge_account_state_isolated():
    root = merge_account_state(None, "acct_a", {"starting_after": "x"})
    assert root["accounts"]["acct_a"]["starting_after"] == "x"
    root2 = merge_account_state(root, "acct_b", {"max_created_unix": 99})
    assert root2["accounts"]["acct_a"]["starting_after"] == "x"
    assert root2["accounts"]["acct_b"]["max_created_unix"] == 99


def test_get_account_state():
    root = {"accounts": {"__platform__": {"a": 1}}}
    assert get_account_state(root, None) == {"a": 1}


def test_resolve_created_gte_with_watermark():
    gte = resolve_created_gte(
        True,
        {"max_created_unix": 1000},
        None,
        100,
    )
    assert gte == 900


def test_resolve_created_gte_from_last_loaded():
    dt = datetime(2024, 1, 2, tzinfo=timezone.utc)
    iso = dt.isoformat()
    gte = resolve_created_gte(True, {}, iso, 0)
    assert gte == int(dt.timestamp())


def test_resolve_created_gte_full_load():
    assert resolve_created_gte(False, {"max_created_unix": 100}, None, 10) is None


def test_resolve_created_gte_zero_watermark_falls_back_to_last_loaded():
    dt = datetime(2024, 6, 1, tzinfo=timezone.utc)
    iso = dt.isoformat()
    gte = resolve_created_gte(True, {"max_created_unix": 0}, iso, 100)
    assert gte == max(0, int(dt.timestamp()) - 100)
