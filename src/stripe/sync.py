"""Paginated Stripe list sync with checkpoint_json persistence."""
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import stripe
from sqlalchemy import or_

from src.scripts.checkpoint_manager import CheckpointManager
from src.scripts.loaders.base_loader import LoadResult
from src.stripe.checkpoint_state import (
    get_account_state,
    max_created_unix_from_objects,
    merge_account_state,
    resolve_created_gte,
)
from src.stripe.repository import touch_now, upsert_rows
from src.stripe.settings import StripeExtractSettings

logger = logging.getLogger(__name__)


def _list_page(
    list_fn: Callable[..., Any],
    *,
    limit: int,
    starting_after: Optional[str],
    created_gte: Optional[int],
    stripe_account_id: Optional[str],
) -> Any:
    params: Dict[str, Any] = {"limit": limit}
    if starting_after:
        params["starting_after"] = starting_after
    if created_gte is not None:
        params["created"] = {"gte": created_gte}
    if stripe_account_id:
        return list_fn(**params, stripe_account=stripe_account_id)
    return list_fn(**params)


def _with_backoff(call: Callable[[], Any], max_attempts: int = 6) -> Any:
    delay = 1.0
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return call()
        except stripe.error.RateLimitError as e:
            last_exc = e
            logger.warning("Stripe rate limit, sleeping %.1fs (attempt %s)", delay, attempt + 1)
            time.sleep(delay)
            delay = min(delay * 2, 60.0)
        except stripe.error.APIConnectionError as e:
            last_exc = e
            logger.warning("Stripe connection error, sleeping %.1fs: %s", delay, e)
            time.sleep(delay)
            delay = min(delay * 2, 60.0)
    if last_exc:
        raise last_exc
    raise RuntimeError("Stripe backoff exhausted")


def sync_stripe_entity(
    session: Any,
    checkpoint_manager: CheckpointManager,
    settings: StripeExtractSettings,
    entity_type: str,
    model_class: Any,
    list_fn: Callable[..., Any],
    mapper: Callable[[Any, Optional[str], datetime, bool], dict],
    stripe_account_id: Optional[str],
    update: bool,
) -> LoadResult:
    now = touch_now()
    root = checkpoint_manager.get_checkpoint_json(entity_type) or {}
    acc_state = get_account_state(root, stripe_account_id)
    last_loaded = checkpoint_manager.get_last_loaded_timestamp(entity_type)
    created_gte_initial = resolve_created_gte(update, acc_state, last_loaded, settings.lookback_seconds)

    in_progress = bool(acc_state.get("in_progress"))
    starting_after = acc_state.get("starting_after") if in_progress else None
    created_gte = created_gte_initial
    if in_progress and acc_state.get("resume_created_gte") is not None:
        created_gte = acc_state["resume_created_gte"]

    total = 0
    success = 0
    failed = 0
    max_created = int(acc_state.get("max_created_unix") or 0)

    try:
        while True:
            def do_list():
                return _list_page(
                    list_fn,
                    limit=settings.list_limit,
                    starting_after=starting_after,
                    created_gte=created_gte,
                    stripe_account_id=stripe_account_id,
                )

            page = _with_backoff(do_list)
            items = list(page.data) if page.data else []

            if not items:
                root = merge_account_state(
                    root,
                    stripe_account_id,
                    {
                        "starting_after": None,
                        "in_progress": False,
                        "resume_created_gte": None,
                        "max_created_unix": max_created,
                    },
                )
                checkpoint_manager.save_checkpoint(
                    entity_type=entity_type,
                    total_records_processed=total,
                    api_offset=0,
                    completed=True,
                    checkpoint_json=root,
                )
                break

            batch: List[dict] = []
            for obj in items:
                total += 1
                try:
                    batch.append(mapper(obj, stripe_account_id, now, settings.store_raw_payload))
                except Exception as e:
                    failed += 1
                    logger.error("Stripe map failed for %s: %s", entity_type, e, exc_info=True)

            if batch:
                try:
                    upsert_rows(session, model_class, batch)
                    success += len(batch)
                except Exception as e:
                    failed += len(batch)
                    logger.error("Stripe upsert failed for %s: %s", entity_type, e, exc_info=True)

            page_max = max_created_unix_from_objects(items)
            max_created = max(max_created, page_max)

            if page.has_more:
                starting_after = items[-1].id
                root = merge_account_state(
                    root,
                    stripe_account_id,
                    {
                        "starting_after": starting_after,
                        "in_progress": True,
                        "resume_created_gte": created_gte_initial if created_gte_initial is not None else created_gte,
                        "max_created_unix": max_created,
                    },
                )
                checkpoint_manager.save_checkpoint(
                    entity_type=entity_type,
                    total_records_processed=total,
                    api_offset=0,
                    completed=False,
                    checkpoint_json=root,
                )
            else:
                root = merge_account_state(
                    root,
                    stripe_account_id,
                    {
                        "starting_after": None,
                        "in_progress": False,
                        "resume_created_gte": None,
                        "max_created_unix": max_created,
                    },
                )
                checkpoint_manager.save_checkpoint(
                    entity_type=entity_type,
                    total_records_processed=total,
                    api_offset=0,
                    completed=True,
                    checkpoint_json=root,
                )
                break

    except stripe.error.StripeError as e:
        logger.error("Stripe API error for %s: %s", entity_type, e, exc_info=True)
        failed += 1
        raise

    return LoadResult(total, success, failed)


