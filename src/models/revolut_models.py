"""SQLAlchemy models for Revolut BI tables (see documentation/revolut/02-schema-design.md)."""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, Index, Text

from sqlalchemy.dialects.postgresql import JSONB

from src.models.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class RevolutAccount(Base):
    __tablename__ = "revolut_accounts"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=True)
    currency = Column(Text, nullable=True, index=True)
    state = Column(Text, nullable=True, index=True)
    balance = Column(BigInteger, nullable=True)
    balance_updated_at = Column(DateTime(timezone=True), nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class RevolutTransaction(Base):
    __tablename__ = "revolut_transactions"

    id = Column(Text, primary_key=True)
    account_id = Column(Text, nullable=True, index=True)
    type = Column(Text, nullable=True, index=True)
    state = Column(Text, nullable=True, index=True)
    amount = Column(BigInteger, nullable=True)
    currency = Column(Text, nullable=True)
    fee_amount = Column(BigInteger, nullable=True)
    fee_currency = Column(Text, nullable=True)
    bill_amount = Column(BigInteger, nullable=True)
    bill_currency = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    api_updated_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    merchant_name = Column(Text, nullable=True)
    merchant_city = Column(Text, nullable=True)
    merchant_category_code = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    counterparty_id = Column(Text, nullable=True)
    related_transaction_id = Column(Text, nullable=True, index=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_revolut_transactions_account_created", "account_id", "created_at"),)
