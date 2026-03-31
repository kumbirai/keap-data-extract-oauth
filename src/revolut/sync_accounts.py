"""Load Revolut accounts into revolut_accounts."""
import logging
from typing import Any, List, Optional, Set, Tuple

from src.database.batch_upsert import touch_now, upsert_rows
from src.models.revolut_models import RevolutAccount
from src.revolut.client import RevolutClient
from src.revolut.mappers import map_account
from src.revolut.settings import RevolutExtractSettings
from src.scripts.checkpoint_manager import CheckpointManager
from src.scripts.loaders.base_loader import LoadResult

logger = logging.getLogger(__name__)

REVOLUT_ACCOUNTS_ENTITY = "revolut_accounts"


def filtered_revolut_account_ids(raw_list: Any, allow: Optional[Set[str]]) -> List[str]:
    """Account UUIDs from a Revolut list-accounts response after allowlist (stable API order)."""
    ids: List[str] = []
    if not isinstance(raw_list, list):
        return ids
    for item in raw_list:
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


def sync_revolut_accounts(
    session: Any,
    checkpoint_manager: CheckpointManager,
    client: RevolutClient,
    settings: RevolutExtractSettings,
) -> Tuple[LoadResult, List[str]]:
    now = touch_now()
    total = 0
    success = 0
    failed = 0
    try:
        raw_list = client.list_accounts()
    except Exception as e:
        logger.error("Revolut list accounts failed: %s", e, exc_info=True)
        return LoadResult(0, 0, 1), []

    allow = settings.account_allowlist
    account_ids = filtered_revolut_account_ids(raw_list, allow)
    batch: List[dict] = []
    for item in raw_list:
        if not isinstance(item, dict):
            failed += 1
            continue
        aid = item.get("id")
        if aid is None:
            failed += 1
            continue
        sid = str(aid)
        if allow is not None and sid not in allow:
            continue
        total += 1
        try:
            batch.append(map_account(item, now, settings.store_raw_payload))
        except Exception as e:
            failed += 1
            logger.error("Revolut account map failed: %s", e, exc_info=True)

    if batch:
        try:
            upsert_rows(session, RevolutAccount, batch)
            success += len(batch)
        except Exception as e:
            failed += len(batch)
            logger.error("Revolut account upsert failed: %s", e, exc_info=True)

    checkpoint_manager.save_checkpoint(
        entity_type=REVOLUT_ACCOUNTS_ENTITY,
        total_records_processed=success,
        api_offset=0,
        completed=True,
        checkpoint_json={"last_run_at": now.isoformat().replace("+00:00", "Z")},
    )
    return LoadResult(total, success, failed), account_ids
