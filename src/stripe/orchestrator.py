"""Stripe multi-entity extract facade (documentation/stripe/sprint-02/03-extract-integration.md)."""
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

import stripe

from src.models.stripe_models import (
    StripeBalanceTransaction,
    StripeCharge,
    StripeCoupon,
    StripeCreditNote,
    StripeCustomer,
    StripeDispute,
    StripeInvoice,
    StripeInvoiceLineItem,
    StripePaymentIntent,
    StripePayout,
    StripePrice,
    StripeProduct,
    StripePromotionCode,
    StripeRefund,
    StripeSubscription,
    StripeSubscriptionItem,
    StripeTransfer,
)
from src.scripts.checkpoint_manager import CheckpointManager
from src.scripts.loaders.base_loader import LoadResult
from src.stripe import mappers
from src.stripe.constants import (
    STRIPE_ALL_ENTITY_TYPE,
    STRIPE_CHILD_ENTITY_TYPES as _DECLARED_CHILD_TYPES,
    STRIPE_TOP_LEVEL_ENTITY_TYPES as _DECLARED_TOP_TYPES,
)
from src.stripe.settings import StripeExtractSettings
from src.stripe.sync import (
    query_invoice_parents_for_line_items,
    query_subscription_parents_for_items,
    retrieve_and_upsert,
    sync_stripe_child_entity,
    sync_stripe_entity,
)

logger = logging.getLogger(__name__)

StripeEntitySpec = Tuple[str, Type[Any], Any, Callable[..., dict]]

STRIPE_ENTITY_SPECS: List[StripeEntitySpec] = [
    ("stripe_products", StripeProduct, stripe.Product, mappers.map_product),
    ("stripe_prices", StripePrice, stripe.Price, mappers.map_price),
    ("stripe_coupons", StripeCoupon, stripe.Coupon, mappers.map_coupon),
    ("stripe_customers", StripeCustomer, stripe.Customer, mappers.map_customer),
    ("stripe_subscriptions", StripeSubscription, stripe.Subscription, mappers.map_subscription),
    ("stripe_invoices", StripeInvoice, stripe.Invoice, mappers.map_invoice),
    ("stripe_payment_intents", StripePaymentIntent, stripe.PaymentIntent, mappers.map_payment_intent),
    ("stripe_charges", StripeCharge, stripe.Charge, mappers.map_charge),
    ("stripe_disputes", StripeDispute, stripe.Dispute, mappers.map_dispute),
    ("stripe_promotion_codes", StripePromotionCode, stripe.PromotionCode, mappers.map_promotion_code),
    ("stripe_credit_notes", StripeCreditNote, stripe.CreditNote, mappers.map_credit_note),
    ("stripe_refunds", StripeRefund, stripe.Refund, mappers.map_refund),
    ("stripe_balance_transactions", StripeBalanceTransaction, stripe.BalanceTransaction, mappers.map_balance_transaction),
    ("stripe_payouts", StripePayout, stripe.Payout, mappers.map_payout),
    ("stripe_transfers", StripeTransfer, stripe.Transfer, mappers.map_transfer),
]

_STRIPE_TOP_TYPES = [s[0] for s in STRIPE_ENTITY_SPECS]
if _STRIPE_TOP_TYPES != _DECLARED_TOP_TYPES:
    raise RuntimeError("STRIPE_ENTITY_SPECS out of sync with STRIPE_TOP_LEVEL_ENTITY_TYPES")


def _invoice_lines_page(
    parent_id: str,
    limit: int,
    starting_after: Optional[str],
    stripe_account_id: Optional[str],
) -> Any:
    params: Dict[str, Any] = {"limit": limit}
    if starting_after:
        params["starting_after"] = starting_after
    if stripe_account_id:
        return stripe.Invoice.list_lines(parent_id, stripe_account=stripe_account_id, **params)
    return stripe.Invoice.list_lines(parent_id, **params)


