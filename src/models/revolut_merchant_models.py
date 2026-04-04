"""SQLAlchemy models for Revolut Merchant API BI tables (see documentation/revolut/sprint-02/02-schema-design.md)."""
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB

from src.models.base import Base


class RevolutMerchantOrder(Base):
    __tablename__ = "revolut_merchant_orders"

    id = Column(Text, primary_key=True)
    token = Column(Text, nullable=True)
    type = Column(Text, nullable=True)
    state = Column(Text, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=True, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    amount = Column(BigInteger, nullable=True)
    currency = Column(Text, nullable=True)
    outstanding_amount = Column(BigInteger, nullable=True)
    capture_mode = Column(Text, nullable=True)
    cancel_authorised_only = Column(Boolean, nullable=True)
    customer_id = Column(Text, nullable=True, index=True)
    email = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    merchant_order_ext_ref = Column(Text, nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=False)
    updated_at_etl = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index(
            "ix_revolut_merchant_orders_currency_created",
            "currency",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
    )


class RevolutMerchantOrderPayment(Base):
    __tablename__ = "revolut_merchant_order_payments"

    id = Column(Text, primary_key=True)
    order_id = Column(Text, nullable=True, index=True)
    state = Column(Text, nullable=True, index=True)
    amount = Column(BigInteger, nullable=True)
    currency = Column(Text, nullable=True)
    payment_method_type = Column(Text, nullable=True)
    card_bin = Column(Text, nullable=True)
    card_last_four = Column(Text, nullable=True)
    card_brand = Column(Text, nullable=True)
    card_funding_type = Column(Text, nullable=True)
    card_country = Column(Text, nullable=True)
    arn = Column(Text, nullable=True)
    bank_message = Column(Text, nullable=True)
    decline_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True, index=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=False)
    updated_at_etl = Column(DateTime(timezone=True), nullable=False)


class RevolutMerchantCustomer(Base):
    __tablename__ = "revolut_merchant_customers"

    id = Column(Text, primary_key=True)
    email = Column(Text, nullable=True, index=True)
    phone = Column(Text, nullable=True)
    full_name = Column(Text, nullable=True)
    business_name = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=False)
    updated_at_etl = Column(DateTime(timezone=True), nullable=False)


class RevolutMerchantPaymentMethod(Base):
    __tablename__ = "revolut_merchant_payment_methods"

    id = Column(Text, primary_key=True)
    customer_id = Column(Text, nullable=True, index=True)
    type = Column(Text, nullable=True, index=True)
    card_bin = Column(Text, nullable=True)
    card_last_four = Column(Text, nullable=True)
    card_expiry_month = Column(Integer, nullable=True)
    card_expiry_year = Column(Integer, nullable=True)
    card_cardholder_name = Column(Text, nullable=True)
    card_brand = Column(Text, nullable=True, index=True)
    card_funding_type = Column(Text, nullable=True)
    card_issuer = Column(Text, nullable=True)
    billing_street_line_1 = Column(Text, nullable=True)
    billing_city = Column(Text, nullable=True)
    billing_postcode = Column(Text, nullable=True)
    billing_country = Column(Text, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=False)
    updated_at_etl = Column(DateTime(timezone=True), nullable=False)


class RevolutMerchantDispute(Base):
    __tablename__ = "revolut_merchant_disputes"

    id = Column(Text, primary_key=True)
    order_id = Column(Text, nullable=True, index=True)
    state = Column(Text, nullable=True, index=True)
    reason = Column(Text, nullable=True)
    amount = Column(BigInteger, nullable=True)
    currency = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=False)
    updated_at_etl = Column(DateTime(timezone=True), nullable=False)


class RevolutMerchantLocation(Base):
    __tablename__ = "revolut_merchant_locations"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=True)
    type = Column(Text, nullable=True, index=True)
    address_line_1 = Column(Text, nullable=True)
    address_city = Column(Text, nullable=True)
    address_country = Column(Text, nullable=True)
    currency = Column(Text, nullable=True, index=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=False)
    updated_at_etl = Column(DateTime(timezone=True), nullable=False)