def _stripe_account_clause(model: Any, stripe_account_id: Optional[str]) -> Any:
    col = model.stripe_account_id
    if stripe_account_id:
        return col == stripe_account_id
    return col.is_(None)


def query_invoice_parents_for_line_items(
    session: Any,
    watermark_dt: Optional[datetime],
    stripe_account_id: Optional[str],
    mutable_statuses: Tuple[str, ...],
) -> List[Tuple[str, Optional[datetime]]]:
    from src.models.stripe_models import StripeInvoice

    m = StripeInvoice
    q = session.query(m.id, m.created).filter(_stripe_account_clause(m, stripe_account_id))
    if watermark_dt is not None:
        q = q.filter(or_(m.created >= watermark_dt, m.status.in_(mutable_statuses)))
    rows = q.order_by(m.id.asc()).all()
    return [(r.id, r.created) for r in rows]


def query_subscription_parents_for_items(
    session: Any,
    watermark_dt: Optional[datetime],
    stripe_account_id: Optional[str],
    mutable_statuses: Tuple[str, ...],
) -> List[Tuple[str, Optional[datetime]]]:
    from src.models.stripe_models import StripeSubscription

    m = StripeSubscription
    q = session.query(m.id, m.current_period_start).filter(_stripe_account_clause(m, stripe_account_id))
    if watermark_dt is not None:
        q = q.filter(
            or_(
                m.current_period_start >= watermark_dt,
                m.status.in_(mutable_statuses),
            )
        )
    rows = q.order_by(m.id.asc()).all()
    return [(r.id, r.current_period_start) for r in rows]


