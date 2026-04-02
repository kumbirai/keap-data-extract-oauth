"""Keap REST v2 multi-entity extract facade."""
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type

from sqlalchemy.orm import Session

from src.api.exceptions import (
    KeapBadRequestError,
    KeapForbiddenError,
    KeapNotFoundError,
    KeapServerError,
)
from src.auth.token_manager import TokenManager
from src.models.entity_models import Affiliate, Campaign, Contact
from src.models.keap_v2_models import (
    KeapV2AffiliateReferral,
    KeapV2Automation,
    KeapV2AutomationCategory,
    KeapV2CampaignGoal,
    KeapV2CampaignSequenceV2,
    KeapV2CategoryDiscount,
    KeapV2Company,
    KeapV2ContactLeadScore,
    KeapV2ContactLink,
    KeapV2ContactLinkType,
    KeapV2FreeTrialDiscount,
    KeapV2LeadSource,
    KeapV2LeadSourceCategory,
    KeapV2LeadSourceExpense,
    KeapV2LeadSourceRecurringExpense,
    KeapV2LeadSourceRecurringExpenseIncurred,
    KeapV2OrderTotalDiscount,
    KeapV2ProductDiscount,
    KeapV2ShippingDiscount,
)
from src.scripts.checkpoint_manager import CheckpointManager
from src.scripts.loaders.base_loader import LoadResult

from . import mappers
from .backoff import with_keap_backoff
from .checkpoint_state import fanout_state
from .client import KeapV2Client
from .constants import (
    KEAP_V2_AFFILIATE_REFERRALS,
    KEAP_V2_ALL,
    KEAP_V2_AUTOMATION_CATEGORIES,
    KEAP_V2_AUTOMATIONS,
    KEAP_V2_CAMPAIGN_GOALS,
    KEAP_V2_CAMPAIGN_SEQUENCES,
    KEAP_V2_CATEGORY_DISCOUNTS,
    KEAP_V2_COMPANIES,
    KEAP_V2_CONTACT_LEAD_SCORES,
    KEAP_V2_CONTACT_LINK_TYPES,
    KEAP_V2_CONTACT_LINKS,
    KEAP_V2_ENTITY_TYPES,
    KEAP_V2_FREE_TRIAL_DISCOUNTS,
    KEAP_V2_LEAD_SOURCE_CATEGORIES,
    KEAP_V2_LEAD_SOURCE_EXPENSES,
    KEAP_V2_LEAD_SOURCE_RECURRING_EXPENSE_INCURRED,
    KEAP_V2_LEAD_SOURCE_RECURRING_EXPENSES,
    KEAP_V2_LEAD_SOURCES,
    KEAP_V2_ORDER_TOTAL_DISCOUNTS,
    KEAP_V2_PRODUCT_DISCOUNTS,
    KEAP_V2_SHIPPING_DISCOUNTS,
)
from .repository import touch_now, upsert_composite_rows, upsert_simple_rows
from .settings import KeapV2ExtractSettings

logger = logging.getLogger(__name__)

ListCursorSpec = Tuple[str, str, Tuple[str, ...], Type[Any], Callable[[Dict[str, Any], Any], Optional[Dict[str, Any]]]]


LIST_CURSOR_SPECS: List[ListCursorSpec] = [
    (
        KEAP_V2_CONTACT_LINK_TYPES,
        "contacts/links/types",
        ("link_types", "linkTypes", "types", "contact_link_types"),
        KeapV2ContactLinkType,
        mappers.map_contact_link_type,
    ),
    (KEAP_V2_COMPANIES, "companies", ("companies",), KeapV2Company, mappers.map_company),
    (
        KEAP_V2_AUTOMATION_CATEGORIES,
        "automationCategory",
        ("automation_categories", "categories", "automationCategories"),
        KeapV2AutomationCategory,
        mappers.map_automation_category,
    ),
    (KEAP_V2_AUTOMATIONS, "automations", ("automations",), KeapV2Automation, mappers.map_automation),
    (
        KEAP_V2_CATEGORY_DISCOUNTS,
        "discounts/productCategories",
        ("discounts", "category_discounts", "product_category_discounts"),
        KeapV2CategoryDiscount,
        mappers.map_category_discount,
    ),
    (KEAP_V2_PRODUCT_DISCOUNTS, "discounts/products", ("discounts", "product_discounts"), KeapV2ProductDiscount, mappers.map_product_discount),
    (
        KEAP_V2_ORDER_TOTAL_DISCOUNTS,
        "discounts/orderTotals",
        ("discounts", "order_total_discounts"),
        KeapV2OrderTotalDiscount,
        mappers.map_generic_discount_row,
    ),
    (
        KEAP_V2_FREE_TRIAL_DISCOUNTS,
        "discounts/freeTrials",
        ("discounts", "free_trial_discounts"),
        KeapV2FreeTrialDiscount,
        mappers.map_generic_discount_row,
    ),
    (
        KEAP_V2_SHIPPING_DISCOUNTS,
        "discounts/shipping",
        ("discounts", "shipping_discounts"),
        KeapV2ShippingDiscount,
        mappers.map_generic_discount_row,
    ),
    (
        KEAP_V2_LEAD_SOURCE_CATEGORIES,
        "leadSourceCategories",
        ("lead_source_categories", "categories", "leadSourceCategories"),
        KeapV2LeadSourceCategory,
        mappers.map_lead_source_category,
    ),
    (KEAP_V2_LEAD_SOURCES, "leadSources", ("lead_sources", "leadSources"), KeapV2LeadSource, mappers.map_lead_source),
]

