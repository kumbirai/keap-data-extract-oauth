"""Tests for Revolut client assertion JWT (local RSA key, no network)."""
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

from src.revolut.api_constants import JWT_ALGORITHM
from src.revolut.auth import build_client_assertion_jwt
from src.revolut.settings import RevolutExtractSettings


def _temp_key_path(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )
    p = tmp_path / "rev.pem"
    p.write_bytes(pem)
    return p, key


def test_build_client_assertion_jwt_claims(tmp_path):
    path, private_key = _temp_key_path(tmp_path)
    settings = RevolutExtractSettings(
        client_id="cid",
        issuer="cid",
        jwt_audience="https://revolut.com",
        jwt_kid="kid-1",
        private_key_path=str(path),
        private_key_passphrase=None,
        refresh_token="rt",
        authorization_code=None,
        access_token=None,
        use_sandbox=True,
        transaction_lookback_days=7,
        initial_history_days=30,
        list_count=100,
        store_raw_payload=False,
        account_allowlist=None,
    )
    token = build_client_assertion_jwt(settings, private_key)
    decoded = jwt.decode(
        token,
        private_key.public_key(),
        algorithms=[JWT_ALGORITHM],
        audience=settings.jwt_audience,
        issuer=settings.issuer,
    )
    assert decoded["sub"] == "cid"
    assert decoded["iss"] == "cid"
    assert "jti" in decoded
    assert "exp" in decoded
    headers = jwt.get_unverified_header(token)
    assert headers["kid"] == "kid-1"
    assert headers["alg"] == JWT_ALGORITHM


def test_build_client_assertion_jwt_omits_kid_header_when_unset(tmp_path):
    path, private_key = _temp_key_path(tmp_path)
    settings = RevolutExtractSettings(
        client_id="cid",
        issuer="cid",
        jwt_audience="https://revolut.com",
        jwt_kid=None,
        private_key_path=str(path),
        private_key_passphrase=None,
        refresh_token="rt",
        authorization_code=None,
        access_token=None,
        use_sandbox=True,
        transaction_lookback_days=7,
        initial_history_days=30,
        list_count=100,
        store_raw_payload=False,
        account_allowlist=None,
    )
    token = build_client_assertion_jwt(settings, private_key)
    headers = jwt.get_unverified_header(token)
    assert "kid" not in headers
    assert headers["alg"] == JWT_ALGORITHM
