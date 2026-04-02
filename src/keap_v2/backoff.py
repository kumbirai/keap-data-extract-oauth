"""Retry wrapper for Keap API rate limits and transient server errors."""
import logging
import time
from typing import Callable, Optional, TypeVar

from src.api.exceptions import KeapAPIError, KeapRateLimitError, KeapServerError

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_keap_backoff(call: Callable[[], T], max_attempts: int = 8) -> T:
    delay = 1.0
    last_exc: Optional[Exception] = None
    for attempt in range(max_attempts):
        try:
            return call()
        except KeapRateLimitError as e:
            last_exc = e
            logger.warning(
                "Keap rate limit, sleeping %.1fs (attempt %s/%s)",
                delay,
                attempt + 1,
                max_attempts,
            )
            time.sleep(delay)
            delay = min(delay * 2, 120.0)
        except KeapServerError as e:
            last_exc = e
            logger.warning(
                "Keap server error, sleeping %.1fs (attempt %s): %s",
                delay,
                attempt + 1,
                e,
            )
            time.sleep(delay)
            delay = min(delay * 2, 120.0)
    if last_exc:
        raise last_exc
    raise KeapAPIError("Keap backoff exhausted with no exception")
