"""add revolut bi tables

Revision ID: 005_revolut_bi
Revises: 004_checkpoint_json
Create Date: 2026-03-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "005_revolut_bi"
down_revision = "004_checkpoint_json"
branch_labels = None
depends_on = None


def _ensure_index(bind, table: str, name: str, columns: list, **kw) -> None:
    insp = inspect(bind)
    if not insp.has_table(table):
        return
    existing = {ix["name"] for ix in insp.get_indexes(table)}
    if name in existing:
        return
    op.create_index(name, table, columns, **kw)


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if not insp.has_table("revolut_accounts"):
        op.create_table(
            "revolut_accounts",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=True),
            sa.Column("state", sa.Text(), nullable=True),
            sa.Column("balance", sa.BigInteger(), nullable=True),
            sa.Column("balance_updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if not insp.has_table("revolut_transactions"):
        op.create_table(
            "revolut_transactions",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("account_id", sa.Text(), nullable=True),
            sa.Column("type", sa.Text(), nullable=True),
            sa.Column("state", sa.Text(), nullable=True),
            sa.Column("amount", sa.BigInteger(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=True),
            sa.Column("fee_amount", sa.BigInteger(), nullable=True),
            sa.Column("fee_currency", sa.Text(), nullable=True),
            sa.Column("bill_amount", sa.BigInteger(), nullable=True),
            sa.Column("bill_currency", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("api_updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("merchant_name", sa.Text(), nullable=True),
            sa.Column("merchant_city", sa.Text(), nullable=True),
            sa.Column("merchant_category_code", sa.Text(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("counterparty_id", sa.Text(), nullable=True),
            sa.Column("related_transaction_id", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    _ensure_index(bind, "revolut_accounts", "ix_revolut_accounts_currency", ["currency"])
    _ensure_index(bind, "revolut_accounts", "ix_revolut_accounts_state", ["state"])

    _ensure_index(bind, "revolut_transactions", "ix_revolut_transactions_account_id", ["account_id"])
    _ensure_index(bind, "revolut_transactions", "ix_revolut_transactions_type", ["type"])
    _ensure_index(bind, "revolut_transactions", "ix_revolut_transactions_state", ["state"])
    _ensure_index(bind, "revolut_transactions", "ix_revolut_transactions_completed_at", ["completed_at"])
    _ensure_index(
        bind,
        "revolut_transactions",
        "ix_revolut_transactions_related_transaction_id",
        ["related_transaction_id"],
    )
    _ensure_index(
        bind,
        "revolut_transactions",
        "ix_revolut_transactions_account_created",
        ["account_id", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    def drop_ix(table: str, name: str) -> None:
        if not insp.has_table(table):
            return
        existing = {ix["name"] for ix in insp.get_indexes(table)}
        if name in existing:
            op.drop_index(name, table_name=table)

    drop_ix("revolut_transactions", "ix_revolut_transactions_account_created")
    drop_ix("revolut_transactions", "ix_revolut_transactions_related_transaction_id")
    drop_ix("revolut_transactions", "ix_revolut_transactions_completed_at")
    drop_ix("revolut_transactions", "ix_revolut_transactions_state")
    drop_ix("revolut_transactions", "ix_revolut_transactions_type")
    drop_ix("revolut_transactions", "ix_revolut_transactions_account_id")
    drop_ix("revolut_accounts", "ix_revolut_accounts_state")
    drop_ix("revolut_accounts", "ix_revolut_accounts_currency")

    if insp.has_table("revolut_transactions"):
        op.drop_table("revolut_transactions")
    if insp.has_table("revolut_accounts"):
        op.drop_table("revolut_accounts")
