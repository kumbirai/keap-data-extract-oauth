"""Tests for Keap v2 JSON mappers."""
from datetime import datetime, timezone

from src.keap_v2 import mappers


def test_extract_list_items_prefers_first_matching_key():
    data = {"next_page_token": "x", "companies": [{"id": "1"}], "noise": []}
    assert len(mappers.extract_list_items(data, "companies", "orders")) == 1
    assert mappers.extract_list_items(data, "missing", "nope") == []


def test_map_company_roundtrip_id():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    row = mappers.map_company(
        {
            "id": "42",
            "company_name": "Acme",
            "create_time": "2025-01-01T00:00:00Z",
        },
        now,
    )
    assert row is not None
    assert row["id"] == "42"
    assert row["company_name"] == "Acme"
    assert row["create_time"] is not None


def test_map_contact_link_resolves_camel_case():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    row = mappers.map_contact_link(
        10,
        {"linkedContactId": 20, "linkTypeId": "3"},
        now,
    )
    assert row is not None
    assert row["contact_id"] == 10
    assert row["linked_contact_id"] == 20
    assert row["link_type_id"] == "3"


def test_map_product_discount_boolean_string():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    row = mappers.map_product_discount(
        {
            "id": "d1",
            "name": "P",
            "discount_value": "10.5",
            "apply_to_commissions": "true",
        },
        now,
    )
    assert row is not None
    assert row["discount_value"] == 10.5
    assert row["apply_to_commissions"] is True
