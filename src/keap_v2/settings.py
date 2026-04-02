"""Environment-driven settings for Keap REST v2 extract."""
import os
from dataclasses import dataclass


DEFAULT_CRM_BASE_URL = "https://api.infusionsoft.com/crm"


def _truthy(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        v = int(raw)
        return v if v > 0 else default
    except ValueError:
        return default


def _non_negative_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        v = float(raw)
        return v if v >= 0 else default
    except ValueError:
        return default


@dataclass(frozen=True)
class KeapV2ExtractSettings:
    """Configuration for v2 list and fan-out sync."""

    enabled: bool
    crm_base_url: str
    page_size: int
    fan_out_delay_seconds: float
    lead_score_max_attempts: int

    @classmethod
    def from_env(cls) -> "KeapV2ExtractSettings":
        return cls(
            enabled=_truthy("KEAP_V2_EXTRACT_ENABLED", True),
            crm_base_url=os.getenv("KEAP_REST_CRM_BASE_URL", DEFAULT_CRM_BASE_URL).rstrip("/"),
            page_size=_positive_int("KEAP_V2_PAGE_SIZE", 100),
            fan_out_delay_seconds=_non_negative_float("KEAP_V2_FAN_OUT_DELAY_SECONDS", 0.0),
            lead_score_max_attempts=_positive_int("KEAP_V2_LEAD_SCORE_MAX_ATTEMPTS", 3),
        )
