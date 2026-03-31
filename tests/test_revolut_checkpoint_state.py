"""Tests for Revolut transaction window and pagination helpers."""
from datetime import datetime, timezone, timedelta

from src.revolut.checkpoint_state import (
    compute_transaction_window,
    max_created_iso,
    next_pagination_to,
    parse_iso_to_utc,
    transactions_entity_key,
)


def test_transactions_entity_key():
    assert transactions_entity_key("uuid-here") == "revolut_transactions:uuid-here"


def test_compute_window_full_load():
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    wf, wt = compute_transaction_window(
        update=False,
        state={},
        lookback_days=7,
        initial_history_days=30,
        now=now,
    )
    assert wt == now.astimezone(timezone.utc)
    assert (wt - wf).days == 30


def test_compute_window_incremental_with_watermark():
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    state = {"last_max_created_at": "2026-05-20T10:00:00Z"}
    wf, wt = compute_transaction_window(
        update=True,
        state=state,
        lookback_days=5,
        initial_history_days=30,
        now=now,
    )
    expected_from = parse_iso_to_utc("2026-05-20T10:00:00Z") - timedelta(days=5)
    assert abs((wf - expected_from).total_seconds()) < 1
    assert wt == now.astimezone(timezone.utc)


def test_next_pagination_to_full_page():
    items = [{"created_at": "2026-01-01T00:00:00Z"}] * 3
    assert next_pagination_to(items, count=3) == "2026-01-01T00:00:00Z"
    assert next_pagination_to(items[:2], count=3) is None


def test_max_created_iso():
    items = [
        {"created_at": "2026-01-01T10:00:00Z"},
        {"created_at": "2026-01-02T10:00:00Z"},
    ]
    assert max_created_iso(None, items).startswith("2026-01-02")
