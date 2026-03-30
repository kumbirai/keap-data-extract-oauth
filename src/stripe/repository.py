"""Batch upsert Stripe rows into PostgreSQL."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Type

from sqlalchemy import Table, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session


def upsert_rows(session: Session, model_class: Type[Any], rows: Sequence[Dict[str, Any]]) -> None:
    if not rows:
        return
    table: Table = model_class.__table__
    all_cols = {c.name for c in table.columns}
    cleaned: List[Dict[str, Any]] = [{k: v for k, v in row.items() if k in all_cols} for row in rows]
    stmt = insert(table).values(cleaned)
    excluded = stmt.excluded
    update_cols: Dict[str, Any] = {}
    for name in all_cols:
        if name == "id":
            continue
        if name == "loaded_at":
            update_cols[name] = func.coalesce(table.c.loaded_at, excluded.loaded_at)
        else:
            update_cols[name] = excluded[name]
    stmt = stmt.on_conflict_do_update(index_elements=[table.c.id], set_=update_cols)
    session.execute(stmt)
    session.commit()


def touch_now() -> datetime:
    return datetime.now(timezone.utc)
