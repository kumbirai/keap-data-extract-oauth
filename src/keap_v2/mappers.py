"""Map Keap v2 JSON objects to row dicts for warehouse tables."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dateutil import parser as date_parser


def parse_datetime(val: Any) -> Optional[datetime]:
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val
    try:
        return date_parser.isoparse(str(val))
    except (ValueError, TypeError):
        return None


def str_id(val: Any) -> Optional[str]:
    if val is None:
        return None
    return str(val).strip() or None


def coerce_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def map_company(obj: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    oid = str_id(obj.get("id"))
    if not oid:
        return None
    return {
        "id": oid,
        "company_name": obj.get("company_name"),
        "notes": obj.get("notes"),
        "website": obj.get("website"),
        "create_time": parse_datetime(obj.get("create_time")),
        "update_time": parse_datetime(obj.get("update_time")),
        "custom_fields": obj.get("custom_fields"),
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def map_contact_link_type(obj: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    oid = str_id(obj.get("id"))
    if not oid:
        return None
    return {
        "id": oid,
        "name": obj.get("name"),
        "description": obj.get("description"),
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def map_contact_link(
    anchor_contact_id: int,
    obj: Dict[str, Any],
    now: datetime,
) -> Optional[Dict[str, Any]]:
    linked = coerce_int(
        obj.get("linked_contact_id")
        or obj.get("linkedContactId")
        or obj.get("contact_id")
        or obj.get("contactId")
        or obj.get("id")
    )
    lt = str_id(
        obj.get("link_type_id")
        or obj.get("linkTypeId")
        or obj.get("type_id")
        or obj.get("link_type")
    )
    if linked is None or not lt:
        return None
    return {
        "contact_id": anchor_contact_id,
        "linked_contact_id": linked,
        "link_type_id": lt,
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def map_automation_category(obj: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    oid = str_id(obj.get("id"))
    if not oid:
        return None
    return {
        "id": oid,
        "name": obj.get("name"),
        "description": obj.get("description"),
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def map_automation(obj: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    oid = str_id(obj.get("id"))
    if not oid:
        return None
    locked = obj.get("locked")
    if isinstance(locked, str):
        locked = locked.lower() in ("true", "1", "yes")
    return {
        "id": oid,
        "title": obj.get("title"),
        "status": str_id(obj.get("status")),
        "locked": locked,
        "active_contacts": coerce_int(obj.get("active_contacts")),
        "error_message": obj.get("error_message"),
        "published_date": parse_datetime(obj.get("published_date")),
        "published_by": str_id(obj.get("published_by")),
        "published_timezone": obj.get("published_timezone"),
        "categories": obj.get("categories"),
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def map_category_discount(obj: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    oid = str_id(obj.get("id"))
    if not oid:
        return None
    return {
        "id": oid,
        "name": obj.get("name"),
        "description": obj.get("description"),
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def map_product_discount(obj: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    oid = str_id(obj.get("id"))
    if not oid:
        return None
    apply_c = obj.get("apply_to_commissions")
    if isinstance(apply_c, str):
        apply_c = apply_c.lower() in ("true", "1", "yes")
    dv = obj.get("discount_value")
    try:
        discount_value = float(dv) if dv is not None else None
    except (TypeError, ValueError):
        discount_value = None
    return {
        "id": oid,
        "name": obj.get("name"),
        "description": obj.get("description"),
        "product_id": str_id(obj.get("product_id")),
        "discount_type": str_id(obj.get("discount_type")),
        "discount_value": discount_value,
        "apply_to_commissions": apply_c,
        "criteria": obj.get("criteria"),
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def map_generic_discount_row(obj: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    oid = str_id(obj.get("id"))
    if not oid:
        return None
    return {
        "id": oid,
        "name": obj.get("name"),
        "description": obj.get("description"),
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def map_campaign_goal(campaign_id: int, obj: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    gid = str_id(obj.get("id") or obj.get("goal_id"))
    if not gid:
        return None
    return {
        "campaign_id": campaign_id,
        "goal_id": gid,
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def map_campaign_sequence_v2(campaign_id: int, obj: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    sid = str_id(obj.get("id") or obj.get("sequence_id"))
    if not sid:
        return None
    return {
        "campaign_id": campaign_id,
        "sequence_id": sid,
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def map_affiliate_referral(affiliate_id: int, obj: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    oid = str_id(obj.get("id"))
    if not oid:
        return None
    return {
        "id": oid,
        "affiliate_id": affiliate_id,
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def map_contact_lead_score(contact_id: int, obj: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    return {
        "contact_id": contact_id,
        "score_payload": obj if isinstance(obj, dict) else None,
        "raw_payload": obj if isinstance(obj, dict) else {"value": obj},
        "loaded_at": now,
        "updated_at": now,
    }


def map_lead_source_category(obj: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    oid = str_id(obj.get("id"))
    if not oid:
        return None
    return {
        "id": oid,
        "name": obj.get("name"),
        "description": obj.get("description"),
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def map_lead_source(obj: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    oid = str_id(obj.get("id"))
    if not oid:
        return None
    return {
        "id": oid,
        "name": obj.get("name"),
        "description": obj.get("description"),
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def map_lead_source_expense(lead_source_id: str, obj: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    eid = str_id(obj.get("id") or obj.get("expense_id"))
    if not eid:
        return None
    return {
        "lead_source_id": lead_source_id,
        "expense_id": eid,
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def map_lead_source_recurring_expense(
    lead_source_id: str,
    obj: Dict[str, Any],
    now: datetime,
) -> Optional[Dict[str, Any]]:
    rid = str_id(obj.get("id") or obj.get("recurring_expense_id"))
    if not rid:
        return None
    return {
        "lead_source_id": lead_source_id,
        "recurring_expense_id": rid,
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def map_lead_source_recurring_incurred(
    lead_source_id: str,
    recurring_expense_id: str,
    obj: Dict[str, Any],
    now: datetime,
) -> Optional[Dict[str, Any]]:
    iid = str_id(obj.get("id") or obj.get("expense_id"))
    if not iid:
        return None
    return {
        "lead_source_id": lead_source_id,
        "recurring_expense_id": recurring_expense_id,
        "incurred_id": iid,
        "raw_payload": obj,
        "loaded_at": now,
        "updated_at": now,
    }


def extract_list_items(data: Dict[str, Any], *keys: str) -> List[Any]:
    for key in keys:
        val = data.get(key)
        if isinstance(val, list):
            return val
    return []
