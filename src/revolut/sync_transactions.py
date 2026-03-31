"""
Load Revolut transactions per account with date window, lookback, and `to`-based pagination.

Revolut returns transactions in reverse chronological order. When a page is full, the next
request uses `to` set to the previous page's oldest `created_at` (see Revolut guide:
accounts-and-transactions syncing).
"""
import logging
from datetime import datetime, timezone
from typing import Any, List, Sequence

from src.database.batch_upsert import touch_now, upsert_rows
from src.models.revolut_models import RevolutTransaction
from src.revolut.checkpoint_state import (
    compute_transaction_window,
    max_created_iso,
    merge_state,
    next_pagination_to,
    transactions_entity_key,
)
from src.revolut.client import RevolutClient
from src.revolut.mappers import map_transaction
from src.revolut.settings import RevolutExtractSettings
from src.scripts.checkpoint_manager import CheckpointManager
from src.scripts.loaders.base_loader import LoadResult

logger = logging.getLogger(__name__)


def _iso_z(dt: datetime) -> str:
    u = dt.astimezone(timezone.utc)
    return u.isoformat().replace("+00:00", "Z")


def sync_revolut_transactions_for_accounts(
    session: Any,
    checkpoint_manager: CheckpointManager,
    client: RevolutClient,
    settings: RevolutExtractSettings,
    account_ids: Sequence[str],
    update: bool,
) -> LoadResult:
    total = 0
    success = 0
    failed = 0
    now = touch_now()

    for account_id in account_ids:
        r = _sync_one_account(session, checkpoint_manager, client, settings, account_id, update, now)
        total += r.total_records
        success += r.success_count
        failed += r.failed_count
    return LoadResult(total, success, failed)


def _sync_one_account(
    session: Any,
    checkpoint_manager: CheckpointManager,
    client: RevolutClient,
    settings: RevolutExtractSettings,
    account_id: str,
    update: bool,
    now: datetime,
) -> LoadResult:
    entity_key = transactions_entity_key(account_id)
    state = checkpoint_manager.get_checkpoint_json(entity_key) or {}
    if not isinstance(state, dict):
        state = {}

    in_progress = bool(state.get("in_progress"))
    pagination_to = state.get("pagination_to") if in_progress else None

    if in_progress and state.get("window_from"):
        from_iso = str(state["window_from"])
        wto_raw = state.get("window_to")
        if wto_raw:
            try:
                window_to = datetime.fromisoformat(str(wto_raw).replace("Z", "+00:00"))
                if window_to.tzinfo is None:
                    window_to = window_to.replace(tzinfo=timezone.utc)
            except ValueError:
                _, window_to = compute_transaction_window(
                    update=update,
                    state=state,
                    lookback_days=settings.transaction_lookback_days,
                    initial_history_days=settings.initial_history_days,
                    now=now,
                )
        else:
            _, window_to = compute_transaction_window(
                update=update,
                state=state,
                lookback_days=settings.transaction_lookback_days,
                initial_history_days=settings.initial_history_days,
                now=now,
            )
    else:
        window_from, window_to = compute_transaction_window(
            update=update,
            state=state,
            lookback_days=settings.transaction_lookback_days,
            initial_history_days=settings.initial_history_days,
            now=now,
        )
        from_iso = _iso_z(window_from)

    to_iso = str(pagination_to) if pagination_to else _iso_z(window_to)

    total = 0
    success = 0
    failed = 0
    max_created = state.get("last_max_created_at")
    count = settings.list_count

    try:
        while True:
            items = client.list_transactions(
                account_id=account_id,
                from_iso=from_iso,
                to_iso=to_iso,
                count=count,
            )
            if not items:
                new_state = merge_state(
                    state,
                    {
                        "in_progress": False,
                        "pagination_to": None,
                        "window_from": from_iso,
                        "window_to": _iso_z(window_to),
                        "last_max_created_at": max_created,
                    },
                )
                checkpoint_manager.save_checkpoint(
                    entity_type=entity_key,
                    total_records_processed=total,
                    api_offset=0,
                    completed=True,
                    checkpoint_json=new_state,
                )
                break

            batch: List[dict] = []
            for item in items:
                if not isinstance(item, dict):
                    failed += 1
                    continue
                total += 1
                try:
                    batch.append(
                        map_transaction(
                            item,
                            default_account_id=account_id,
                            now=now,
                            store_raw=settings.store_raw_payload,
                        )
                    )
                except Exception as e:
                    failed += 1
                    logger.error(
                        "Revolut transaction map failed account=%s: %s",
                        account_id,
                        e,
                        exc_info=True,
                    )

            if batch:
                try:
                    upsert_rows(session, RevolutTransaction, batch)
                    success += len(batch)
                except Exception as e:
                    failed += len(batch)
                    logger.error(
                        "Revolut transaction upsert failed account=%s: %s",
                        account_id,
                        e,
                        exc_info=True,
                    )

            max_created = max_created_iso(max_created if isinstance(max_created, str) else None, items)

            nxt = next_pagination_to(items, count=count)
            if nxt:
                new_state = merge_state(
                    state,
                    {
                        "in_progress": True,
                        "pagination_to": nxt,
                        "window_from": from_iso,
                        "window_to": _iso_z(window_to),
                        "last_max_created_at": max_created,
                    },
                )
                checkpoint_manager.save_checkpoint(
                    entity_type=entity_key,
                    total_records_processed=total,
                    api_offset=0,
                    completed=False,
                    checkpoint_json=new_state,
                )
                state = new_state
                to_iso = nxt
                continue

            new_state = merge_state(
                state,
                {
                    "in_progress": False,
                    "pagination_to": None,
                    "window_from": from_iso,
                    "window_to": _iso_z(window_to),
                    "last_max_created_at": max_created,
                },
            )
            checkpoint_manager.save_checkpoint(
                entity_type=entity_key,
                total_records_processed=total,
                api_offset=0,
                completed=True,
                checkpoint_json=new_state,
            )
            break

    except Exception as e:
        logger.error("Revolut transaction sync failed account=%s: %s", account_id, e, exc_info=True)
        return LoadResult(total, success, failed + 1)

    return LoadResult(total, success, failed)
