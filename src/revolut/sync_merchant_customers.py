"""Load Revolut Merchant customers + payment methods fan-out."""
import logging
from typing import Any, List

from src.database.batch_upsert import touch_now, upsert_rows
from src.models.revolut_merchant_models import RevolutMerchantCustomer, RevolutMerchantPaymentMethod
from src.revolut.merchant_checkpoint_state import MERCHANT_CUSTOMERS_ENTITY, to_iso
from src.revolut.merchant_client import RevolutMerchantApiError, RevolutMerchantClient
from src.revolut.merchant_mappers import map_customer, map_payment_method
from src.revolut.merchant_settings import RevolutMerchantSettings
from src.scripts.checkpoint_manager import CheckpointManager
from src.scripts.loaders.base_loader import LoadResult

logger = logging.getLogger(__name__)


def _load_payment_methods(
    session: Any,
    client: RevolutMerchantClient,
    settings: RevolutMerchantSettings,
    customer_id: str,
    now: Any,
) -> int:
    """Fetch and upsert payment methods for one customer. Returns count upserted."""
    try:
        raw_pms = client.get_customer_payment_methods(customer_id)
    except RevolutMerchantApiError as e:
        if e.status_code == 404:
            logger.warning(
                "Revolut Merchant payment methods 404 for customer_id=%s, skipping", customer_id
            )
            return 0
        logger.error(
            "Revolut Merchant payment methods failed customer_id=%s: %s", customer_id, e, exc_info=True
        )
        return 0
    except Exception as e:
        logger.error(
            "Revolut Merchant payment methods error customer_id=%s: %s", customer_id, e, exc_info=True
        )
        return 0

    pm_rows: List[dict] = []
    for pm in raw_pms:
        if not isinstance(pm, dict):
            continue
        try:
            pm_rows.append(map_payment_method(pm, customer_id, now, settings.store_raw_payload))
        except Exception as e:
            logger.error(
                "Revolut Merchant payment method map failed customer_id=%s pm_id=%s: %s",
                customer_id,
                pm.get("id"),
                e,
                exc_info=True,
            )
    if pm_rows:
        upsert_rows(session, RevolutMerchantPaymentMethod, pm_rows)
    return len(pm_rows)


def sync_merchant_customers(
    session: Any,
    checkpoint_manager: CheckpointManager,
    client: RevolutMerchantClient,
    settings: RevolutMerchantSettings,
) -> LoadResult:
    now = touch_now()
    total = 0
    success = 0
    failed = 0
    cursor = None

    while True:
        try:
            page = client.list_customers(count=settings.page_size, cursor=cursor)
        except Exception as e:
            logger.error("Revolut Merchant list_customers failed cursor=%s: %s", cursor, e, exc_info=True)
            failed += 1
            break

        if not page:
            break

        customer_rows = []
        for item in page:
            if not isinstance(item, dict):
                failed += 1
                continue
            total += 1
            try:
                customer_rows.append(map_customer(item, now, settings.store_raw_payload))
            except Exception as e:
                failed += 1
                logger.error(
                    "Revolut Merchant customer map failed id=%s: %s", item.get("id"), e, exc_info=True
                )

        if customer_rows:
            try:
                upsert_rows(session, RevolutMerchantCustomer, customer_rows)
                success += len(customer_rows)
            except Exception as e:
                failed += len(customer_rows)
                success = max(0, success)
                logger.error("Revolut Merchant customer upsert failed: %s", e, exc_info=True)

            # Fan-out: fetch payment methods per customer
            for row in customer_rows:
                _load_payment_methods(session, client, settings, row["id"], now)

        # Cursor-based pagination: if page is full, try the next cursor.
        # The Merchant API cursor format is unknown until tested; use id of last item as fallback.
        if len(page) < settings.page_size:
            break
        # Try to extract a cursor from the response metadata or fall back to id-based.
        last_item = page[-1] if page else {}
        next_cursor = last_item.get("cursor") or last_item.get("id")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    logger.info(
        "Revolut Merchant customers: total=%s success=%s failed=%s",
        total, success, failed,
    )
    checkpoint_manager.save_checkpoint(
        entity_type=MERCHANT_CUSTOMERS_ENTITY,
        total_records_processed=success,
        api_offset=0,
        completed=True,
        checkpoint_json={"last_run_at": to_iso(now)},
    )
    return LoadResult(total, success, failed)
