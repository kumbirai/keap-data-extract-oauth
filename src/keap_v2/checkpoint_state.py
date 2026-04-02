"""Fan-out checkpoint_json shape for Keap v2 (see CheckpointManager.checkpoint_json).

Keys (all optional):
- ``in_progress`` (bool): run ended before finishing all parents.
- ``last_parent_id`` (int): last parent row fully completed (contact / campaign / affiliate id).
- ``page_token`` (str | None): cursor for the current parent's paged list response.
- ``last_lead_source_id`` (str): last completed lead source id (Text pk from API).
- ``last_recurring_expense_id`` (str): recurring expense id for nested incurred sync.
"""
from typing import Any, Dict, Optional


def fanout_state(blob: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a mutable copy of fan-out checkpoint state."""
    return dict(blob) if isinstance(blob, dict) else {}
