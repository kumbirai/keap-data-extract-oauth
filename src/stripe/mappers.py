"""Map Stripe API objects to database row dicts (column name -> value)."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.stripe.serialize import stripe_object_to_dict


def _stripe_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value if value else None
    return getattr(value, "id", None)


def _unix_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _currency_code(obj: Any) -> Optional[str]:
    c = getattr(obj, "currency", None)
    if c is None:
        return None
    if isinstance(c, str):
        s = c.strip().lower()
        return s if s else None
    return str(c).strip().lower() or None


def _require_currency(obj: Any) -> str:
    c = _currency_code(obj)
    if not c:
        raise ValueError("Stripe object is missing required currency")
    return c


def _metadata(obj: Any) -> Optional[dict]:
    m = getattr(obj, "metadata", None)
    if not m:
        return None
    try:
        return dict(m)
    except (TypeError, ValueError):
        return None


def _base_row(
    obj: Any,
    stripe_account_id: Optional[str],
    now: datetime,
    store_raw: bool,
) -> Dict[str, Any]:
    return {
        "stripe_account_id": stripe_account_id or None,
        "loaded_at": now,
        "updated_at": now,
        "metadata": _metadata(obj),
        "raw_payload": stripe_object_to_dict(obj) if store_raw else None,
    }


def map_product(obj: Any, stripe_account_id: Optional[str], now: datetime, store_raw: bool) -> Dict[str, Any]:
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update(
        {
            "id": obj.id,
            "name": getattr(obj, "name", None) or None,
            "description": getattr(obj, "description", None) or None,
            "active": bool(getattr(obj, "active", True)),
            "default_price_id": _stripe_id(getattr(obj, "default_price", None)),
            "created": _unix_ts(getattr(obj, "created", None)),
        }
    )
    return row


def map_price(obj: Any, stripe_account_id: Optional[str], now: datetime, store_raw: bool) -> Dict[str, Any]:
    rec = getattr(obj, "recurring", None)
    interval = getattr(rec, "interval", None) if rec else None
    interval_count = getattr(rec, "interval_count", None) if rec else None
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update(
        {
            "id": obj.id,
            "product_id": _stripe_id(getattr(obj, "product", None)),
            "currency": _require_currency(obj),
            "unit_amount": getattr(obj, "unit_amount", None),
            "type": getattr(obj, "type", None) or None,
            "recurring_interval": interval,
            "recurring_interval_count": interval_count,
            "active": bool(getattr(obj, "active", True)),
        }
    )
    return row


def map_coupon(obj: Any, stripe_account_id: Optional[str], now: datetime, store_raw: bool) -> Dict[str, Any]:
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update(
        {
            "id": obj.id,
            "name": getattr(obj, "name", None) or None,
            "percent_off": getattr(obj, "percent_off", None),
            "amount_off": getattr(obj, "amount_off", None),
            "currency": _currency_code(obj),
            "duration": getattr(obj, "duration", None) or None,
            "duration_in_months": getattr(obj, "duration_in_months", None),
            "valid": getattr(obj, "valid", None),
            "times_redeemed": getattr(obj, "times_redeemed", None),
            "max_redemptions": getattr(obj, "max_redemptions", None),
            "created": _unix_ts(getattr(obj, "created", None)),
        }
    )
    return row


def map_subscription(obj: Any, stripe_account_id: Optional[str], now: datetime, store_raw: bool) -> Dict[str, Any]:
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update(
        {
            "id": obj.id,
            "customer_id": _stripe_id(getattr(obj, "customer", None)),
            "status": getattr(obj, "status", None) or None,
            "current_period_start": _unix_ts(getattr(obj, "current_period_start", None)),
            "current_period_end": _unix_ts(getattr(obj, "current_period_end", None)),
            "cancel_at_period_end": getattr(obj, "cancel_at_period_end", None),
            "canceled_at": _unix_ts(getattr(obj, "canceled_at", None)),
            "created": _unix_ts(getattr(obj, "created", None)),
            "default_payment_method": _stripe_id(getattr(obj, "default_payment_method", None)),
        }
    )
    return row


def map_invoice(obj: Any, stripe_account_id: Optional[str], now: datetime, store_raw: bool) -> Dict[str, Any]:
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update(
        {
            "id": obj.id,
            "customer_id": _stripe_id(getattr(obj, "customer", None)),
            "subscription_id": _stripe_id(getattr(obj, "subscription", None)),
            "status": getattr(obj, "status", None) or None,
            "currency": _require_currency(obj),
            "amount_due": getattr(obj, "amount_due", None),
            "amount_paid": getattr(obj, "amount_paid", None),
            "total": getattr(obj, "total", None),
            "created": _unix_ts(getattr(obj, "created", None)),
            "period_start": _unix_ts(getattr(obj, "period_start", None)),
            "period_end": _unix_ts(getattr(obj, "period_end", None)),
            "charge_id": _stripe_id(getattr(obj, "charge", None)),
            "payment_intent_id": _stripe_id(getattr(obj, "payment_intent", None)),
        }
    )
    return row


def map_payment_intent(obj: Any, stripe_account_id: Optional[str], now: datetime, store_raw: bool) -> Dict[str, Any]:
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update(
        {
            "id": obj.id,
            "amount": getattr(obj, "amount", None),
            "amount_received": getattr(obj, "amount_received", None),
            "currency": _require_currency(obj),
            "created": _unix_ts(getattr(obj, "created", None)),
            "customer_id": _stripe_id(getattr(obj, "customer", None)),
            "invoice_id": _stripe_id(getattr(obj, "invoice", None)),
            "status": getattr(obj, "status", None) or None,
            "latest_charge_id": _stripe_id(getattr(obj, "latest_charge", None)),
        }
    )
    return row


def map_charge(obj: Any, stripe_account_id: Optional[str], now: datetime, store_raw: bool) -> Dict[str, Any]:
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update(
        {
            "id": obj.id,
            "amount": getattr(obj, "amount", None),
            "amount_refunded": getattr(obj, "amount_refunded", None),
            "currency": _require_currency(obj),
            "created": _unix_ts(getattr(obj, "created", None)),
            "customer_id": _stripe_id(getattr(obj, "customer", None)),
            "invoice_id": _stripe_id(getattr(obj, "invoice", None)),
            "payment_intent_id": _stripe_id(getattr(obj, "payment_intent", None)),
            "balance_transaction_id": _stripe_id(getattr(obj, "balance_transaction", None)),
            "description": getattr(obj, "description", None) or None,
            "receipt_email": getattr(obj, "receipt_email", None) or None,
            "paid": getattr(obj, "paid", None),
            "refunded": getattr(obj, "refunded", None),
            "status": getattr(obj, "status", None) or None,
            "failure_code": getattr(obj, "failure_code", None) or None,
            "failure_message": getattr(obj, "failure_message", None) or None,
            "livemode": getattr(obj, "livemode", None),
        }
    )
    return row


def map_refund(obj: Any, stripe_account_id: Optional[str], now: datetime, store_raw: bool) -> Dict[str, Any]:
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update(
        {
            "id": obj.id,
            "charge_id": _stripe_id(getattr(obj, "charge", None)),
            "payment_intent_id": _stripe_id(getattr(obj, "payment_intent", None)),
            "amount": getattr(obj, "amount", None),
            "currency": _require_currency(obj),
            "created": _unix_ts(getattr(obj, "created", None)),
            "status": getattr(obj, "status", None) or None,
            "balance_transaction_id": _stripe_id(getattr(obj, "balance_transaction", None)),
        }
    )
    return row


def map_balance_transaction(obj: Any, stripe_account_id: Optional[str], now: datetime, store_raw: bool) -> Dict[str, Any]:
    src = getattr(obj, "source", None)
    if isinstance(src, str):
        source_id = src or None
        source_type = None
    elif src is not None:
        source_id = _stripe_id(src)
        source_type = getattr(src, "object", None) or None
    else:
        source_id = None
        source_type = None
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update(
        {
            "id": obj.id,
            "amount": getattr(obj, "amount", None),
            "fee": getattr(obj, "fee", None),
            "net": getattr(obj, "net", None),
            "currency": _require_currency(obj),
            "type": getattr(obj, "type", None) or None,
            "created": _unix_ts(getattr(obj, "created", None)),
            "available_on": _unix_ts(getattr(obj, "available_on", None)),
            "source_id": source_id,
            "source_type": source_type,
            "reporting_category": getattr(obj, "reporting_category", None) or None,
        }
    )
    return row


def map_payout(obj: Any, stripe_account_id: Optional[str], now: datetime, store_raw: bool) -> Dict[str, Any]:
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update(
        {
            "id": obj.id,
            "amount": getattr(obj, "amount", None),
            "currency": _require_currency(obj),
            "status": getattr(obj, "status", None) or None,
            "arrival_date": _unix_ts(getattr(obj, "arrival_date", None)),
            "created": _unix_ts(getattr(obj, "created", None)),
            "description": getattr(obj, "description", None) or None,
            "destination": _stripe_id(getattr(obj, "destination", None)),
            "balance_transaction_id": _stripe_id(getattr(obj, "balance_transaction", None)),
        }
    )
    return row


def _child_base_row(
    obj: Any,
    stripe_account_id: Optional[str],
    now: datetime,
    store_raw: bool,
) -> Dict[str, Any]:
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.pop("raw_payload", None)
    return row


def map_customer(obj: Any, stripe_account_id: Optional[str], now: datetime, store_raw: bool) -> Dict[str, Any]:
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update(
        {
            "id": obj.id,
            "email": (getattr(obj, "email", None) or None),
            "name": (getattr(obj, "name", None) or None),
            "phone": (getattr(obj, "phone", None) or None),
            "description": (getattr(obj, "description", None) or None),
            "currency": _currency_code(obj),
            "balance": getattr(obj, "balance", None),
            "delinquent": getattr(obj, "delinquent", None),
            "created": _unix_ts(getattr(obj, "created", None)),
            "default_source": _stripe_id(getattr(obj, "default_source", None)),
            "invoice_prefix": (getattr(obj, "invoice_prefix", None) or None),
            "tax_exempt": getattr(obj, "tax_exempt", None) or None,
        }
    )
    return row


def map_invoice_line_item(
    obj: Any,
    stripe_account_id: Optional[str],
    now: datetime,
    store_raw: bool,
    *,
    invoice_id: Optional[str] = None,
) -> Dict[str, Any]:
    row = _child_base_row(obj, stripe_account_id, now, store_raw)
    period = getattr(obj, "period", None)
    amt = getattr(obj, "amount", None)
    if amt is None:
        raise ValueError("invoice line item missing amount")
    row.update(
        {
            "id": obj.id,
            "invoice_id": invoice_id or _stripe_id(getattr(obj, "invoice", None)) or "",
            "subscription_id": _stripe_id(getattr(obj, "subscription", None)),
            "subscription_item_id": _stripe_id(getattr(obj, "subscription_item", None)),
            "price_id": _stripe_id(getattr(obj, "price", None)),
            "product_id": _stripe_id(getattr(getattr(obj, "price", None), "product", None)),
            "quantity": getattr(obj, "quantity", None),
            "amount": int(amt),
            "currency": _require_currency(obj),
            "description": (getattr(obj, "description", None) or None),
            "period_start": _unix_ts(getattr(period, "start", None)) if period else None,
            "period_end": _unix_ts(getattr(period, "end", None)) if period else None,
            "type": getattr(obj, "type", None) or None,
            "proration": getattr(obj, "proration", None),
        }
    )
    if not row["invoice_id"]:
        raise ValueError("invoice line item missing invoice_id")
    return row


def map_subscription_item(
    obj: Any,
    stripe_account_id: Optional[str],
    now: datetime,
    store_raw: bool,
    *,
    subscription_id: Optional[str] = None,
) -> Dict[str, Any]:
    row = _child_base_row(obj, stripe_account_id, now, store_raw)
    sid = subscription_id or _stripe_id(getattr(obj, "subscription", None)) or ""
    row.update(
        {
            "id": obj.id,
            "subscription_id": sid,
            "price_id": _stripe_id(getattr(obj, "price", None)),
            "product_id": _stripe_id(getattr(getattr(obj, "price", None), "product", None)),
            "quantity": getattr(obj, "quantity", None),
            "created": _unix_ts(getattr(obj, "created", None)),
        }
    )
    if not row["subscription_id"]:
        raise ValueError("subscription item missing subscription_id")
    return row


def map_dispute(obj: Any, stripe_account_id: Optional[str], now: datetime, store_raw: bool) -> Dict[str, Any]:
    ch = _stripe_id(getattr(obj, "charge", None))
    if not ch:
        raise ValueError("dispute missing charge_id")
    ed = getattr(obj, "evidence_details", None)
    amt = getattr(obj, "amount", None)
    if amt is None:
        raise ValueError("dispute missing amount")
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update(
        {
            "id": obj.id,
            "charge_id": ch,
            "payment_intent_id": _stripe_id(getattr(obj, "payment_intent", None)),
            "amount": int(amt),
            "currency": _require_currency(obj),
            "status": getattr(obj, "status", None) or None,
            "reason": getattr(obj, "reason", None) or None,
            "created": _unix_ts(getattr(obj, "created", None)),
            "evidence_due_by": _unix_ts(getattr(ed, "due_by", None)) if ed else None,
            "is_charge_refundable": getattr(obj, "is_charge_refundable", None),
        }
    )
    return row


def map_promotion_code(obj: Any, stripe_account_id: Optional[str], now: datetime, store_raw: bool) -> Dict[str, Any]:
    cpn = _stripe_id(getattr(obj, "coupon", None))
    if not cpn:
        raise ValueError("promotion code missing coupon_id")
    r = getattr(obj, "restrictions", None)
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update(
        {
            "id": obj.id,
            "code": (getattr(obj, "code", None) or None),
            "coupon_id": cpn,
            "customer_id": _stripe_id(getattr(obj, "customer", None)),
            "active": getattr(obj, "active", None),
            "created": _unix_ts(getattr(obj, "created", None)),
            "expires_at": _unix_ts(getattr(obj, "expires_at", None)),
            "max_redemptions": getattr(obj, "max_redemptions", None),
            "times_redeemed": getattr(obj, "times_redeemed", None),
            "restrictions_minimum_amount": getattr(r, "minimum_amount", None) if r else None,
            "restrictions_minimum_amount_currency": getattr(r, "minimum_amount_currency", None) if r else None,
            "restrictions_first_time_transaction": getattr(r, "first_time_transaction", None) if r else None,
        }
    )
    return row


def map_credit_note(obj: Any, stripe_account_id: Optional[str], now: datetime, store_raw: bool) -> Dict[str, Any]:
    inv = _stripe_id(getattr(obj, "invoice", None))
    if not inv:
        raise ValueError("credit note missing invoice_id")
    row = _base_row(obj, stripe_account_id, now, store_raw)
    amt = getattr(obj, "amount", None)
    if amt is None:
        raise ValueError("credit note missing amount")
    row.update(
        {
            "id": obj.id,
            "invoice_id": inv,
            "customer_id": _stripe_id(getattr(obj, "customer", None)),
            "amount": int(amt),
            "currency": _require_currency(obj),
            "status": getattr(obj, "status", None) or None,
            "type": getattr(obj, "type", None) or None,
            "reason": getattr(obj, "reason", None) or None,
            "memo": (getattr(obj, "memo", None) or None),
            "out_of_band_amount": getattr(obj, "out_of_band_amount", None),
            "refund_id": _stripe_id(getattr(obj, "refund", None)),
            "created": _unix_ts(getattr(obj, "created", None)),
        }
    )
    return row


def map_transfer(obj: Any, stripe_account_id: Optional[str], now: datetime, store_raw: bool) -> Dict[str, Any]:
    api_status = getattr(obj, "status", None)
    if isinstance(api_status, str) and api_status.strip():
        status_val = api_status.strip()
    else:
        reversed_ = getattr(obj, "reversed", None)
        if reversed_ is True:
            status_val = "reversed"
        elif reversed_ is False:
            status_val = "posted"
        else:
            status_val = None
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update(
        {
            "id": obj.id,
            "amount": getattr(obj, "amount", None),
            "currency": _require_currency(obj),
            "created": _unix_ts(getattr(obj, "created", None)),
            "destination": _stripe_id(getattr(obj, "destination", None)),
            "status": status_val,
            "description": getattr(obj, "description", None) or None,
        }
    )
    return row
