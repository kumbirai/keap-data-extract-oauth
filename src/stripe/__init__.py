"""Stripe BI extract (documentation/stripe/)."""
from typing import Any

from src.stripe.constants import STRIPE_ENTITY_TYPES


def run_stripe_extract(*args: Any, **kwargs: Any):
    from src.stripe.orchestrator import run_stripe_extract as _impl

    return _impl(*args, **kwargs)


def run_stripe_entity(*args: Any, **kwargs: Any):
    from src.stripe.orchestrator import run_stripe_entity as _impl

    return _impl(*args, **kwargs)


def run_stripe_object_by_id(*args: Any, **kwargs: Any):
    from src.stripe.orchestrator import run_stripe_object_by_id as _impl

    return _impl(*args, **kwargs)


__all__ = [
    "STRIPE_ENTITY_TYPES",
    "run_stripe_extract",
    "run_stripe_entity",
    "run_stripe_object_by_id",
]