def _subscription_items_page(
    parent_id: str,
    limit: int,
    starting_after: Optional[str],
    stripe_account_id: Optional[str],
) -> Any:
    params: Dict[str, Any] = {"subscription": parent_id, "limit": limit}
    if starting_after:
        params["starting_after"] = starting_after
    if stripe_account_id:
        return stripe.SubscriptionItem.list(stripe_account=stripe_account_id, **params)
    return stripe.SubscriptionItem.list(**params)


STRIPE_CHILD_SPECS: List[Dict[str, Any]] = [
    {
        "entity_type": "stripe_invoice_line_items",
        "child_model": StripeInvoiceLineItem,
        "query_parents": lambda sess, wm, acct: query_invoice_parents_for_line_items(
            sess, wm, acct, ("draft", "open")
        ),
        "list_page": _invoice_lines_page,
        "map_row": lambda obj, acct, now, sr, parent_id: mappers.map_invoice_line_item(
            obj, acct, now, sr, invoice_id=parent_id
        ),
    },
    {
        "entity_type": "stripe_subscription_items",
        "child_model": StripeSubscriptionItem,
        "query_parents": lambda sess, wm, acct: query_subscription_parents_for_items(
            sess, wm, acct, ("active", "past_due", "trialing")
        ),
        "list_page": _subscription_items_page,
        "map_row": lambda obj, acct, now, sr, parent_id: mappers.map_subscription_item(
            obj, acct, now, sr, subscription_id=parent_id
        ),
    },
]

_CHILD_TYPES = [s["entity_type"] for s in STRIPE_CHILD_SPECS]
if _CHILD_TYPES != _DECLARED_CHILD_TYPES:
    raise RuntimeError("STRIPE_CHILD_SPECS out of sync with STRIPE_CHILD_ENTITY_TYPES")

_SPEC_BY_TYPE = {s[0]: s for s in STRIPE_ENTITY_SPECS}
_CHILD_SPEC_BY_TYPE = {s["entity_type"]: s for s in STRIPE_CHILD_SPECS}

CHILD_TYPES_NO_SINGLE_RETRIEVE = frozenset(_CHILD_TYPES)


def _configure_stripe(settings: StripeExtractSettings) -> None:
    stripe.api_key = settings.api_key
    if settings.api_version:
        stripe.api_version = settings.api_version


def _settings_from_env() -> Optional[StripeExtractSettings]:
    import os

    batch = int(os.getenv("BATCH_SIZE", "50"))
    return StripeExtractSettings.from_env(batch_size=batch)


def _run_child_specs(
    session: Any,
    checkpoint_manager: CheckpointManager,
    settings: StripeExtractSettings,
    update: bool,
) -> LoadResult:
    total = LoadResult(0, 0, 0)
    for account_id in settings.account_ids:
        for spec in STRIPE_CHILD_SPECS:
            et = spec["entity_type"]
            logger.info("Stripe child sync %s (account=%s)", et, account_id or "platform")
            r = sync_stripe_child_entity(
                session,
                checkpoint_manager,
                settings,
                et,
                spec["query_parents"],
                spec["list_page"],
                spec["child_model"],
                spec["map_row"],
                account_id,
                update,
            )
            total = LoadResult(
                total.total_records + r.total_records,
                total.success_count + r.success_count,
                total.failed_count + r.failed_count,
            )
    return total


def run_stripe_extract(
    session: Any,
    checkpoint_manager: CheckpointManager,
    update: bool = False,
) -> LoadResult:
    settings = _settings_from_env()
    if not settings:
        logger.info("STRIPE_API_KEY not set; skipping Stripe extract.")
        return LoadResult(0, 0, 0)
    _configure_stripe(settings)
    total = LoadResult(0, 0, 0)
    for account_id in settings.account_ids:
        for spec in STRIPE_ENTITY_SPECS:
            entity_type, model_cls, resource, mapper = spec
            logger.info("Stripe sync %s (account=%s)", entity_type, account_id or "platform")
            r = sync_stripe_entity(
                session,
                checkpoint_manager,
                settings,
                entity_type,
                model_cls,
                resource.list,
                mapper,
                account_id,
                update,
            )
            total = LoadResult(
                total.total_records + r.total_records,
                total.success_count + r.success_count,
                total.failed_count + r.failed_count,
            )
    child = _run_child_specs(session, checkpoint_manager, settings, update)
    return LoadResult(
        total.total_records + child.total_records,
        total.success_count + child.success_count,
        total.failed_count + child.failed_count,
    )


