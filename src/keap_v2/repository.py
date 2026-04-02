"""PostgreSQL upserts for Keap v2 tables (single- and composite-key)."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Type

from sqlalchemy import Table, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.database.batch_upsert import upsert_rows


def touch_now() -> datetime:
    return datetime.now(timezone.utc)


def upsert_simple_rows(session: Session, model_class: Type[Any], rows: Sequence[Dict[str, Any]]) -> None:
    upsert_rows(session, model_class, rows)


def upsert_composite_rows(
    session: Session,
    model_class: Type[Any],
    rows: Sequence[Dict[str, Any]],
    conflict_columns: Sequence[str],
) -> None:
    if not rows:
        return
    table: Table = model_class.__table__
    all_cols = {c.name for c in table.columns}
    cleaned: List[Dict[str, Any]] = [{k: v for k, v in row.items() if k in all_cols} for row in rows]
    stmt = insert(table).values(cleaned)
    excluded = stmt.excluded
    pk = set(conflict_columns)
    update_cols: Dict[str, Any] = {}
    for name in all_cols:
        if name in pk:
            continue
        if name == "loaded_at":
            update_cols[name] = func.coalesce(table.c.loaded_at, excluded.loaded_at)
        else:
            update_cols[name] = excluded[name]
    conflict_targets = [table.c[n] for n in conflict_columns]
    stmt = stmt.on_conflict_do_update(index_elements=conflict_targets, set_=update_cols)
    session.execute(stmt)
    session.commit()
