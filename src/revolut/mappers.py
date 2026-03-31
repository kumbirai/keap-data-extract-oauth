"""Map Revolut Business API JSON objects to database row dicts."""
import copy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Tuple

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
            d = Decimal(value.strip())
            return int(d)
        except (InvalidOperation, ValueError):
            return None
    if isinstance(value, dict):
        inner = value.get("value") or value.get("Value") or value.get("amount")
        return _minor_int(inner)
    return None


def _currency_from_amount_obj(amount_obj: Any) -> Optional[str]:
    if isinstance(amount_obj, dict):
        c = amount_obj.get("currency") or amount_obj.get("Currency")
        if c:
            return str(c).upper()[:3]
    return None


def _extract_amount_currency(payload: Dict[str, Any]) -> Tuple[Optional[int], Optional[str]]:
    amt = payload.get("amount")
    cur = payload.get("currency")
    if isinstance(cur, str):
        cur = cur.upper()[:3]
    if isinstance(amt, dict):
        c2 = _currency_from_amount_obj(amt)
        return _minor_int(amt), (c2 or cur)
    return _minor_int(amt), cur


def _fee_fields(payload: Dict[str, Any]) -> Tuple[Optional[int], Optional[str]]:
    fee = payload.get("fee") or payload.get("fees")
    if isinstance(fee, dict):
        return _minor_int(fee.get("amount") or fee.get("value")), _currency_from_amount_obj(fee) or (
            str(fee.get("currency")).upper()[:3] if fee.get("currency") else None
        )
    return _minor_int(payload.get("fee_amount")), (
        str(payload.get("fee_currency")).upper()[:3] if payload.get("fee_currency") else None
    )


def _bill_fields(payload: Dict[str, Any]) -> Tuple[Optional[int], Optional[str]]:
    bill = payload.get("bill_amount") or payload.get("bill")
    if isinstance(bill, dict):
        return _minor_int(bill), _currency_from_amount_obj(bill)
    return _minor_int(bill), (
        str(payload.get("bill_currency")).upper()[:3] if payload.get("bill_currency") else None
    )


def _merchant_fields(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    m = payload.get("merchant")
    if not isinstance(m, dict):
        return None, None, None
    name = m.get("name")
    city = m.get("city")
    mcc = m.get("category_code") or m.get("mcc")
    return (
        str(name) if name is not None else None,
        str(city) if city is not None else None,
        str(mcc) if mcc is not None else None,
    )


def map_account(payload: Dict[str, Any], now: datetime, store_raw: bool) -> Dict[str, Any]:
    aid = payload.get("id")
    if not aid:
        raise ValueError("Revolut account missing id")
    bal = payload.get("balance")
    bal_minor: Optional[int]
    if isinstance(bal, int):
        bal_minor = bal
    elif isinstance(bal, float):
        bal_minor = int(round(Decimal(str(bal)) * 100))
    elif isinstance(bal, str):
        try:
            bal_minor = int(Decimal(bal.strip()) * 100)
        except (InvalidOperation, ValueError):
            bal_minor = None
    else:
        bal_minor = None
    raw = copy.deepcopy(payload) if store_raw else None
    return {
        "id": str(aid),
        "name": str(payload["name"]) if payload.get("name") is not None else None,
        "currency": str(payload["currency"]).upper()[:3] if payload.get("currency") else None,
        "state": str(payload["state"]) if payload.get("state") is not None else None,
        "balance": bal_minor,
        "balance_updated_at": _parse_ts(payload.get("updated_at") or payload.get("balance_updated_at")),
        "raw_payload": raw,
        "loaded_at": now,
        "updated_at": now,
    }


def map_transaction(
    payload: Dict[str, Any],
    *,
    default_account_id: Optional[str],
    now: datetime,
    store_raw: bool,
) -> Dict[str, Any]:
    tid = payload.get("id")
    if not tid:
        raise ValueError("Revolut transaction missing id")
    amount, currency = _extract_amount_currency(payload)
    fee_amount, fee_currency = _fee_fields(payload)
    bill_amount, bill_currency = _bill_fields(payload)
    m_name, m_city, m_mcc = _merchant_fields(payload)
    meta = payload.get("metadata")
    if meta is not None and not isinstance(meta, dict):
        meta = None
    raw = copy.deepcopy(payload) if store_raw else None
    account_id = payload.get("account_id") or payload.get("account") or default_account_id
    if account_id is not None:
        account_id = str(account_id)
    related = payload.get("related_transaction_id") or payload.get("parent_transaction_id")
    if related is not None:
        related = str(related)
    cp = payload.get("counterparty_id") or payload.get("counterparty")
    if isinstance(cp, dict):
        cp = cp.get("id")
    if cp is not None:
        cp = str(cp)
    desc = payload.get("description")
    if desc is not None:
        desc = str(desc)
    return {
        "id": str(tid),
        "account_id": account_id,
        "type": str(payload["type"]) if payload.get("type") is not None else None,
        "state": str(payload["state"]) if payload.get("state") is not None else None,
        "amount": amount,
        "currency": currency,
        "fee_amount": fee_amount,
        "fee_currency": fee_currency,
        "bill_amount": bill_amount,
        "bill_currency": bill_currency,
        "created_at": _parse_ts(payload.get("created_at")),
        "api_updated_at": _parse_ts(payload.get("updated_at")),
        "completed_at": _parse_ts(payload.get("completed_at")),
        "merchant_name": m_name,
        "merchant_city": m_city,
        "merchant_category_code": m_mcc,
        "description": desc,
        "counterparty_id": cp,
        "related_transaction_id": related,
        "metadata_col": meta,
        "raw_payload": raw,
        "loaded_at": now,
        "updated_at": now,
    }