def run_stripe_entity(
    session: Any,
    checkpoint_manager: CheckpointManager,
    entity_type: str,
    update: bool = False,
) -> LoadResult:
    if entity_type == STRIPE_ALL_ENTITY_TYPE:
        return run_stripe_extract(session, checkpoint_manager, update)
    settings = _settings_from_env()
    if not settings:
        raise RuntimeError(
            "STRIPE_API_KEY is not set. Configure it to load Stripe data, or omit --entity-type stripe_*."
        )
    if entity_type in _CHILD_SPEC_BY_TYPE:
        _configure_stripe(settings)
        spec = _CHILD_SPEC_BY_TYPE[entity_type]
        total = LoadResult(0, 0, 0)
        for account_id in settings.account_ids:
            logger.info("Stripe child sync %s (account=%s)", entity_type, account_id or "platform")
            r = sync_stripe_child_entity(
                session,
                checkpoint_manager,
                settings,
                entity_type,
                spec["query_parents"],
                spec["list_page"],
                spec["child_model"],
                spec["map_row"],
                account_id,
                update,
            )
            total = LoadResult(
                total.total_records + r.total_records,
                total.success_count + r.success_count,
                total.failed_count + r.failed_count,
            )
        return total
    if entity_type not in _SPEC_BY_TYPE:
        raise ValueError(f"Unknown Stripe entity type: {entity_type}")
    _configure_stripe(settings)
    _, model_cls, resource, mapper = _SPEC_BY_TYPE[entity_type]
    total = LoadResult(0, 0, 0)
    for account_id in settings.account_ids:
        logger.info("Stripe sync %s (account=%s)", entity_type, account_id or "platform")
        r = sync_stripe_entity(
            session,
            checkpoint_manager,
            settings,
            entity_type,
            model_cls,
            resource.list,
            mapper,
            account_id,
            update,
        )
        total = LoadResult(
            total.total_records + r.total_records,
            total.success_count + r.success_count,
            total.failed_count + r.failed_count,
        )
    return total


def run_stripe_object_by_id(
    session: Any,
    entity_type: str,
    object_id: str,
) -> LoadResult:
    if entity_type == STRIPE_ALL_ENTITY_TYPE:
        raise ValueError(f"--stripe-object-id is not valid for {STRIPE_ALL_ENTITY_TYPE}")
    if entity_type in CHILD_TYPES_NO_SINGLE_RETRIEVE:
        raise ValueError(
            f"--stripe-object-id is not supported for {entity_type}; re-run the parent entity then the child extract."
        )
    settings = _settings_from_env()
    if not settings:
        raise RuntimeError("STRIPE_API_KEY is not set.")
    if entity_type not in _SPEC_BY_TYPE:
        raise ValueError(f"Unknown Stripe entity type: {entity_type}")
    _configure_stripe(settings)
    _, model_cls, resource, mapper = _SPEC_BY_TYPE[entity_type]
    last_error: Optional[Exception] = None
    for account_id in settings.account_ids:
        try:
            retrieve_and_upsert(
                session,
                settings,
                model_cls,
                resource.retrieve,
                mapper,
                object_id,
                account_id,
            )
            return LoadResult(1, 1, 0)
        except stripe.error.InvalidRequestError as e:
            last_error = e
            continue
    if last_error:
        raise RuntimeError(f"Could not retrieve {entity_type} id={object_id}: {last_error}") from last_error
    raise RuntimeError(f"Could not retrieve {entity_type} id={object_id} on any configured account.")
