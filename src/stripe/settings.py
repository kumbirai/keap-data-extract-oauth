"""Stripe extract configuration from environment."""
import os
from dataclasses import dataclass
from typing import List, Optional


def _parse_account_ids(raw: Optional[str]) -> List[Optional[str]]:
    """Return list of connected account ids; empty string in env means platform-only [None]."""
    if not raw or not raw.strip():
        return [None]
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts if parts else [None]


@dataclass(frozen=True)
class StripeExtractSettings:
    api_key: str
    account_ids: List[Optional[str]]
    api_version: Optional[str]
    list_limit: int
    lookback_seconds: int
    store_raw_payload: bool

    @classmethod
    def from_env(cls, batch_size: int = 50) -> Optional["StripeExtractSettings"]:
        key = os.getenv("STRIPE_API_KEY", "").strip()
        if not key:
            return None
        limit = min(100, max(1, int(os.getenv("STRIPE_LIST_LIMIT", str(batch_size)))))
        lookback_days = max(0, int(os.getenv("STRIPE_CHARGE_LOOKBACK_DAYS", "7")))
        raw_flag = os.getenv("STRIPE_STORE_RAW_PAYLOAD", "true").lower() in ("1", "true", "yes")
        ver = os.getenv("STRIPE_API_VERSION", "").strip() or None
        return cls(
            api_key=key,
            account_ids=_parse_account_ids(os.getenv("STRIPE_ACCOUNT_IDS")),
            api_version=ver,
            list_limit=limit,
            lookback_seconds=lookback_days * 86400,
            store_raw_payload=raw_flag,
        )
