"""Revolut Merchant API extract configuration from environment (documentation/revolut/sprint-02/05-access-keys-and-credentials.md)."""
import os
from dataclasses import dataclass
from typing import Optional

from src.revolut.merchant_api_constants import (
    DEFAULT_API_VERSION,
    DEFAULT_PAGE_SIZE,
    PRODUCTION_HOST,
    SANDBOX_HOST,
)


@dataclass(frozen=True)
class RevolutMerchantSettings:
    """Static Bearer API key settings for the Revolut Merchant API (no OAuth required)."""

    api_key: str
    use_sandbox: bool
    api_version: str
    lookback_days: int
    dispute_lookback_days: int
    initial_history_days: int
    page_size: int
    store_raw_payload: bool

    @property
    def api_base_url(self) -> str:
        host = SANDBOX_HOST if self.use_sandbox else PRODUCTION_HOST
        return host.rstrip("/")

    @classmethod
    def from_env(cls) -> Optional["RevolutMerchantSettings"]:
        api_key = os.getenv("REVOLUT_MERCHANT_API_KEY", "").strip()
        if not api_key:
            return None
        use_sandbox = os.getenv("REVOLUT_MERCHANT_USE_SANDBOX", "false").lower() in ("1", "true", "yes")
        api_version = os.getenv("REVOLUT_MERCHANT_API_VERSION", "").strip() or DEFAULT_API_VERSION
        lookback = max(0, int(os.getenv("REVOLUT_MERCHANT_LOOKBACK_DAYS", "7")))
        dispute_lookback = max(0, int(os.getenv("REVOLUT_MERCHANT_DISPUTE_LOOKBACK_DAYS", "30")))
        initial_days = max(1, int(os.getenv("REVOLUT_MERCHANT_INITIAL_HISTORY_DAYS", "730")))
        page_size = min(max(1, int(os.getenv("REVOLUT_MERCHANT_PAGE_SIZE", str(DEFAULT_PAGE_SIZE)))), 1000)
        raw_flag = os.getenv("REVOLUT_MERCHANT_STORE_RAW_PAYLOAD", "false").lower() in ("1", "true", "yes")
        return cls(
            api_key=api_key,
            use_sandbox=use_sandbox,
            api_version=api_version,
            lookback_days=lookback,
            dispute_lookback_days=dispute_lookback,
            initial_history_days=initial_days,
            page_size=page_size,
            store_raw_payload=raw_flag,
        )
