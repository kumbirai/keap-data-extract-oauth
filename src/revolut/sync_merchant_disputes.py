"""Load Revolut Merchant disputes (time-windowed with longer lookback)."""
import logging
from typing import Any

from src.database.batch_upsert import touch_now, upsert_rows
from src.models.revolut_merchant_models import RevolutMerchantDispute
from src.revolut.merchant_checkpoint_state import (
    MERCHANT_DISPUTES_ENTITY,
    compute_window,
    merge_state,
    next_page_created_before,
    to_iso,
)
from src.revolut.merchant_client import RevolutMerchantClient
from src.revolut.merchant_mappers import map_dispute
from src.revolut.merchant_settings import RevolutMerchantSettings
from src.scripts.checkpoint_manager import CheckpointManager
from src.scripts.loaders.base_loader import LoadResult

logger = logging.getLogger(__name__)


def sync_merchant_disputes(
    session: Any,
    checkpoint_manager: CheckpointManager,
    client: RevolutMerchantClient,
    settings: RevolutMerchantSettings,
    update: bool = False,
) -> LoadResult:
    now = touch_now()
    total = 0
    success = 0
    failed = 0

    state = checkpoint_manager.get_checkpoint_json(MERCHANT_DISPUTES_ENTITY) or {}
    # Use dispute_lookback_days (default 30) — disputes evolve slowly.
    window_from, window_to = compute_window(
        update=update,
        state=state,
        lookback_days=settings.dispute_lookback_days,
        initial_history_days=settings.initial_history_days,
        now=now,
    )

    from_iso = to_iso(window_from)
    created_before = to_iso(window_to)

    logger.info(
        "Revolut Merchant disputes: window [%s, %s) update=%s",
        from_iso, created_before, update,
    )

    while True:
        try:
            page = client.list_disputes(
                from_iso=from_iso,
                created_before=created_before,
                count=settings.page_size,
            )
        except Exception as e:
            logger.error(
                "Revolut Merchant list_disputes failed from=%s created_before=%s: %s",
                from_iso, created_before, e, exc_info=True,
            )
            failed += 1
            break

        if not page:
            break

        batch = []
        for item in page:
            if not isinstance(item, dict):
                failed += 1
                continue
            total += 1
            try:
                batch.append(map_dispute(item, now, settings.store_raw_payload))
            except Exception as e:
                failed += 1
                logger.error(
                    "Revolut Merchant dispute map failed id=%s: %s", item.get("id"), e, exc_info=True
                )

        if batch:
            try:
                upsert_rows(session, RevolutMerchantDispute, batch)
                success += len(batch)
            except Exception as e:
                failed += len(batch)
                logger.error("Revolut Merchant dispute upsert failed: %s", e, exc_info=True)

        next_cb = next_page_created_before(page, page_size=settings.page_size)
        if not next_cb:
            break
        created_before = next_cb

    logger.info(
        "Revolut Merchant disputes: total=%s success=%s failed=%s",
        total, success, failed,
    )
    new_state = merge_state(state, {
        "window_from": from_iso,
        "window_to": to_iso(window_to),
        "last_run_at": to_iso(now),
    })
    checkpoint_manager.save_checkpoint(
        entity_type=MERCHANT_DISPUTES_ENTITY,
        total_records_processed=success,
        api_offset=0,
        completed=True,
        checkpoint_json=new_state,
    )
    return LoadResult(total, success, failed)
