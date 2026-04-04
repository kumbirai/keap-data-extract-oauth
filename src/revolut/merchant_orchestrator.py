"""Revolut Merchant API extract facade (documentation/revolut/sprint-02/03-extract-integration.md)."""
import logging
from typing import Any, Optional

from src.revolut.merchant_client import RevolutMerchantClient
from src.revolut.merchant_settings import RevolutMerchantSettings
from src.revolut.sync_merchant_customers import sync_merchant_customers
from src.revolut.sync_merchant_disputes import sync_merchant_disputes
from src.revolut.sync_merchant_locations import sync_merchant_locations
from src.revolut.sync_merchant_orders import sync_merchant_orders
from src.scripts.checkpoint_manager import CheckpointManager
from src.scripts.loaders.base_loader import LoadResult

logger = logging.getLogger(__name__)

_SKIP_MSG = (
    "Revolut Merchant extract skipped: set REVOLUT_MERCHANT_API_KEY. "
    "See documentation/revolut/sprint-02/05-access-keys-and-credentials.md."
)


def _settings_from_env() -> Optional[RevolutMerchantSettings]:
    return RevolutMerchantSettings.from_env()


def _combine(*results: LoadResult) -> LoadResult:
    return LoadResult(
        sum(r.total_records for r in results),
        sum(r.success_count for r in results),
        sum(r.failed_count for r in results),
    )


def run_revolut_merchant_extract(
    session: Any,
    checkpoint_manager: CheckpointManager,
    update: bool = False,
) -> LoadResult:
    """Run the full Revolut Merchant extract: locations, customers, orders, disputes."""
    settings = _settings_from_env()
    if not settings:
        logger.info(_SKIP_MSG)
        return LoadResult(0, 0, 0)
    client = RevolutMerchantClient(settings)

    loc = sync_merchant_locations(session, checkpoint_manager, client, settings)
    cust = sync_merchant_customers(session, checkpoint_manager, client, settings)
    orders = sync_merchant_orders(session, checkpoint_manager, client, settings, update)
    disputes = sync_merchant_disputes(session, checkpoint_manager, client, settings, update)
    return _combine(loc, cust, orders, disputes)


def run_revolut_merchant_entity(
    session: Any,
    checkpoint_manager: CheckpointManager,
    entity_type: str,
    update: bool = False,
) -> LoadResult:
    """Run a single Revolut Merchant entity type."""
    settings = _settings_from_env()
    if not settings:
        logger.info("%s %s", _SKIP_MSG, entity_type)
        return LoadResult(0, 0, 0)
    client = RevolutMerchantClient(settings)

    if entity_type == "revolut_merchant_locations":
        return sync_merchant_locations(session, checkpoint_manager, client, settings)
    if entity_type == "revolut_merchant_customers":
        return sync_merchant_customers(session, checkpoint_manager, client, settings)
    if entity_type == "revolut_merchant_orders":
        return sync_merchant_orders(session, checkpoint_manager, client, settings, update)
    if entity_type == "revolut_merchant_disputes":
        return sync_merchant_disputes(session, checkpoint_manager, client, settings, update)
    if entity_type == "revolut_merchant_all":
        return run_revolut_merchant_extract(session, checkpoint_manager, update)
    raise ValueError(f"Unknown Revolut Merchant entity type: {entity_type}")