_SPEC_BY_ENTITY = {s[0]: s for s in LIST_CURSOR_SPECS}


def _delay(settings: KeapV2ExtractSettings) -> None:
    if settings.fan_out_delay_seconds > 0:
        time.sleep(settings.fan_out_delay_seconds)


def sync_list_cursor(
    session: Session,
    checkpoint_manager: CheckpointManager,
    client: KeapV2Client,
    settings: KeapV2ExtractSettings,
    entity_type: str,
    resource_path: str,
    item_keys: Tuple[str, ...],
    model_cls: Type[Any],
    map_row: Callable[[Dict[str, Any], Any], Optional[Dict[str, Any]]],
) -> LoadResult:
    now = touch_now()
    page_token: Optional[str] = checkpoint_manager.get_api_page_token(entity_type)
    total = checkpoint_manager.get_checkpoint(entity_type)

    try:
        while True:
            params: Dict[str, Any] = {"page_size": settings.page_size}
            if page_token:
                params["page_token"] = page_token

            data = with_keap_backoff(lambda: client.get(resource_path, params))
            items = mappers.extract_list_items(data, *item_keys)
            rows: List[Dict[str, Any]] = []
            for obj in items:
                if not isinstance(obj, dict):
                    continue
                row = map_row(obj, now)
                if row:
                    rows.append(row)
            if rows:
                upsert_simple_rows(session, model_cls, rows)
            total += len(items)
            page_token = data.get("next_page_token") or None
            checkpoint_manager.save_checkpoint(
                entity_type,
                total,
                completed=False,
                api_page_token=page_token,
            )
            if not page_token:
                break
        checkpoint_manager.save_checkpoint(
            entity_type,
            total,
            completed=True,
            api_page_token=None,
        )
        return LoadResult(total, total, 0)
    except KeapForbiddenError:
        logger.error("Keap v2 %s skipped after 403 (check OAuth scopes).", entity_type)
        return LoadResult(total, 0, 1)


