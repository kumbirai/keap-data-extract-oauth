"""Tests for Revolut API JSON → row mappers."""
from datetime import datetime, timezone

from src.revolut import mappers


def test_map_transaction_card_payment():
    now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    payload = {
        "id": "txn-1",
        "type": "card_payment",
        "state": "completed",
        "amount": 1999,
        "currency": "GBP",
        "created_at": "2026-01-10T10:00:00.000Z",
        "updated_at": "2026-01-10T10:01:00.000Z",
        "completed_at": "2026-01-10T10:01:00.000Z",
        "related_transaction_id": None,
        "merchant": {"name": "Cafe", "city": "London", "category_code": "5812"},
        "description": "Coffee",
    }
    row = mappers.map_transaction(
        payload, default_account_id="acc-1", now=now, store_raw=False
    )
    assert row["id"] == "txn-1"
    assert row["account_id"] == "acc-1"
    assert row["type"] == "card_payment"
    assert row["state"] == "completed"
    assert row["amount"] == 1999
    assert row["currency"] == "GBP"
    assert row["merchant_name"] == "Cafe"
    assert row["merchant_category_code"] == "5812"
    assert row["raw_payload"] is None
    assert row["created_at"] is not None


def test_map_transaction_fee_with_related():
    now = datetime(2026, 1, 15, tzinfo=timezone.utc)
    payload = {
        "id": "fee-1",
        "account_id": "acc-2",
        "type": "fee",
        "state": "completed",
        "amount": -50,
        "currency": "EUR",
        "created_at": "2026-01-11T08:00:00Z",
        "related_transaction_id": "parent-9",
    }
    row = mappers.map_transaction(payload, default_account_id=None, now=now, store_raw=True)
    assert row["related_transaction_id"] == "parent-9"
    assert row["raw_payload"]["id"] == "fee-1"


def test_map_account_balance_float():
    now = datetime(2026, 1, 15, tzinfo=timezone.utc)
    payload = {
        "id": "a1",
        "name": "Main",
        "currency": "GBP",
        "state": "active",
        "balance": 100.5,
        "updated_at": "2026-01-01T00:00:00Z",
    }
    row = mappers.map_account(payload, now=now, store_raw=False)
    assert row["id"] == "a1"
    assert row["balance"] == 10050