def _dt_to_unix(dt: Optional[datetime]) -> int:
    if dt is None:
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def sync_stripe_child_entity(
    session: Any,
    checkpoint_manager: CheckpointManager,
    settings: StripeExtractSettings,
    entity_type: str,
    query_parents: Callable[
        [Any, Optional[datetime], Optional[str]],
        List[Tuple[str, Optional[datetime]]],
    ],
    list_page: Callable[[str, int, Optional[str], Optional[str]], Any],
    child_model_class: Any,
    map_child_row: Callable[[Any, Optional[str], datetime, bool, str], dict],
    stripe_account_id: Optional[str],
    update: bool,
) -> LoadResult:
    """Sync child objects (invoice lines, subscription items) by iterating parent ids from the DB.

    Resume uses last_parent_id with lexicographic comparison, matching ORDER BY parent id in the
    parent queries (stable replay; ids are not guaranteed to follow wall-clock order).
    """
    now = touch_now()
    root = checkpoint_manager.get_checkpoint_json(entity_type) or {}
    acc_state = get_account_state(root, stripe_account_id)
    last_loaded = checkpoint_manager.get_last_loaded_timestamp(entity_type)
    parent_created_gte_initial = resolve_created_gte(update, acc_state, last_loaded, settings.lookback_seconds)

    in_progress = bool(acc_state.get("in_progress"))
    last_parent_id = acc_state.get("last_parent_id") if in_progress else None
    parent_created_gte_unix = parent_created_gte_initial
    if in_progress and acc_state.get("resume_parent_created_gte_unix") is not None:
        parent_created_gte_unix = acc_state["resume_parent_created_gte_unix"]

    watermark_dt: Optional[datetime] = None
    if parent_created_gte_unix is not None:
        watermark_dt = datetime.fromtimestamp(int(parent_created_gte_unix), tz=timezone.utc)

    parents = query_parents(session, watermark_dt, stripe_account_id)
    if last_parent_id:
        parents = [(pid, ts) for pid, ts in parents if pid > last_parent_id]

    total = 0
    success = 0
    failed = 0
    max_created_tracked = max(int(acc_state.get("max_created_unix") or 0), 0)

    if not parents:
        done_max = max(max_created_tracked, int(time.time()))
        root = merge_account_state(
            root,
            stripe_account_id,
            {
                "last_parent_id": None,
                "in_progress": False,
                "resume_parent_created_gte_unix": None,
                "max_created_unix": done_max,
            },
        )
        checkpoint_manager.save_checkpoint(
            entity_type=entity_type,
            total_records_processed=0,
            api_offset=0,
            completed=True,
            checkpoint_json=root,
        )
        return LoadResult(0, 0, 0)

    try:
        for parent_id, par_ts in parents:
            max_created_tracked = max(max_created_tracked, _dt_to_unix(par_ts))
            starting_after: Optional[str] = None
            while True:

                def do_list():
                    return list_page(parent_id, settings.list_limit, starting_after, stripe_account_id)

                page = _with_backoff(do_list)
                items = list(page.data) if page.data else []
                if not items:
                    break

                batch: List[dict] = []
                for obj in items:
                    total += 1
                    try:
                        batch.append(
                            map_child_row(obj, stripe_account_id, now, settings.store_raw_payload, parent_id)
                        )
                    except Exception as e:
                        failed += 1
                        logger.error(
                            "Stripe child map failed for %s parent=%s: %s",
                            entity_type,
                            parent_id,
                            e,
                            exc_info=True,
                        )

                if batch:
                    try:
                        upsert_rows(session, child_model_class, batch)
                        success += len(batch)
                    except Exception as e:
                        failed += len(batch)
                        logger.error(
                            "Stripe child upsert failed for %s parent=%s: %s",
                            entity_type,
                            parent_id,
                            e,
                            exc_info=True,
                        )

                if page.has_more:
                    starting_after = items[-1].id
                else:
                    break

            root = merge_account_state(
                root,
                stripe_account_id,
                {
                    "last_parent_id": parent_id,
                    "in_progress": True,
                    "resume_parent_created_gte_unix": parent_created_gte_unix,
                    "max_created_unix": max_created_tracked,
                },
            )
            checkpoint_manager.save_checkpoint(
                entity_type=entity_type,
                total_records_processed=total,
                api_offset=0,
                completed=False,
                checkpoint_json=root,
            )

        done_max = max(max_created_tracked, int(time.time()))
        root = merge_account_state(
            root,
            stripe_account_id,
            {
                "last_parent_id": None,
                "in_progress": False,
                "resume_parent_created_gte_unix": None,
                "max_created_unix": done_max,
            },
        )
        checkpoint_manager.save_checkpoint(
            entity_type=entity_type,
            total_records_processed=total,
            api_offset=0,
            completed=True,
            checkpoint_json=root,
        )

    except stripe.error.StripeError as e:
        logger.error("Stripe API error for %s: %s", entity_type, e, exc_info=True)
        failed += 1
        raise

    return LoadResult(total, success, failed)


def retrieve_and_upsert(
    session: Any,
    settings: StripeExtractSettings,
    model_class: Any,
    retrieve_fn: Callable[..., Any],
    mapper: Callable[[Any, Optional[str], datetime, bool], dict],
    object_id: str,
    stripe_account_id: Optional[str],
) -> bool:
    now = touch_now()

    def fetch():
        if stripe_account_id:
            return retrieve_fn(object_id, stripe_account=stripe_account_id)
        return retrieve_fn(object_id)

    obj = _with_backoff(fetch)
    row = mapper(obj, stripe_account_id, now, settings.store_raw_payload)
    upsert_rows(session, model_class, [row])
    return True
