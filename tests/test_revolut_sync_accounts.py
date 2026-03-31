"""Tests for Revolut account list filtering (shared by dimension sync and transaction scope)."""
from src.revolut.sync_accounts import filtered_revolut_account_ids


def test_filtered_revolut_account_ids_respects_allowlist():
    raw = [
        {"id": "a1", "name": "One"},
        {"id": "a2", "name": "Two"},
        "not-a-dict",
        {"no_id": True},
    ]
    assert filtered_revolut_account_ids(raw, {"a2"}) == ["a2"]


def test_filtered_revolut_account_ids_all_when_no_allowlist():
    raw = [{"id": "x1"}, {"id": "x2"}]
    assert filtered_revolut_account_ids(raw, None) == ["x1", "x2"]


def test_filtered_revolut_account_ids_non_list():
    assert filtered_revolut_account_ids({}, None) == []
