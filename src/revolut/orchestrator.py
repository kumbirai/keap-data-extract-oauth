"""Revolut extract facade (documentation/revolut/03-extract-integration.md)."""
import logging
from typing import Any, List, Optional

from src.revolut.client import RevolutClient
from src.revolut.settings import RevolutExtractSettings
from src.revolut.sync_accounts import sync_revolut_accounts
from src.revolut.sync_transactions import sync_revolut_transactions_for_accounts
from src.scripts.checkpoint_manager import CheckpointManager
from src.scripts.loaders.base_loader import LoadResult

logger = logging.getLogger(__name__)


def _settings_from_env() -> Optional[RevolutExtractSettings]:
    return RevolutExtractSettings.from_env()


def _account_ids_for_sync(client: RevolutClient, settings: RevolutExtractSettings) -> List[str]:
    raw = client.list_accounts()
    ids: List[str] = []
    allow = settings.account_allowlist
    for item in raw:
        if not isinstance(item, dict):
            continue
        aid = item.get("id")
        if aid is None:
            continue
        sid = str(aid)
        if allow is not None and sid not in allow:
            continue
        ids.append(sid)
    return ids


def run_revolut_extract(
    session: Any,
    checkpoint_manager: CheckpointManager,
    update: bool = False,
) -> LoadResult:
    settings = _settings_from_env()
    if not settings:
        logger.info(
            "Revolut extract skipped: set REVOLUT_CLIENT_ID, REVOLUT_PRIVATE_KEY_PATH, "
            "REVOLUT_JWT_KID, and REVOLUT_REFRESH_TOKEN or REVOLUT_AUTHORIZATION_CODE."
        )
        return LoadResult(0, 0, 0)
    client = RevolutClient(settings)
    acc = sync_revolut_accounts(session, checkpoint_manager, client, settings)
    try:
        account_ids = _account_ids_for_sync(client, settings)
    except Exception as e:
        logger.error("Revolut failed to list accounts for transaction sync: %s", e, exc_info=True)
        return LoadResult(
            acc.total_records,
            acc.success_count,
            acc.failed_count + 1,
        )
    txn = sync_revolut_transactions_for_accounts(
        session, checkpoint_manager, client, settings, account_ids, update
    )
    return LoadResult(
        acc.total_records + txn.total_records,
        acc.success_count + txn.success_count,
        acc.failed_count + txn.failed_count,
    )


def run_revolut_entity(
    session: Any,
    checkpoint_manager: CheckpointManager,
    entity_type: str,
    update: bool = False,
) -> LoadResult:
    settings = _settings_from_env()
    if not settings:
        raise RuntimeError(
            "Revolut is not configured. Set REVOLUT_CLIENT_ID, REVOLUT_PRIVATE_KEY_PATH, "
            "REVOLUT_JWT_KID, and REVOLUT_REFRESH_TOKEN or REVOLUT_AUTHORIZATION_CODE."
        )
    client = RevolutClient(settings)
    if entity_type == "revolut_accounts":
        return sync_revolut_accounts(session, checkpoint_manager, client, settings)
    if entity_type in ("revolut_transactions", "revolut_all"):
        if entity_type == "revolut_all":
            acc = sync_revolut_accounts(session, checkpoint_manager, client, settings)
            account_ids = _account_ids_for_sync(client, settings)
            txn = sync_revolut_transactions_for_accounts(
                session, checkpoint_manager, client, settings, account_ids, update
            )
            return LoadResult(
                acc.total_records + txn.total_records,
                acc.success_count + txn.success_count,
                acc.failed_count + txn.failed_count,
            )
        account_ids = _account_ids_for_sync(client, settings)
        return sync_revolut_transactions_for_accounts(
            session, checkpoint_manager, client, settings, account_ids, update
        )
    raise ValueError(f"Unknown Revolut entity type: {entity_type}")
