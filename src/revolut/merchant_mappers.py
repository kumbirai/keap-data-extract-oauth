"""Map Revolut Merchant API JSON objects to database row dicts."""
import copy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

from dateutil import parser as date_parser


def _parse_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = date_parser.isoparse(str(value).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def _minor_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    if isinstance(value, str):
        try:
            return int(Decimal(value.strip()))
        except (InvalidOperation, ValueError):
            return None
    if isinstance(value, dict):
        inner = value.get("value") or value.get("amount")
        return _minor_int(inner)
    return None


def _str(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _currency(value: Any) -> Optional[str]:
    s = _str(value)
    return s.upper()[:3] if s else None


def _int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    s = str(value).lower().strip()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return None


def _metadata(value: Any) -> Optional[dict]:
    if isinstance(value, dict):
        return value
    return None


def map_order(payload: Dict[str, Any], now: datetime, store_raw: bool) -> Dict[str, Any]:
    oid = payload.get("id")
    if not oid:
        raise ValueError("Revolut Merchant order missing id")
    raw = copy.deepcopy(payload) if store_raw else None
    customer = payload.get("customer") or {}
    if isinstance(customer, str):
        customer_id = customer
    else:
        customer_id = _str(customer.get("id") if isinstance(customer, dict) else None)
    return {
        "id": str(oid),
        "token": _str(payload.get("token")),
        "type": _str(payload.get("type")),
        "state": _str(payload.get("state")),
        "created_at": _parse_ts(payload.get("created_at")),
        "updated_at": _parse_ts(payload.get("updated_at")),
        "completed_at": _parse_ts(payload.get("completed_at")),
        "amount": _minor_int(payload.get("order_amount") or payload.get("amount")),
        "currency": _currency(payload.get("currency")),
        "outstanding_amount": _minor_int(payload.get("outstanding_amount")),
        "capture_mode": _str(payload.get("capture_mode")),
        "cancel_authorised_only": _bool(payload.get("cancel_authorised_only")),
        "customer_id": customer_id,
        "email": _str(payload.get("email")),
        "description": _str(payload.get("description")),
        "merchant_order_ext_ref": _str(
            payload.get("merchant_order_ext_ref") or payload.get("merchant_order_reference")
        ),
        "metadata_col": _metadata(payload.get("metadata")),
        "raw_payload": raw,
        "loaded_at": now,
        "updated_at_etl": now,
    }


def map_customer(payload: Dict[str, Any], now: datetime, store_raw: bool) -> Dict[str, Any]:
    cid = payload.get("id")
    if not cid:
        raise ValueError("Revolut Merchant customer missing id")
    raw = copy.deepcopy(payload) if store_raw else None
    return {
        "id": str(cid),
        "email": _str(payload.get("email")),
        "phone": _str(payload.get("phone")),
        "full_name": _str(payload.get("full_name") or payload.get("name")),
        "business_name": _str(payload.get("business_name")),
        "created_at": _parse_ts(payload.get("created_at")),
        "updated_at": _parse_ts(payload.get("updated_at")),
        "raw_payload": raw,
        "loaded_at": now,
        "updated_at_etl": now,
    }


def map_payment_method(
    payload: Dict[str, Any], customer_id: str, now: datetime, store_raw: bool
) -> Dict[str, Any]:
    pmid = payload.get("id")
    if not pmid:
        raise ValueError("Revolut Merchant payment method missing id")
    raw = copy.deepcopy(payload) if store_raw else None
    card = payload.get("card") or {}
    billing = (card.get("billing_address") if isinstance(card, dict) else None) or {}
    return {
        "id": str(pmid),
        "customer_id": str(customer_id),
        "type": _str(payload.get("type")),
        "card_bin": _str(card.get("bin") if isinstance(card, dict) else None),
        "card_last_four": _str(card.get("last_four") if isinstance(card, dict) else None),
        "card_expiry_month": _int(card.get("expiry_month") if isinstance(card, dict) else None),
        "card_expiry_year": _int(card.get("expiry_year") if isinstance(card, dict) else None),
        "card_cardholder_name": _str(card.get("cardholder_name") if isinstance(card, dict) else None),
        "card_brand": _str(card.get("brand") if isinstance(card, dict) else None),
        "card_funding_type": _str(card.get("funding_type") if isinstance(card, dict) else None),
        "card_issuer": _str(card.get("issuer") if isinstance(card, dict) else None),
        "billing_street_line_1": _str(billing.get("street_line_1")),
        "billing_city": _str(billing.get("city")),
        "billing_postcode": _str(billing.get("postcode")),
        "billing_country": _str(billing.get("country")),
        "raw_payload": raw,
        "loaded_at": now,
        "updated_at_etl": now,
    }


def map_order_payment(
    payload: Dict[str, Any], order_id: str, now: datetime, store_raw: bool
) -> Dict[str, Any]:
    pid = payload.get("id")
    if not pid:
        raise ValueError("Revolut Merchant order payment missing id")
    raw = copy.deepcopy(payload) if store_raw else None
    pm = payload.get("payment_method") or {}
    card = (pm.get("card") if isinstance(pm, dict) else None) or {}
    return {
        "id": str(pid),
        "order_id": str(order_id),
        "state": _str(payload.get("state")),
        "amount": _minor_int(payload.get("amount")),
        "currency": _currency(payload.get("currency")),
        "payment_method_type": _str(pm.get("type") if isinstance(pm, dict) else None),
        "card_bin": _str(card.get("bin") if isinstance(card, dict) else None),
        "card_last_four": _str(card.get("last_four") if isinstance(card, dict) else None),
        "card_brand": _str(card.get("brand") if isinstance(card, dict) else None),
        "card_funding_type": _str(card.get("funding_type") if isinstance(card, dict) else None),
        "card_country": _str(card.get("country") if isinstance(card, dict) else None),
        "arn": _str(pm.get("arn") if isinstance(pm, dict) else payload.get("arn")),
        "bank_message": _str(payload.get("bank_message")),
        "decline_reason": _str(payload.get("decline_reason") or payload.get("reason")),
        "created_at": _parse_ts(payload.get("created_at")),
        "raw_payload": raw,
        "loaded_at": now,
        "updated_at_etl": now,
    }


def map_dispute(payload: Dict[str, Any], now: datetime, store_raw: bool) -> Dict[str, Any]:
    did = payload.get("id")
    if not did:
        raise ValueError("Revolut Merchant dispute missing id")
    raw = copy.deepcopy(payload) if store_raw else None
    order_id = _str(payload.get("order_id") or payload.get("order", {}).get("id") if isinstance(payload.get("order"), dict) else payload.get("order_id"))
    return {
        "id": str(did),
        "order_id": order_id,
        "state": _str(payload.get("state")),
        "reason": _str(payload.get("reason")),
        "amount": _minor_int(payload.get("amount")),
        "currency": _currency(payload.get("currency")),
        "created_at": _parse_ts(payload.get("created_at")),
        "updated_at": _parse_ts(payload.get("updated_at")),
        "due_at": _parse_ts(payload.get("due_at") or payload.get("due_by")),
        "raw_payload": raw,
        "loaded_at": now,
        "updated_at_etl": now,
    }


def map_location(payload: Dict[str, Any], now: datetime, store_raw: bool) -> Dict[str, Any]:
    lid = payload.get("id")
    if not lid:
        raise ValueError("Revolut Merchant location missing id")
    raw = copy.deepcopy(payload) if store_raw else None
    address = payload.get("address") or {}
    return {
        "id": str(lid),
        "name": _str(payload.get("name")),
        "type": _str(payload.get("type")),
        "address_line_1": _str(address.get("line_1") or address.get("street_line_1") if isinstance(address, dict) else None),
        "address_city": _str(address.get("city") if isinstance(address, dict) else None),
        "address_country": _str(address.get("country") if isinstance(address, dict) else None),
        "currency": _currency(payload.get("currency")),
        "raw_payload": raw,
        "loaded_at": now,
        "updated_at_etl": now,
    }
