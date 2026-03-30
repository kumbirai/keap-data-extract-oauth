"""Serialize Stripe SDK objects to plain dicts for raw_payload storage."""
from typing import Any, Optional


def stripe_object_to_dict(obj: Any) -> Optional[dict]:
    if obj is None:
        return None
    try:
        from stripe import util

        fn = getattr(util, "convert_to_dict", None)
        if callable(fn):
            return fn(obj)
    except Exception:
        pass
    if hasattr(obj, "to_dict_recursive"):
        try:
            return obj.to_dict_recursive()
        except Exception:
            pass
    if hasattr(obj, "to_dict"):
        try:
            return obj.to_dict()
        except Exception:
            pass
    return None
