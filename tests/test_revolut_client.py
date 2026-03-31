"""Tests for Revolut HTTP client retry behaviour (mocked requests)."""
from unittest.mock import MagicMock, patch

import pytest

from src.revolut.client import RevolutApiError, RevolutClient
from src.revolut.settings import RevolutExtractSettings


def _settings(tmp_path):
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )
    p = tmp_path / "k.pem"
    p.write_bytes(pem)
    return RevolutExtractSettings(
        client_id="c",
        issuer="c",
        jwt_audience="https://revolut.com",
        jwt_kid="k",
        private_key_path=str(p),
        private_key_passphrase=None,
        refresh_token="rt",
        authorization_code=None,
        use_sandbox=True,
        transaction_lookback_days=7,
        initial_history_days=30,
        list_count=100,
        store_raw_payload=False,
        account_allowlist=None,
    )


@patch("src.revolut.client.time.sleep", lambda s: None)
@patch("src.revolut.client.requests.post")
@patch("src.revolut.client.requests.request")
def test_list_accounts_retries_429_then_success(mock_request, mock_post, tmp_path):
    settings = _settings(tmp_path)
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"access_token": "tok", "expires_in": 2400},
    )
    ok = MagicMock(status_code=200, content=b'[{"id":"a1"}]', json=lambda: [{"id": "a1"}])
    fail429 = MagicMock(status_code=429, text="rate")
    mock_request.side_effect = [fail429, ok]

    client = RevolutClient(settings)
    out = client.list_accounts()
    assert out == [{"id": "a1"}]
    assert mock_request.call_count == 2


@patch("src.revolut.client.time.sleep", lambda s: None)
@patch("src.revolut.client.requests.post")
@patch("src.revolut.client.requests.request")
def test_request_raises_after_backoff_exhausted(mock_request, mock_post, tmp_path):
    settings = _settings(tmp_path)
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"access_token": "tok", "expires_in": 2400},
    )
    mock_request.return_value = MagicMock(status_code=500, text="err")

    client = RevolutClient(settings)
    with pytest.raises(RevolutApiError):
        client.list_accounts()
