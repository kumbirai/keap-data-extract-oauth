"""Orchestrator behaviour when Revolut env is absent."""
from unittest.mock import MagicMock, patch

from src.revolut.orchestrator import run_revolut_entity, run_revolut_extract
from src.scripts.loaders.base_loader import LoadResult


@patch("src.revolut.orchestrator._settings_from_env", return_value=None)
def test_run_revolut_entity_skips_when_not_configured(_mock_settings):
    out = run_revolut_entity(MagicMock(), MagicMock(), "revolut_all", update=False)
    assert out == LoadResult(0, 0, 0)


@patch("src.revolut.orchestrator._settings_from_env", return_value=None)
def test_run_revolut_extract_skips_when_not_configured(_mock_settings):
    out = run_revolut_extract(MagicMock(), MagicMock(), update=False)
    assert out == LoadResult(0, 0, 0)
