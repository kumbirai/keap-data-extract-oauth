"""Tests for Stripe object → row mappers (dict fixtures)."""
import pytest
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


def test_map_customer_minimal():
    obj = SimpleNamespace(
        id="cus_1",
        email="A@B.com",
        name="N",
        phone=None,
        description=None,
        currency="usd",
        balance=-100,
        delinquent=False,
        created=1700000000,
        default_source=None,
        invoice_prefix="INV",
        tax_exempt="none",
        metadata={},
    )
    row = mappers.map_customer(obj, None, _now(), False)
    assert row["id"] == "cus_1"
    assert row["email"] == "A@B.com"
    assert row["balance"] == -100
    assert row["raw_payload"] is None


def test_map_invoice_line_item_missing_amount_raises():
    obj = SimpleNamespace(
        id="il_x",
        invoice=None,
        subscription=None,
        subscription_item=None,
        price=None,
        quantity=None,
        amount=None,
        currency="usd",
        description=None,
        period=None,
        type=None,
        proration=None,
        metadata={},
    )
    with pytest.raises(ValueError, match="amount"):
        mappers.map_invoice_line_item(obj, None, _now(), False, invoice_id="in_1")


def test_map_invoice_line_item_with_period():
    period = SimpleNamespace(start=1700000000, end=1700086400)
    price = SimpleNamespace(id="price_1", product="prod_1")
    obj = SimpleNamespace(
        id="il_1",
        invoice=None,
        subscription=None,
        subscription_item=None,
        price=price,
        quantity=2,
        amount=500,
        currency="usd",
        description="Line",
        period=period,
        type="subscription",
        proration=False,
        metadata={},
    )
    row = mappers.map_invoice_line_item(obj, "acct_1", _now(), False, invoice_id="in_1")
    assert row["id"] == "il_1"
    assert row["invoice_id"] == "in_1"
    assert row["amount"] == 500
    assert row["price_id"] == "price_1"
    assert row["product_id"] == "prod_1"
    assert "raw_payload" not in row
    assert row["stripe_account_id"] == "acct_1"


def test_map_subscription_item():
    price = SimpleNamespace(id="price_2", product="prod_2")
    obj = SimpleNamespace(
        id="si_1",
        subscription=None,
        price=price,
        quantity=1,
        created=1700000000,
        metadata=None,
    )
    row = mappers.map_subscription_item(obj, None, _now(), False, subscription_id="sub_1")
    assert row["subscription_id"] == "sub_1"
    assert row["price_id"] == "price_2"
    assert "raw_payload" not in row


def test_map_dispute():
    ch = SimpleNamespace(id="ch_1")
    ed = SimpleNamespace(due_by=1700100000)
    obj = SimpleNamespace(
        id="dp_1",
        charge=ch,
        payment_intent=None,
        amount=2000,
        currency="gbp",
        status="needs_response",
        reason="fraudulent",
        created=1700000000,
        evidence_details=ed,
        is_charge_refundable=True,
        metadata={},
    )
    row = mappers.map_dispute(obj, None, _now(), False)
    assert row["charge_id"] == "ch_1"
    assert row["amount"] == 2000
    assert row["currency"] == "gbp"
    assert row["evidence_due_by"] is not None


def test_map_dispute_missing_amount_raises():
    ch = SimpleNamespace(id="ch_1")
    obj = SimpleNamespace(
        id="dp_y",
        charge=ch,
        amount=None,
        currency="usd",
        created=1700000000,
        evidence_details=None,
        metadata={},
    )
    with pytest.raises(ValueError, match="amount"):
        mappers.map_dispute(obj, None, _now(), False)


def test_map_dispute_missing_charge_raises():
    obj = SimpleNamespace(
        id="dp_x",
        charge=None,
        amount=1,
        currency="usd",
        created=1700000000,
        evidence_details=None,
        metadata={},
    )
    with pytest.raises(ValueError, match="charge"):
        mappers.map_dispute(obj, None, _now(), False)


def test_map_promotion_code():
    cpn = SimpleNamespace(id="coupon_1")
    r = SimpleNamespace(
        minimum_amount=1000,
        minimum_amount_currency="usd",
        first_time_transaction=True,
    )
    obj = SimpleNamespace(
        id="promo_1",
        code="SAVE10",
        coupon=cpn,
        customer=None,
        active=True,
        created=1700000000,
        expires_at=None,
        max_redemptions=100,
        times_redeemed=3,
        restrictions=r,
        metadata={},
    )
    row = mappers.map_promotion_code(obj, None, _now(), False)
    assert row["coupon_id"] == "coupon_1"
    assert row["code"] == "SAVE10"
    assert row["restrictions_minimum_amount"] == 1000


def test_map_credit_note():
    inv = SimpleNamespace(id="in_z")
    obj = SimpleNamespace(
        id="cn_1",
        invoice=inv,
        customer="cus_z",
        amount=300,
        currency="usd",
        status="issued",
        type="post_payment",
        reason="duplicate",
        memo="m",
        out_of_band_amount=0,
        refund=None,
        created=1700000000,
        metadata={},
    )
    row = mappers.map_credit_note(obj, None, _now(), False)
    assert row["invoice_id"] == "in_z"
    assert row["customer_id"] == "cus_z"
    assert row["amount"] == 300


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