def _fanout_save(
    checkpoint_manager: CheckpointManager,
    entity_type: str,
    total: int,
    *,
    last_parent_id: int = 0,
    current_parent_id: Optional[int] = None,
    page_token: Optional[str] = None,
    completed: bool = False,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    blob: Dict[str, Any] = {
        "in_progress": not completed,
        "last_parent_id": last_parent_id,
        "current_parent_id": current_parent_id,
        "page_token": page_token,
    }
    if extra:
        blob.update(extra)
    checkpoint_manager.save_checkpoint(
        entity_type,
        total,
        completed=completed,
        checkpoint_json=blob,
        api_page_token=None,
    )


def sync_contact_links(
    session: Session,
    checkpoint_manager: CheckpointManager,
    client: KeapV2Client,
    settings: KeapV2ExtractSettings,
) -> LoadResult:
    entity_type = KEAP_V2_CONTACT_LINKS
    state = fanout_state(checkpoint_manager.get_checkpoint_json(entity_type))
    last_done = int(state.get("last_parent_id") or 0)
    resume_parent = state.get("current_parent_id")
    resume_token: Optional[str] = state.get("page_token")
    total = checkpoint_manager.get_checkpoint(entity_type)
    now = touch_now()

    try:
        contact_ids: List[int] = [
            row[0] for row in session.query(Contact.id).filter(Contact.id > last_done).order_by(Contact.id).all()
        ]
        if resume_parent is not None:
            rp = int(resume_parent)
            if rp in contact_ids:
                contact_ids = [rp] + [c for c in contact_ids if c != rp]
            else:
                contact_ids.insert(0, rp)

        for cid in contact_ids:
            _delay(settings)
            inner_token: Optional[str] = None
            if resume_parent is not None and cid == int(resume_parent):
                inner_token = resume_token
                resume_parent = None
                resume_token = None
            while True:
                params: Dict[str, Any] = {"page_size": settings.page_size}
                if inner_token:
                    params["page_token"] = inner_token
                try:
                    data = with_keap_backoff(
                        lambda p=params, i=cid: client.get(f"contacts/{i}/links", p)
                    )
                except KeapNotFoundError:
                    logger.debug("Contact %s links not found; skipping.", cid)
                    inner_token = None
                    break
                except KeapBadRequestError:
                    logger.warning(
                        "Contact %s links: API returned 400 (invalid or unsupported id for v2); skipping.",
                        cid,
                    )
                    inner_token = None
                    break
                except KeapForbiddenError:
                    raise
                items = mappers.extract_list_items(data, "links", "linked_contacts", "contact_links")
                rows: List[Dict[str, Any]] = []
                for obj in items:
                    if not isinstance(obj, dict):
                        continue
                    row = mappers.map_contact_link(cid, obj, now)
                    if row:
                        rows.append(row)
                if rows:
                    upsert_composite_rows(
                        session,
                        KeapV2ContactLink,
                        rows,
                        ("contact_id", "linked_contact_id", "link_type_id"),
                    )
                total += len(items)
                inner_token = data.get("next_page_token") or None
                _fanout_save(
                    checkpoint_manager,
                    entity_type,
                    total,
                    last_parent_id=last_done,
                    current_parent_id=cid,
                    page_token=inner_token,
                    completed=False,
                )
                if not inner_token:
                    break
            last_done = cid
            _fanout_save(
                checkpoint_manager,
                entity_type,
                total,
                last_parent_id=last_done,
                current_parent_id=None,
                page_token=None,
                completed=False,
            )

        _fanout_save(
            checkpoint_manager,
            entity_type,
            total,
            last_parent_id=last_done,
            current_parent_id=None,
            page_token=None,
            completed=True,
        )
        return LoadResult(total, total, 0)
    except KeapForbiddenError:
        logger.error("Keap v2 %s skipped after 403 (check OAuth scopes).", entity_type)
        return LoadResult(total, 0, 1)


def sync_contact_lead_scores(
    session: Session,
    checkpoint_manager: CheckpointManager,
    client: KeapV2Client,
    settings: KeapV2ExtractSettings,
) -> LoadResult:
    entity_type = KEAP_V2_CONTACT_LEAD_SCORES
    state = fanout_state(checkpoint_manager.get_checkpoint_json(entity_type))
    last_done = int(state.get("last_parent_id") or 0)
    total = checkpoint_manager.get_checkpoint(entity_type)
    skipped = 0
    now = touch_now()
    try:
        q = session.query(Contact.id).filter(Contact.id > last_done).order_by(Contact.id)
        for (cid,) in q.all():
            _delay(settings)
            try:
                data = with_keap_backoff(
                    lambda i=cid: client.get(f"contacts/{i}/leadScore", {}),
                    max_attempts=settings.lead_score_max_attempts,
                )
            except (KeapNotFoundError, KeapBadRequestError):
                last_done = cid
                _fanout_save(
                    checkpoint_manager,
                    entity_type,
                    total,
                    last_parent_id=last_done,
                    completed=False,
                )
                continue
            except KeapServerError as e:
                logger.warning(
                    "Keap v2 leadScore skipped for contact %s after %s attempts (Keap 5xx): %s",
                    cid,
                    settings.lead_score_max_attempts,
                    e,
                )
                skipped += 1
                last_done = cid
                _fanout_save(
                    checkpoint_manager,
                    entity_type,
                    total,
                    last_parent_id=last_done,
                    completed=False,
                )
                continue
            row = mappers.map_contact_lead_score(cid, data, now)
            upsert_composite_rows(session, KeapV2ContactLeadScore, [row], ("contact_id",))
            total += 1
            last_done = cid
            _fanout_save(
                checkpoint_manager,
                entity_type,
                total,
                last_parent_id=last_done,
                completed=False,
            )
        _fanout_save(
            checkpoint_manager,
            entity_type,
            total,
            last_parent_id=last_done,
            completed=True,
        )
        if skipped:
            logger.info(
                "Keap v2 %s finished with %s contact(s) skipped (leadScore 5xx).",
                entity_type,
                skipped,
            )
        return LoadResult(total, total, skipped)
    except KeapForbiddenError:
        logger.error("Keap v2 %s skipped after 403 (check OAuth scopes).", entity_type)
        return LoadResult(total, 0, 1)


def _sync_campaign_children(
    session: Session,
    checkpoint_manager: CheckpointManager,
    client: KeapV2Client,
    settings: KeapV2ExtractSettings,
    entity_type: str,
    subpath: str,
    item_keys: Tuple[str, ...],
    model_cls: Type[Any],
    map_row: Callable[[int, Dict[str, Any], Any], Optional[Dict[str, Any]]],
    conflict_cols: Sequence[str],
) -> LoadResult:
    state = fanout_state(checkpoint_manager.get_checkpoint_json(entity_type))
    last_done = int(state.get("last_parent_id") or 0)
    resume_parent = state.get("current_parent_id")
    resume_token: Optional[str] = state.get("page_token")
    total = checkpoint_manager.get_checkpoint(entity_type)
    now = touch_now()

    campaigns: List[int] = [
        r[0] for r in session.query(Campaign.id).filter(Campaign.id > last_done).order_by(Campaign.id).all()
    ]
    if resume_parent is not None:
        rp = int(resume_parent)
        if rp in campaigns:
            campaigns = [rp] + [c for c in campaigns if c != rp]
        else:
            campaigns.insert(0, rp)

    try:
        for camp_id in campaigns:
            _delay(settings)
            inner_token: Optional[str] = None
            if resume_parent is not None and camp_id == int(resume_parent):
                inner_token = resume_token
                resume_parent = None
                resume_token = None
            while True:
                params: Dict[str, Any] = {"page_size": settings.page_size}
                if inner_token:
                    params["page_token"] = inner_token
                try:
                    data = with_keap_backoff(
                        lambda p=params, c=camp_id: client.get(f"campaigns/{c}/{subpath}", p)
                    )
                except (KeapNotFoundError, KeapBadRequestError):
                    inner_token = None
                    break
                items = mappers.extract_list_items(data, *item_keys)
                rows: List[Dict[str, Any]] = []
                for obj in items:
                    if not isinstance(obj, dict):
                        continue
                    row = map_row(camp_id, obj, now)
                    if row:
                        rows.append(row)
                if rows:
                    upsert_composite_rows(session, model_cls, rows, conflict_cols)
                total += len(items)
                inner_token = data.get("next_page_token") or None
                _fanout_save(
                    checkpoint_manager,
                    entity_type,
                    total,
                    last_parent_id=last_done,
                    current_parent_id=camp_id,
                    page_token=inner_token,
                    completed=False,
                )
                if not inner_token:
                    break
            last_done = camp_id
            _fanout_save(
                checkpoint_manager,
                entity_type,
                total,
                last_parent_id=last_done,
                current_parent_id=None,
                page_token=None,
                completed=False,
            )
        _fanout_save(
            checkpoint_manager,
            entity_type,
            total,
            last_parent_id=last_done,
            completed=True,
        )
        return LoadResult(total, total, 0)
    except KeapForbiddenError:
        logger.error("Keap v2 %s skipped after 403 (check OAuth scopes).", entity_type)
        return LoadResult(total, 0, 1)


def sync_affiliate_referrals(
    session: Session,
    checkpoint_manager: CheckpointManager,
    client: KeapV2Client,
    settings: KeapV2ExtractSettings,
) -> LoadResult:
    entity_type = KEAP_V2_AFFILIATE_REFERRALS
    state = fanout_state(checkpoint_manager.get_checkpoint_json(entity_type))
    last_done = int(state.get("last_parent_id") or 0)
    resume_parent = state.get("current_parent_id")
    resume_token: Optional[str] = state.get("page_token")
    total = checkpoint_manager.get_checkpoint(entity_type)
    now = touch_now()

    affiliates: List[int] = [
        r[0] for r in session.query(Affiliate.id).filter(Affiliate.id > last_done).order_by(Affiliate.id).all()
    ]
    if resume_parent is not None:
        rp = int(resume_parent)
        if rp in affiliates:
            affiliates = [rp] + [a for a in affiliates if a != rp]
        else:
            affiliates.insert(0, rp)

    try:
        for aid in affiliates:
            _delay(settings)
            inner_token: Optional[str] = None
            if resume_parent is not None and aid == int(resume_parent):
                inner_token = resume_token
                resume_parent = None
                resume_token = None
            while True:
                params: Dict[str, Any] = {"page_size": settings.page_size}
                if inner_token:
                    params["page_token"] = inner_token
                try:
                    data = with_keap_backoff(
                        lambda p=params, a=aid: client.get(f"affiliates/{a}/referrals", p)
                    )
                except (KeapNotFoundError, KeapBadRequestError):
                    inner_token = None
                    break
                items = mappers.extract_list_items(data, "referrals", "referral_list")
                rows: List[Dict[str, Any]] = []
                for obj in items:
                    if not isinstance(obj, dict):
                        continue
                    row = mappers.map_affiliate_referral(aid, obj, now)
                    if row:
                        rows.append(row)
                if rows:
                    upsert_simple_rows(session, KeapV2AffiliateReferral, rows)
                total += len(items)
                inner_token = data.get("next_page_token") or None
                _fanout_save(
                    checkpoint_manager,
                    entity_type,
                    total,
                    last_parent_id=last_done,
                    current_parent_id=aid,
                    page_token=inner_token,
                    completed=False,
                )
                if not inner_token:
                    break
            last_done = aid
            _fanout_save(
                checkpoint_manager,
                entity_type,
                total,
                last_parent_id=last_done,
                current_parent_id=None,
                page_token=None,
                completed=False,
            )
        _fanout_save(
            checkpoint_manager,
            entity_type,
            total,
            last_parent_id=last_done,
            completed=True,
        )
        return LoadResult(total, total, 0)
    except KeapForbiddenError:
        logger.error("Keap v2 %s skipped after 403 (check OAuth scopes).", entity_type)
        return LoadResult(total, 0, 1)


def sync_lead_source_expenses_tree(
    session: Session,
    checkpoint_manager: CheckpointManager,
    client: KeapV2Client,
    settings: KeapV2ExtractSettings,
) -> Tuple[LoadResult, LoadResult, LoadResult]:
    ls_ids = sorted(
        {r[0] for r in session.query(KeapV2LeadSource.id).all()},
        key=lambda x: str(x),
    )
    if not ls_ids:
        empty = LoadResult(0, 0, 0)
        for et in (
            KEAP_V2_LEAD_SOURCE_EXPENSES,
            KEAP_V2_LEAD_SOURCE_RECURRING_EXPENSES,
            KEAP_V2_LEAD_SOURCE_RECURRING_EXPENSE_INCURRED,
        ):
            checkpoint_manager.save_checkpoint(et, 0, completed=True, checkpoint_json={})
        return empty, empty, empty
    now = touch_now()
    r1 = _sync_per_lead_source_list(
        session,
        checkpoint_manager,
        client,
        settings,
        KEAP_V2_LEAD_SOURCE_EXPENSES,
        ls_ids,
        "expenses",
        ("expenses", "lead_source_expenses"),
        lambda ls_id, obj, n: mappers.map_lead_source_expense(ls_id, obj, n),
        KeapV2LeadSourceExpense,
        ("lead_source_id", "expense_id"),
    )
    r2 = _sync_per_lead_source_list(
        session,
        checkpoint_manager,
        client,
        settings,
        KEAP_V2_LEAD_SOURCE_RECURRING_EXPENSES,
        ls_ids,
        "recurringExpenses",
        ("recurring_expenses", "recurringExpenses"),
        lambda ls_id, obj, n: mappers.map_lead_source_recurring_expense(ls_id, obj, n),
        KeapV2LeadSourceRecurringExpense,
        ("lead_source_id", "recurring_expense_id"),
    )
    recurring_rows = session.query(
        KeapV2LeadSourceRecurringExpense.lead_source_id,
        KeapV2LeadSourceRecurringExpense.recurring_expense_id,
    ).all()
    r3 = _sync_recurring_incurred(
        session,
        checkpoint_manager,
        client,
        settings,
        recurring_rows,
        now,
    )
    return r1, r2, r3


def _sync_per_lead_source_list(
    session: Session,
    checkpoint_manager: CheckpointManager,
    client: KeapV2Client,
    settings: KeapV2ExtractSettings,
    entity_type: str,
    lead_source_ids: Sequence[str],
    path_suffix: str,
    item_keys: Tuple[str, ...],
    map_row: Callable[[str, Dict[str, Any], Any], Optional[Dict[str, Any]]],
    model_cls: Type[Any],
    conflict_cols: Sequence[str],
) -> LoadResult:
    state = fanout_state(checkpoint_manager.get_checkpoint_json(entity_type))
    completed_through = int(state.get("last_parent_idx") or -1)
    resume_ls = str(state["last_lead_source_id"]) if state.get("last_lead_source_id") else None
    resume_token: Optional[str] = state.get("page_token")
    total = checkpoint_manager.get_checkpoint(entity_type)
    now = touch_now()

    def save_ls_checkpoint(
        ls_idx: int,
        ls_id: str,
        token: Optional[str],
        done: bool,
    ) -> None:
        checkpoint_manager.save_checkpoint(
            entity_type,
            total,
            completed=done,
            checkpoint_json={
                "in_progress": not done,
                "last_parent_idx": ls_idx,
                "last_lead_source_id": ls_id,
                "page_token": token,
            },
        )

    try:
        if not lead_source_ids:
            checkpoint_manager.save_checkpoint(entity_type, total, completed=True, checkpoint_json={})
            return LoadResult(0, 0, 0)

        ids_ordered = sorted({str(x) for x in lead_source_ids})
        if resume_ls and resume_token and resume_ls in ids_ordered:
            ids_ordered = [resume_ls] + [x for x in ids_ordered if x != resume_ls]
        elif resume_ls and resume_token:
            ids_ordered.insert(0, resume_ls)

        for i, ls_id in enumerate(ids_ordered):
            inner_token: Optional[str] = None
            if resume_token and resume_ls == ls_id:
                inner_token = resume_token
                resume_token = None
                resume_ls = None
            elif i <= completed_through and inner_token is None:
                continue
            _delay(settings)
            while True:
                params: Dict[str, Any] = {"page_size": settings.page_size}
                if inner_token:
                    params["page_token"] = inner_token
                try:
                    data = with_keap_backoff(
                        lambda p=params, lid=ls_id: client.get(f"leadSources/{lid}/{path_suffix}", p)
                    )
                except (KeapNotFoundError, KeapBadRequestError):
                    inner_token = None
                    break
                items = mappers.extract_list_items(data, *item_keys)
                rows: List[Dict[str, Any]] = []
                for obj in items:
                    if not isinstance(obj, dict):
                        continue
                    row = map_row(ls_id, obj, now)
                    if row:
                        rows.append(row)
                if rows:
                    upsert_composite_rows(session, model_cls, rows, conflict_cols)
                total += len(items)
                inner_token = data.get("next_page_token") or None
                save_ls_checkpoint(i, ls_id, inner_token, False)
                if not inner_token:
                    break
            completed_through = i
            save_ls_checkpoint(i, ls_id, None, False)

        last_i = len(ids_ordered) - 1
        if last_i >= 0:
            save_ls_checkpoint(last_i, ids_ordered[last_i], None, True)
        return LoadResult(total, total, 0)
    except KeapForbiddenError:
        logger.error("Keap v2 %s skipped after 403 (check OAuth scopes).", entity_type)
        return LoadResult(total, 0, 1)


def _sync_recurring_incurred(
    session: Session,
    checkpoint_manager: CheckpointManager,
    client: KeapV2Client,
    settings: KeapV2ExtractSettings,
    recurring_pairs: Sequence[Tuple[str, str]],
    now: Any,
) -> LoadResult:
    entity_type = KEAP_V2_LEAD_SOURCE_RECURRING_EXPENSE_INCURRED
    state = fanout_state(checkpoint_manager.get_checkpoint_json(entity_type))
    start_idx = int(state.get("pair_idx") or 0)
    page_token: Optional[str] = state.get("page_token")
    total = checkpoint_manager.get_checkpoint(entity_type)

    def save_pair_checkpoint(idx: int, token: Optional[str], done: bool) -> None:
        checkpoint_manager.save_checkpoint(
            entity_type,
            total,
            completed=done,
            checkpoint_json={
                "in_progress": not done,
                "pair_idx": idx,
                "page_token": token,
            },
        )

    try:
        if not recurring_pairs:
            checkpoint_manager.save_checkpoint(entity_type, total, completed=True, checkpoint_json={})
            return LoadResult(0, 0, 0)

        for idx in range(start_idx, len(recurring_pairs)):
            ls_id, rec_id = recurring_pairs[idx]
            _delay(settings)
            inner_token: Optional[str] = page_token if idx == start_idx else None
            page_token = None
            while True:
                params: Dict[str, Any] = {"page_size": settings.page_size}
                if inner_token:
                    params["page_token"] = inner_token
                path = f"leadSources/{ls_id}/recurringExpenses/{rec_id}/expenses"
                try:
                    data = with_keap_backoff(lambda p=params: client.get(path, p))
                except (KeapNotFoundError, KeapBadRequestError):
                    inner_token = None
                    break
                items = mappers.extract_list_items(data, "expenses", "incurred_expenses")
                rows: List[Dict[str, Any]] = []
                for obj in items:
                    if not isinstance(obj, dict):
                        continue
                    row = mappers.map_lead_source_recurring_incurred(ls_id, rec_id, obj, now)
                    if row:
                        rows.append(row)
                if rows:
                    upsert_composite_rows(
                        session,
                        KeapV2LeadSourceRecurringExpenseIncurred,
                        rows,
                        ("lead_source_id", "recurring_expense_id", "incurred_id"),
                    )
                total += len(items)
                inner_token = data.get("next_page_token") or None
                save_pair_checkpoint(idx, inner_token, False)
                if not inner_token:
                    break
            save_pair_checkpoint(idx, None, False)

        save_pair_checkpoint(len(recurring_pairs), None, True)
        return LoadResult(total, total, 0)
    except KeapForbiddenError:
        logger.error("Keap v2 %s skipped after 403 (check OAuth scopes).", entity_type)
        return LoadResult(total, 0, 1)


def _merge_results(*results: LoadResult) -> LoadResult:
    t = s = f = 0
    for r in results:
        t += r.total_records
        s += r.success_count
        f += r.failed_count
    return LoadResult(t, s, f)


def run_keap_v2_extract(
    session: Session,
    checkpoint_manager: CheckpointManager,
    token_manager: TokenManager,
    update: bool = False,
) -> LoadResult:
    del update
    settings = KeapV2ExtractSettings.from_env()
    if not settings.enabled:
        logger.info("KEAP_V2_EXTRACT_ENABLED is off; skipping Keap v2 extract.")
        return LoadResult(0, 0, 0)

    client = KeapV2Client(token_manager, settings)
    try:
        total = LoadResult(0, 0, 0)
        for spec in LIST_CURSOR_SPECS:
            et, path, keys, model_cls, mapper = spec
            logger.info("Keap v2 sync %s", et)
            r = sync_list_cursor(session, checkpoint_manager, client, settings, et, path, keys, model_cls, mapper)
            total = _merge_results(total, r)

        logger.info("Keap v2 sync %s", KEAP_V2_LEAD_SOURCE_EXPENSES)
        r_exp, r_rec, r_inc = sync_lead_source_expenses_tree(
            session, checkpoint_manager, client, settings
        )
        total = _merge_results(total, r_exp, r_rec, r_inc)

        logger.info("Keap v2 sync %s", KEAP_V2_CONTACT_LINKS)
        total = _merge_results(total, sync_contact_links(session, checkpoint_manager, client, settings))

        logger.info("Keap v2 sync %s", KEAP_V2_CONTACT_LEAD_SCORES)
        total = _merge_results(
            total,
            sync_contact_lead_scores(session, checkpoint_manager, client, settings),
        )

        for et, subpath, keys, model_cls, mapper, conflicts in (
            (
                KEAP_V2_CAMPAIGN_GOALS,
                "goals",
                ("goals", "campaign_goals"),
                KeapV2CampaignGoal,
                mappers.map_campaign_goal,
                ("campaign_id", "goal_id"),
            ),
            (
                KEAP_V2_CAMPAIGN_SEQUENCES,
                "sequences",
                ("sequences", "campaign_sequences"),
                KeapV2CampaignSequenceV2,
                mappers.map_campaign_sequence_v2,
                ("campaign_id", "sequence_id"),
            ),
        ):
            logger.info("Keap v2 sync %s", et)
            r = _sync_campaign_children(
                session,
                checkpoint_manager,
                client,
                settings,
                et,
                subpath,
                keys,
                model_cls,
                mapper,
                conflicts,
            )
            total = _merge_results(total, r)

        logger.info("Keap v2 sync %s", KEAP_V2_AFFILIATE_REFERRALS)
        total = _merge_results(
            total,
            sync_affiliate_referrals(session, checkpoint_manager, client, settings),
        )

        return total
    finally:
        client.close()


def run_keap_v2_entity(
    session: Session,
    checkpoint_manager: CheckpointManager,
    token_manager: TokenManager,
    entity_type: str,
    update: bool = False,
) -> LoadResult:
    if entity_type == KEAP_V2_ALL:
        return run_keap_v2_extract(session, checkpoint_manager, token_manager, update)
    if entity_type not in KEAP_V2_ENTITY_TYPES:
        raise ValueError(f"Unknown Keap v2 entity type: {entity_type}")

    settings = KeapV2ExtractSettings.from_env()
    if not settings.enabled:
        logger.info("KEAP_V2_EXTRACT_ENABLED is off; skipping %s.", entity_type)
        return LoadResult(0, 0, 0)

    client = KeapV2Client(token_manager, settings)
    try:
        if entity_type in _SPEC_BY_ENTITY:
            et, path, keys, model_cls, mapper = _SPEC_BY_ENTITY[entity_type]
            return sync_list_cursor(
                session, checkpoint_manager, client, settings, et, path, keys, model_cls, mapper
            )
        if entity_type == KEAP_V2_CAMPAIGN_GOALS:
            return _sync_campaign_children(
                session,
                checkpoint_manager,
                client,
                settings,
                entity_type,
                "goals",
                ("goals", "campaign_goals"),
                KeapV2CampaignGoal,
                mappers.map_campaign_goal,
                ("campaign_id", "goal_id"),
            )
        if entity_type == KEAP_V2_CAMPAIGN_SEQUENCES:
            return _sync_campaign_children(
                session,
                checkpoint_manager,
                client,
                settings,
                entity_type,
                "sequences",
                ("sequences", "campaign_sequences"),
                KeapV2CampaignSequenceV2,
                mappers.map_campaign_sequence_v2,
                ("campaign_id", "sequence_id"),
            )
        if entity_type == KEAP_V2_LEAD_SOURCE_EXPENSES:
            ls_ids = sorted(
        {r[0] for r in session.query(KeapV2LeadSource.id).all()},
        key=lambda x: str(x),
    )
            return _sync_per_lead_source_list(
                session,
                checkpoint_manager,
                client,
                settings,
                entity_type,
                ls_ids,
                "expenses",
                ("expenses", "lead_source_expenses"),
                lambda ls_id, obj, n: mappers.map_lead_source_expense(ls_id, obj, n),
                KeapV2LeadSourceExpense,
                ("lead_source_id", "expense_id"),
            )
        if entity_type == KEAP_V2_LEAD_SOURCE_RECURRING_EXPENSES:
            ls_ids = sorted(
        {r[0] for r in session.query(KeapV2LeadSource.id).all()},
        key=lambda x: str(x),
    )
            return _sync_per_lead_source_list(
                session,
                checkpoint_manager,
                client,
                settings,
                entity_type,
                ls_ids,
                "recurringExpenses",
                ("recurring_expenses", "recurringExpenses"),
                lambda ls_id, obj, n: mappers.map_lead_source_recurring_expense(ls_id, obj, n),
                KeapV2LeadSourceRecurringExpense,
                ("lead_source_id", "recurring_expense_id"),
            )
        if entity_type == KEAP_V2_LEAD_SOURCE_RECURRING_EXPENSE_INCURRED:
            recurring_rows = session.query(
                KeapV2LeadSourceRecurringExpense.lead_source_id,
                KeapV2LeadSourceRecurringExpense.recurring_expense_id,
            ).all()
            return _sync_recurring_incurred(
                session,
                checkpoint_manager,
                client,
                settings,
                recurring_rows,
                touch_now(),
            )
        if entity_type == KEAP_V2_CONTACT_LINKS:
            return sync_contact_links(session, checkpoint_manager, client, settings)
        if entity_type == KEAP_V2_CONTACT_LEAD_SCORES:
            return sync_contact_lead_scores(session, checkpoint_manager, client, settings)
        if entity_type == KEAP_V2_AFFILIATE_REFERRALS:
            return sync_affiliate_referrals(session, checkpoint_manager, client, settings)
        raise ValueError(f"Unhandled Keap v2 entity type: {entity_type}")
    finally:
        client.close()
