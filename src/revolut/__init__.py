"""Revolut BI extract (documentation/revolut/)."""
from typing import Any

from src.revolut.constants import REVOLUT_ENTITY_TYPES


def run_revolut_extract(*args: Any, **kwargs: Any):
    from src.revolut.orchestrator import run_revolut_extract as _impl

    return _impl(*args, **kwargs)


def run_revolut_entity(*args: Any, **kwargs: Any):
    from src.revolut.orchestrator import run_revolut_entity as _impl

    return _impl(*args, **kwargs)


__all__ = [
    "REVOLUT_ENTITY_TYPES",
    "run_revolut_extract",
    "run_revolut_entity",
]
