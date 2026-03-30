"""Stripe multi-entity extract facade (documentation/stripe/03-extract-integration.md)."""
import logging
import os
from typing import Any, Callable, List, Optional, Tuple, Type

import stripe

from src.models.stripe_models import (
    StripeBalanceTransaction,
    StripeCharge,
    StripeCoupon,
    StripeInvoice,
    StripePaymentIntent,
    StripePayout,
    StripePrice,
    StripeProduct,
    StripeRefund,
    StripeSubscription,
    StripeTransfer,
)
from src.scripts.checkpoint_manager import CheckpointManager
from src.scripts.loaders.base_loader import LoadResult
from src.stripe import mappers
from src.stripe.constants import STRIPE_ENTITY_TYPES as _DECLARED_ENTITY_TYPES
from src.stripe.settings import StripeExtractSettings
from src.stripe.sync import retrieve_and_upsert, sync_stripe_entity

logger = logging.getLogger(__name__)

StripeEntitySpec = Tuple[str, Type[Any], Any, Callable[..., dict]]

STRIPE_ENTITY_SPECS: List[StripeEntitySpec] = [
    ("stripe_products", StripeProduct, stripe.Product, mappers.map_product),
    ("stripe_prices", StripePrice, stripe.Price, mappers.map_price),
    ("stripe_coupons", StripeCoupon, stripe.Coupon, mappers.map_coupon),
    ("stripe_subscriptions", StripeSubscription, stripe.Subscription, mappers.map_subscription),
    ("stripe_invoices", StripeInvoice, stripe.Invoice, mappers.map_invoice),
    ("stripe_payment_intents", StripePaymentIntent, stripe.PaymentIntent, mappers.map_payment_intent),
    ("stripe_charges", StripeCharge, stripe.Charge, mappers.map_charge),
    ("stripe_refunds", StripeRefund, stripe.Refund, mappers.map_refund),
    ("stripe_balance_transactions", StripeBalanceTransaction, stripe.BalanceTransaction, mappers.map_balance_transaction),
    ("stripe_payouts", StripePayout, stripe.Payout, mappers.map_payout),
    ("stripe_transfers", StripeTransfer, stripe.Transfer, mappers.map_transfer),
]

STRIPE_ENTITY_TYPES = [s[0] for s in STRIPE_ENTITY_SPECS]
if STRIPE_ENTITY_TYPES != _DECLARED_ENTITY_TYPES:
    raise RuntimeError("STRIPE_ENTITY_TYPES out of sync with STRIPE_ENTITY_SPECS")

_SPEC_BY_TYPE = {s[0]: s for s in STRIPE_ENTITY_SPECS}


def _configure_stripe(settings: StripeExtractSettings) -> None:
    stripe.api_key = settings.api_key
    if settings.api_version:
        stripe.api_version = settings.api_version


def _settings_from_env() -> Optional[StripeExtractSettings]:
    batch = int(os.getenv("BATCH_SIZE", "50"))
    return StripeExtractSettings.from_env(batch_size=batch)


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
    return total


def run_stripe_entity(
    session: Any,
    checkpoint_manager: CheckpointManager,
    entity_type: str,
    update: bool = False,
) -> LoadResult:
    settings = _settings_from_env()
    if not settings:
        raise RuntimeError(
            "STRIPE_API_KEY is not set. Configure it to load Stripe data, or omit --entity-type stripe_*."
        )
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
