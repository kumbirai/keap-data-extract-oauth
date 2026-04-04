"""Load Revolut Merchant orders (time-windowed) + order payments fan-out."""
import logging
from typing import Any, List

from src.database.batch_upsert import touch_now, upsert_rows
from src.models.revolut_merchant_models import RevolutMerchantOrder, RevolutMerchantOrderPayment
from src.revolut.merchant_checkpoint_state import (
    MERCHANT_ORDERS_ENTITY,
    compute_window,
    merge_state,
    next_page_created_before,
    to_iso,
)
from src.revolut.merchant_client import RevolutMerchantApiError, RevolutMerchantClient
from src.revolut.merchant_mappers import map_order, map_order_payment
from src.revolut.merchant_settings import RevolutMerchantSettings
from src.scripts.checkpoint_manager import CheckpointManager
from src.scripts.loaders.base_loader import LoadResult

logger = logging.getLogger(__name__)


def _load_order_payments(
    session: Any,
    client: RevolutMerchantClient,
    settings: RevolutMerchantSettings,
    order_id: str,
    now: Any,
) -> int:
    """Fetch and upsert payment attempts for one order. Returns count upserted."""
    try:
        raw_payments = client.get_order_payments(order_id)
    except RevolutMerchantApiError as e:
        if e.status_code == 404:
            logger.warning(
                "Revolut Merchant order payments 404 for order_id=%s, skipping", order_id
            )
            return 0
        logger.error(
            "Revolut Merchant order payments failed order_id=%s: %s", order_id, e, exc_info=True
        )
        return 0
    except Exception as e:
        logger.error(
            "Revolut Merchant order payments error order_id=%s: %s", order_id, e, exc_info=True
        )
        return 0

    rows: List[dict] = []
    for payment in raw_payments:
        if not isinstance(payment, dict):
            continue
        try:
            rows.append(map_order_payment(payment, order_id, now, settings.store_raw_payload))
        except Exception as e:
            logger.error(
                "Revolut Merchant order payment map failed order_id=%s payment_id=%s: %s",
                order_id,
                payment.get("id"),
                e,
                exc_info=True,
            )
    if rows:
        upsert_rows(session, RevolutMerchantOrderPayment, rows)
    return len(rows)


def sync_merchant_orders(
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

    state = checkpoint_manager.get_checkpoint_json(MERCHANT_ORDERS_ENTITY) or {}
    window_from, window_to = compute_window(
        update=update,
        state=state,
        lookback_days=settings.lookback_days,
        initial_history_days=settings.initial_history_days,
        now=now,
    )

    from_iso = to_iso(window_from)
    created_before = to_iso(window_to)

    logger.info(
        "Revolut Merchant orders: window [%s, %s) update=%s",
        from_iso, created_before, update,
    )

    while True:
        try:
            page = client.list_orders(
                from_iso=from_iso,
                created_before=created_before,
                count=settings.page_size,
            )
        except Exception as e:
            logger.error(
                "Revolut Merchant list_orders failed from=%s created_before=%s: %s",
                from_iso, created_before, e, exc_info=True,
            )
            failed += 1
            break

        if not page:
            break

        order_rows = []
        for item in page:
            if not isinstance(item, dict):
                failed += 1
                continue
            total += 1
            try:
                order_rows.append(map_order(item, now, settings.store_raw_payload))
            except Exception as e:
                failed += 1
                logger.error(
                    "Revolut Merchant order map failed id=%s: %s", item.get("id"), e, exc_info=True
                )

        if order_rows:
            try:
                upsert_rows(session, RevolutMerchantOrder, order_rows)
                success += len(order_rows)
            except Exception as e:
                failed += len(order_rows)
                logger.error("Revolut Merchant order upsert failed: %s", e, exc_info=True)

            # Fan-out: fetch payment attempts per order
            for row in order_rows:
                _load_order_payments(session, client, settings, row["id"], now)

        # Advance pagination cursor: created_before = created_at of last item in page
        next_cb = next_page_created_before(page, page_size=settings.page_size)
        if not next_cb:
            break
        created_before = next_cb

    logger.info(
        "Revolut Merchant orders: total=%s success=%s failed=%s",
        total, success, failed,
    )
    new_state = merge_state(state, {
        "window_from": from_iso,
        "window_to": to_iso(window_to),
        "last_run_at": to_iso(now),
    })
    checkpoint_manager.save_checkpoint(
        entity_type=MERCHANT_ORDERS_ENTITY,
        total_records_processed=success,
        api_offset=0,
        completed=True,
        checkpoint_json=new_state,
    )
    return LoadResult(total, success, failed)
