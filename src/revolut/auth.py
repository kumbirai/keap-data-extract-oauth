"""PS256 client assertion JWT for Revolut Business API token exchange."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from src.revolut.api_constants import DEFAULT_ASSERTION_TTL_SECONDS, JWT_ALGORITHM
from src.revolut.settings import RevolutExtractSettings


def load_signing_key(settings: RevolutExtractSettings) -> Any:
    if not settings.private_key_path:
        raise ValueError("REVOLUT_PRIVATE_KEY_PATH is required for OAuth token exchange")
    with open(settings.private_key_path, "rb") as f:
        pem = f.read()
    passphrase = settings.private_key_passphrase.encode() if settings.private_key_passphrase else None
    return load_pem_private_key(pem, password=passphrase)


def build_client_assertion_jwt(settings: RevolutExtractSettings, private_key: Any) -> str:
    if not settings.client_id or not settings.issuer or not settings.jwt_kid:
        raise ValueError("Client assertion requires client_id, issuer, and jwt_kid")
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=DEFAULT_ASSERTION_TTL_SECONDS)
    payload: Dict[str, Any] = {
        "iss": settings.issuer,
        "sub": settings.client_id,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    headers = {"kid": settings.jwt_kid, "alg": JWT_ALGORITHM}
    return jwt.encode(payload, private_key, algorithm=JWT_ALGORITHM, headers=headers)
