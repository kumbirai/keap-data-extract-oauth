"""Load Revolut Merchant locations into revolut_merchant_locations (full sync each run)."""
import logging
from typing import Any

from src.database.batch_upsert import touch_now, upsert_rows
from src.models.revolut_merchant_models import RevolutMerchantLocation
from src.revolut.merchant_checkpoint_state import MERCHANT_LOCATIONS_ENTITY, to_iso
from src.revolut.merchant_client import RevolutMerchantClient
from src.revolut.merchant_mappers import map_location
from src.revolut.merchant_settings import RevolutMerchantSettings
from src.scripts.checkpoint_manager import CheckpointManager
from src.scripts.loaders.base_loader import LoadResult

logger = logging.getLogger(__name__)


def sync_merchant_locations(
    session: Any,
    checkpoint_manager: CheckpointManager,
    client: RevolutMerchantClient,
    settings: RevolutMerchantSettings,
) -> LoadResult:
    now = touch_now()
    total = 0
    success = 0
    failed = 0

    try:
        raw_list = client.list_locations()
    except Exception as e:
        logger.error("Revolut Merchant list_locations failed: %s", e, exc_info=True)
        return LoadResult(0, 0, 1)

    batch = []
    for item in raw_list:
        if not isinstance(item, dict):
            failed += 1
            continue
        total += 1
        try:
            batch.append(map_location(item, now, settings.store_raw_payload))
        except Exception as e:
            failed += 1
            logger.error("Revolut Merchant location map failed id=%s: %s", item.get("id"), e, exc_info=True)

    if batch:
        try:
            upsert_rows(session, RevolutMerchantLocation, batch)
            success += len(batch)
        except Exception as e:
            failed += len(batch)
            success = 0
            logger.error("Revolut Merchant location upsert failed: %s", e, exc_info=True)

    logger.info(
        "Revolut Merchant locations: total=%s success=%s failed=%s",
        total, success, failed,
    )
    checkpoint_manager.save_checkpoint(
        entity_type=MERCHANT_LOCATIONS_ENTITY,
        total_records_processed=success,
        api_offset=0,
        completed=True,
        checkpoint_json={"last_run_at": to_iso(now)},
    )
    return LoadResult(total, success, failed)
