"""Tests for Stripe object → row mappers (dict fixtures)."""
from datetime import datetime, timezone
from types import SimpleNamespace

from src.stripe import mappers


def _now():
    return datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_map_charge_minimal():
    obj = SimpleNamespace(
        id="ch_1",
        amount=1099,
        amount_refunded=0,
        currency="usd",
        created=1700000000,
        customer=None,
        invoice=None,
        payment_intent=None,
        balance_transaction="txn_1",
        description=None,
        receipt_email="a@b.com",
        paid=True,
        refunded=False,
        status="succeeded",
        failure_code=None,
        failure_message=None,
        livemode=False,
        metadata={"k": "v"},
    )
    row = mappers.map_charge(obj, None, _now(), store_raw=False)
    assert row["id"] == "ch_1"
    assert row["amount"] == 1099
    assert row["balance_transaction_id"] == "txn_1"
    assert row["metadata"] == {"k": "v"}
    assert row["raw_payload"] is None
    assert row["stripe_account_id"] is None


def test_map_balance_transaction_source_object():
    src = SimpleNamespace(id="ch_x", object="charge")
    obj = SimpleNamespace(
        id="txn_1",
        amount=100,
        fee=3,
        net=97,
        currency="usd",
        type="charge",
        created=1700000000,
        available_on=1700086400,
        source=src,
        reporting_category="charge",
        metadata={},
    )
    row = mappers.map_balance_transaction(obj, "acct_1", _now(), False)
    assert row["source_id"] == "ch_x"
    assert row["source_type"] == "charge"
    assert row["stripe_account_id"] == "acct_1"


def test_map_balance_transaction_source_string():
    obj = SimpleNamespace(
        id="txn_2",
        amount=50,
        fee=0,
        net=50,
        currency="usd",
        type="adjustment",
        created=1700000000,
        available_on=None,
        source="ch_y",
        reporting_category=None,
        metadata=None,
    )
    row = mappers.map_balance_transaction(obj, None, _now(), False)
    assert row["source_id"] == "ch_y"
    assert row["source_type"] is None


def test_map_transfer_prefers_api_status():
    obj = SimpleNamespace(
        id="tr_1",
        amount=500,
        currency="usd",
        created=1700000000,
        destination="acct_z",
        status="paid",
        reversed=False,
        description=None,
        metadata=None,
    )
    row = mappers.map_transfer(obj, None, _now(), False)
    assert row["status"] == "paid"


def test_map_product_default_price_expanded():
    dp = SimpleNamespace(id="price_1")
    obj = SimpleNamespace(
        id="prod_1",
        name="N",
        description="D",
        active=True,
        default_price=dp,
        created=1700000000,
        metadata={},
    )
    row = mappers.map_product(obj, None, _now(), False)
    assert row["default_price_id"] == "price_1"
