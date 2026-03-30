"""SQLAlchemy models for Stripe BI tables (see documentation/stripe/02-schema-design.md)."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, Text

from sqlalchemy.dialects.postgresql import JSONB

from src.models.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class StripeProduct(Base):
    __tablename__ = "stripe_products"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, server_default="true")
    default_price_id = Column(Text, nullable=True)
    created = Column(DateTime(timezone=True), nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StripePrice(Base):
    __tablename__ = "stripe_prices"

    id = Column(Text, primary_key=True)
    product_id = Column(Text, nullable=True, index=True)
    currency = Column(Text, nullable=False)
    unit_amount = Column(Integer, nullable=True)
    type = Column(Text, nullable=True)
    recurring_interval = Column(Text, nullable=True)
    recurring_interval_count = Column(Integer, nullable=True)
    active = Column(Boolean, nullable=False, server_default="true")
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StripeCoupon(Base):
    __tablename__ = "stripe_coupons"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=True)
    percent_off = Column(Float, nullable=True)
    amount_off = Column(Integer, nullable=True)
    currency = Column(Text, nullable=True)
    duration = Column(Text, nullable=True)
    duration_in_months = Column(Integer, nullable=True)
    valid = Column(Boolean, nullable=True)
    times_redeemed = Column(Integer, nullable=True)
    max_redemptions = Column(Integer, nullable=True)
    created = Column(DateTime(timezone=True), nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StripeSubscription(Base):
    __tablename__ = "stripe_subscriptions"

    id = Column(Text, primary_key=True)
    customer_id = Column(Text, nullable=True, index=True)
    status = Column(Text, nullable=True, index=True)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    created = Column(DateTime(timezone=True), nullable=True)
    default_payment_method = Column(Text, nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StripeInvoice(Base):
    __tablename__ = "stripe_invoices"

    id = Column(Text, primary_key=True)
    customer_id = Column(Text, nullable=True, index=True)
    subscription_id = Column(Text, nullable=True, index=True)
    status = Column(Text, nullable=True, index=True)
    currency = Column(Text, nullable=False)
    amount_due = Column(Integer, nullable=True)
    amount_paid = Column(Integer, nullable=True)
    total = Column(Integer, nullable=True)
    created = Column(DateTime(timezone=True), nullable=True)
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    charge_id = Column(Text, nullable=True)
    payment_intent_id = Column(Text, nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StripePaymentIntent(Base):
    __tablename__ = "stripe_payment_intents"

    id = Column(Text, primary_key=True)
    amount = Column(Integer, nullable=True)
    amount_received = Column(Integer, nullable=True)
    currency = Column(Text, nullable=False)
    created = Column(DateTime(timezone=True), nullable=True)
    customer_id = Column(Text, nullable=True, index=True)
    invoice_id = Column(Text, nullable=True)
    status = Column(Text, nullable=True, index=True)
    latest_charge_id = Column(Text, nullable=True, index=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StripeCharge(Base):
    __tablename__ = "stripe_charges"

    id = Column(Text, primary_key=True)
    amount = Column(Integer, nullable=True)
    amount_refunded = Column(Integer, nullable=True)
    currency = Column(Text, nullable=False)
    created = Column(DateTime(timezone=True), nullable=True)
    customer_id = Column(Text, nullable=True, index=True)
    invoice_id = Column(Text, nullable=True)
    payment_intent_id = Column(Text, nullable=True)
    balance_transaction_id = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    receipt_email = Column(Text, nullable=True)
    paid = Column(Boolean, nullable=True)
    refunded = Column(Boolean, nullable=True)
    status = Column(Text, nullable=True, index=True)
    failure_code = Column(Text, nullable=True)
    failure_message = Column(Text, nullable=True)
    livemode = Column(Boolean, nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StripeRefund(Base):
    __tablename__ = "stripe_refunds"

    id = Column(Text, primary_key=True)
    charge_id = Column(Text, nullable=True, index=True)
    payment_intent_id = Column(Text, nullable=True)
    amount = Column(Integer, nullable=True)
    currency = Column(Text, nullable=False)
    created = Column(DateTime(timezone=True), nullable=True)
    status = Column(Text, nullable=True, index=True)
    balance_transaction_id = Column(Text, nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StripeBalanceTransaction(Base):
    __tablename__ = "stripe_balance_transactions"

    id = Column(Text, primary_key=True)
    amount = Column(Integer, nullable=True)
    fee = Column(Integer, nullable=True)
    net = Column(Integer, nullable=True)
    currency = Column(Text, nullable=False)
    type = Column(Text, nullable=True, index=True)
    created = Column(DateTime(timezone=True), nullable=True)
    available_on = Column(DateTime(timezone=True), nullable=True, index=True)
    source_id = Column(Text, nullable=True, index=True)
    source_type = Column(Text, nullable=True)
    reporting_category = Column(Text, nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StripePayout(Base):
    __tablename__ = "stripe_payouts"

    id = Column(Text, primary_key=True)
    amount = Column(Integer, nullable=True)
    currency = Column(Text, nullable=False)
    status = Column(Text, nullable=True, index=True)
    arrival_date = Column(DateTime(timezone=True), nullable=True)
    created = Column(DateTime(timezone=True), nullable=True)
    description = Column(Text, nullable=True)
    destination = Column(Text, nullable=True)
    balance_transaction_id = Column(Text, nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StripeTransfer(Base):
    __tablename__ = "stripe_transfers"

    id = Column(Text, primary_key=True)
    amount = Column(Integer, nullable=True)
    currency = Column(Text, nullable=False)
    created = Column(DateTime(timezone=True), nullable=True)
    destination = Column(Text, nullable=True)
    status = Column(Text, nullable=True, index=True)
    description = Column(Text, nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
