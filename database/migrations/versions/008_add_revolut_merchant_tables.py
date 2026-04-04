"""add revolut merchant api tables

Revision ID: 008_revolut_merchant
Revises: 007_keap_v2_bi
Create Date: 2026-04-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "008_revolut_merchant"
down_revision = "007_keap_v2_bi"
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

    # ------------------------------------------------------------------
    # revolut_merchant_orders
    # ------------------------------------------------------------------
    if not insp.has_table("revolut_merchant_orders"):
        op.create_table(
            "revolut_merchant_orders",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("token", sa.Text(), nullable=True),
            sa.Column("type", sa.Text(), nullable=True),
            sa.Column("state", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("amount", sa.BigInteger(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=True),
            sa.Column("outstanding_amount", sa.BigInteger(), nullable=True),
            sa.Column("capture_mode", sa.Text(), nullable=True),
            sa.Column("cancel_authorised_only", sa.Boolean(), nullable=True),
            sa.Column("customer_id", sa.Text(), nullable=True),
            sa.Column("email", sa.Text(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("merchant_order_ext_ref", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at_etl", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    _ensure_index(bind, "revolut_merchant_orders", "ix_rmo_state", ["state"])
    _ensure_index(bind, "revolut_merchant_orders", "ix_rmo_created_at", ["created_at"])
    _ensure_index(bind, "revolut_merchant_orders", "ix_rmo_customer_id", ["customer_id"])
    _ensure_index(
        bind,
        "revolut_merchant_orders",
        "ix_rmo_currency_created",
        ["currency", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )

    # ------------------------------------------------------------------
    # revolut_merchant_order_payments
    # ------------------------------------------------------------------
    if not insp.has_table("revolut_merchant_order_payments"):
        op.create_table(
            "revolut_merchant_order_payments",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("order_id", sa.Text(), nullable=True),
            sa.Column("state", sa.Text(), nullable=True),
            sa.Column("amount", sa.BigInteger(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=True),
            sa.Column("payment_method_type", sa.Text(), nullable=True),
            sa.Column("card_bin", sa.Text(), nullable=True),
            sa.Column("card_last_four", sa.Text(), nullable=True),
            sa.Column("card_brand", sa.Text(), nullable=True),
            sa.Column("card_funding_type", sa.Text(), nullable=True),
            sa.Column("card_country", sa.Text(), nullable=True),
            sa.Column("arn", sa.Text(), nullable=True),
            sa.Column("bank_message", sa.Text(), nullable=True),
            sa.Column("decline_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at_etl", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    _ensure_index(bind, "revolut_merchant_order_payments", "ix_rmop_order_id", ["order_id"])
    _ensure_index(bind, "revolut_merchant_order_payments", "ix_rmop_state", ["state"])
    _ensure_index(bind, "revolut_merchant_order_payments", "ix_rmop_created_at", ["created_at"])

    # ------------------------------------------------------------------
    # revolut_merchant_customers
    # ------------------------------------------------------------------
    if not insp.has_table("revolut_merchant_customers"):
        op.create_table(
            "revolut_merchant_customers",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("email", sa.Text(), nullable=True),
            sa.Column("phone", sa.Text(), nullable=True),
            sa.Column("full_name", sa.Text(), nullable=True),
            sa.Column("business_name", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at_etl", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    _ensure_index(bind, "revolut_merchant_customers", "ix_rmc_email", ["email"])
    _ensure_index(bind, "revolut_merchant_customers", "ix_rmc_created_at", ["created_at"])

    # ------------------------------------------------------------------
    # revolut_merchant_payment_methods
    # ------------------------------------------------------------------
    if not insp.has_table("revolut_merchant_payment_methods"):
        op.create_table(
            "revolut_merchant_payment_methods",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("customer_id", sa.Text(), nullable=True),
            sa.Column("type", sa.Text(), nullable=True),
            sa.Column("card_bin", sa.Text(), nullable=True),
            sa.Column("card_last_four", sa.Text(), nullable=True),
            sa.Column("card_expiry_month", sa.Integer(), nullable=True),
            sa.Column("card_expiry_year", sa.Integer(), nullable=True),
            sa.Column("card_cardholder_name", sa.Text(), nullable=True),
            sa.Column("card_brand", sa.Text(), nullable=True),
            sa.Column("card_funding_type", sa.Text(), nullable=True),
            sa.Column("card_issuer", sa.Text(), nullable=True),
            sa.Column("billing_street_line_1", sa.Text(), nullable=True),
            sa.Column("billing_city", sa.Text(), nullable=True),
            sa.Column("billing_postcode", sa.Text(), nullable=True),
            sa.Column("billing_country", sa.Text(), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at_etl", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    _ensure_index(bind, "revolut_merchant_payment_methods", "ix_rmpm_customer_id", ["customer_id"])
    _ensure_index(bind, "revolut_merchant_payment_methods", "ix_rmpm_type", ["type"])
    _ensure_index(bind, "revolut_merchant_payment_methods", "ix_rmpm_card_brand", ["card_brand"])

    # ------------------------------------------------------------------
    # revolut_merchant_disputes
    # ------------------------------------------------------------------
    if not insp.has_table("revolut_merchant_disputes"):
        op.create_table(
            "revolut_merchant_disputes",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("order_id", sa.Text(), nullable=True),
            sa.Column("state", sa.Text(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("amount", sa.BigInteger(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at_etl", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    _ensure_index(bind, "revolut_merchant_disputes", "ix_rmd_state", ["state"])
    _ensure_index(bind, "revolut_merchant_disputes", "ix_rmd_order_id", ["order_id"])
    _ensure_index(bind, "revolut_merchant_disputes", "ix_rmd_created_at", ["created_at"])

    # ------------------------------------------------------------------
    # revolut_merchant_locations
    # ------------------------------------------------------------------
    if not insp.has_table("revolut_merchant_locations"):
        op.create_table(
            "revolut_merchant_locations",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=True),
            sa.Column("type", sa.Text(), nullable=True),
            sa.Column("address_line_1", sa.Text(), nullable=True),
            sa.Column("address_city", sa.Text(), nullable=True),
            sa.Column("address_country", sa.Text(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at_etl", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    _ensure_index(bind, "revolut_merchant_locations", "ix_rml_currency", ["currency"])
    _ensure_index(bind, "revolut_merchant_locations", "ix_rml_type", ["type"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    def drop_ix(table: str, name: str) -> None:
        if not insp.has_table(table):
            return
        existing = {ix["name"] for ix in insp.get_indexes(table)}
        if name in existing:
            op.drop_index(name, table_name=table)

    # Locations
    drop_ix("revolut_merchant_locations", "ix_rml_type")
    drop_ix("revolut_merchant_locations", "ix_rml_currency")
    if insp.has_table("revolut_merchant_locations"):
        op.drop_table("revolut_merchant_locations")

    # Disputes
    drop_ix("revolut_merchant_disputes", "ix_rmd_created_at")
    drop_ix("revolut_merchant_disputes", "ix_rmd_order_id")
    drop_ix("revolut_merchant_disputes", "ix_rmd_state")
    if insp.has_table("revolut_merchant_disputes"):
        op.drop_table("revolut_merchant_disputes")

    # Payment methods
    drop_ix("revolut_merchant_payment_methods", "ix_rmpm_card_brand")
    drop_ix("revolut_merchant_payment_methods", "ix_rmpm_type")
    drop_ix("revolut_merchant_payment_methods", "ix_rmpm_customer_id")
    if insp.has_table("revolut_merchant_payment_methods"):
        op.drop_table("revolut_merchant_payment_methods")

    # Customers
    drop_ix("revolut_merchant_customers", "ix_rmc_created_at")
    drop_ix("revolut_merchant_customers", "ix_rmc_email")
    if insp.has_table("revolut_merchant_customers"):
        op.drop_table("revolut_merchant_customers")

    # Order payments
    drop_ix("revolut_merchant_order_payments", "ix_rmop_created_at")
    drop_ix("revolut_merchant_order_payments", "ix_rmop_state")
    drop_ix("revolut_merchant_order_payments", "ix_rmop_order_id")
    if insp.has_table("revolut_merchant_order_payments"):
        op.drop_table("revolut_merchant_order_payments")

    # Orders
    drop_ix("revolut_merchant_orders", "ix_rmo_currency_created")
    drop_ix("revolut_merchant_orders", "ix_rmo_customer_id")
    drop_ix("revolut_merchant_orders", "ix_rmo_created_at")
    drop_ix("revolut_merchant_orders", "ix_rmo_state")
    if insp.has_table("revolut_merchant_orders"):
        op.drop_table("revolut_merchant_orders")
