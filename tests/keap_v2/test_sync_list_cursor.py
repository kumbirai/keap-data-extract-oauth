"""Tests for Keap v2 cursor list sync (mocked HTTP)."""
from unittest.mock import MagicMock, patch

from src.keap_v2 import mappers
from src.keap_v2.client import KeapV2Client
from src.keap_v2.constants import KEAP_V2_COMPANIES
from src.keap_v2.orchestrator import sync_list_cursor
from src.keap_v2.settings import KeapV2ExtractSettings
from src.models.keap_v2_models import KeapV2Company


@patch("src.keap_v2.orchestrator.upsert_simple_rows")
def test_sync_list_cursor_pages_until_empty_token(mock_upsert):
    session = MagicMock()
    cm = MagicMock()
    cm.get_api_page_token.return_value = None
    cm.get_checkpoint.return_value = 0

    pages = [
        {"companies": [{"id": "1", "company_name": "A"}], "next_page_token": "t2"},
        {"companies": [{"id": "2", "company_name": "B"}], "next_page_token": None},
    ]
    it = iter(pages)

    client = MagicMock(spec=KeapV2Client)
    client.get = MagicMock(side_effect=lambda path, params: next(it))

    settings = KeapV2ExtractSettings(
        enabled=True,
        crm_base_url="https://example.com/crm",
        page_size=100,
        fan_out_delay_seconds=0.0,
    )

    result = sync_list_cursor(
        session,
        cm,
        client,
        settings,
        KEAP_V2_COMPANIES,
        "companies",
        ("companies",),
        KeapV2Company,
        mappers.map_company,
    )

    assert result.total_records == 2
    assert result.success_count == 2
    assert client.get.call_count == 2
    assert mock_upsert.call_count == 2
    assert cm.save_checkpoint.call_count >= 2
