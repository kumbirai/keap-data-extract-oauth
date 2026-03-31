"""Revolut extract configuration from environment (documentation/revolut/05-access-keys-and-credentials.md)."""
import os
from dataclasses import dataclass
from typing import Optional, Set

from src.revolut.api_constants import MAX_TRANSACTION_PAGE_SIZE


def _parse_account_allowlist(raw: Optional[str]) -> Optional[Set[str]]:
    if raw is None or not raw.strip():
        return None
    parts = {p.strip() for p in raw.split(",") if p.strip()}
    return parts if parts else None


@dataclass(frozen=True)
class RevolutExtractSettings:
    client_id: str
    issuer: str
    jwt_audience: str
    jwt_kid: str
    private_key_path: str
    private_key_passphrase: Optional[str]
    refresh_token: Optional[str]
    authorization_code: Optional[str]
    use_sandbox: bool
    transaction_lookback_days: int
    initial_history_days: int
    list_count: int
    store_raw_payload: bool
    account_allowlist: Optional[Set[str]]

    @property
    def api_base_url(self) -> str:
        from src.revolut.api_constants import PRODUCTION_HOST, SANDBOX_HOST

        host = SANDBOX_HOST if self.use_sandbox else PRODUCTION_HOST
        return host.rstrip("/")

    @property
    def token_url(self) -> str:
        from src.revolut.api_constants import TOKEN_PATH

        return f"{self.api_base_url}{TOKEN_PATH}"

    @classmethod
    def from_env(cls) -> Optional["RevolutExtractSettings"]:
        client_id = os.getenv("REVOLUT_CLIENT_ID", "").strip()
        if not client_id:
            return None
        key_path = os.getenv("REVOLUT_PRIVATE_KEY_PATH", "").strip()
        if not key_path:
            return None
        kid = os.getenv("REVOLUT_JWT_KID", "").strip()
        if not kid:
            return None
        issuer = os.getenv("REVOLUT_ISSUER", "").strip() or client_id
        audience = os.getenv("REVOLUT_JWT_AUDIENCE", "").strip()
        if not audience:
            from src.revolut.api_constants import DEFAULT_JWT_AUDIENCE

            audience = DEFAULT_JWT_AUDIENCE
        refresh = os.getenv("REVOLUT_REFRESH_TOKEN", "").strip() or None
        auth_code = os.getenv("REVOLUT_AUTHORIZATION_CODE", "").strip() or None
        if not refresh and not auth_code:
            return None
        use_sandbox = os.getenv("REVOLUT_USE_SANDBOX", "false").lower() in ("1", "true", "yes")
        lookback = max(0, int(os.getenv("REVOLUT_TRANSACTION_LOOKBACK_DAYS", "7")))
        initial_days = max(1, int(os.getenv("REVOLUT_INITIAL_HISTORY_DAYS", "730")))
        list_count = min(max(1, int(os.getenv("REVOLUT_LIST_COUNT", "500"))), MAX_TRANSACTION_PAGE_SIZE)
        raw_flag = os.getenv("REVOLUT_STORE_RAW_PAYLOAD", "false").lower() in ("1", "true", "yes")
        passphrase = os.getenv("REVOLUT_PRIVATE_KEY_PASSPHRASE", "").strip() or None
        allow = _parse_account_allowlist(os.getenv("REVOLUT_ACCOUNT_IDS"))
        return cls(
            client_id=client_id,
            issuer=issuer,
            jwt_audience=audience,
            jwt_kid=kid,
            private_key_path=key_path,
            private_key_passphrase=passphrase,
            refresh_token=refresh,
            authorization_code=auth_code,
            use_sandbox=use_sandbox,
            transaction_lookback_days=lookback,
            initial_history_days=initial_days,
            list_count=list_count,
            store_raw_payload=raw_flag,
            account_allowlist=allow,
        )
