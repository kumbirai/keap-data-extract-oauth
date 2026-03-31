"""add stripe bi tables

Revision ID: 003_stripe_bi
Revises: 002_extraction_state
Create Date: 2026-03-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "003_stripe_bi"
down_revision = "002_extraction_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if not insp.has_table("stripe_products"):
        op.create_table(
            "stripe_products",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
            sa.Column("default_price_id", sa.Text(), nullable=True),
            sa.Column("created", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not insp.has_table("stripe_prices"):
        op.create_table(
            "stripe_prices",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("product_id", sa.Text(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=False),
            sa.Column("unit_amount", sa.Integer(), nullable=True),
            sa.Column("type", sa.Text(), nullable=True),
            sa.Column("recurring_interval", sa.Text(), nullable=True),
            sa.Column("recurring_interval_count", sa.Integer(), nullable=True),
            sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not insp.has_table("stripe_coupons"):
        op.create_table(
            "stripe_coupons",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=True),
            sa.Column("percent_off", sa.Float(), nullable=True),
            sa.Column("amount_off", sa.Integer(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=True),
            sa.Column("duration", sa.Text(), nullable=True),
            sa.Column("duration_in_months", sa.Integer(), nullable=True),
            sa.Column("valid", sa.Boolean(), nullable=True),
            sa.Column("times_redeemed", sa.Integer(), nullable=True),
            sa.Column("max_redemptions", sa.Integer(), nullable=True),
            sa.Column("created", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not insp.has_table("stripe_subscriptions"):
        op.create_table(
            "stripe_subscriptions",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("customer_id", sa.Text(), nullable=True),
            sa.Column("status", sa.Text(), nullable=True),
            sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
            sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancel_at_period_end", sa.Boolean(), nullable=True),
            sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created", sa.DateTime(timezone=True), nullable=True),
            sa.Column("default_payment_method", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not insp.has_table("stripe_invoices"):
        op.create_table(
            "stripe_invoices",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("customer_id", sa.Text(), nullable=True),
            sa.Column("subscription_id", sa.Text(), nullable=True),
            sa.Column("status", sa.Text(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=False),
            sa.Column("amount_due", sa.Integer(), nullable=True),
            sa.Column("amount_paid", sa.Integer(), nullable=True),
            sa.Column("total", sa.Integer(), nullable=True),
            sa.Column("created", sa.DateTime(timezone=True), nullable=True),
            sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
            sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("charge_id", sa.Text(), nullable=True),
            sa.Column("payment_intent_id", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not insp.has_table("stripe_payment_intents"):
        op.create_table(
            "stripe_payment_intents",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=True),
            sa.Column("amount_received", sa.Integer(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=False),
            sa.Column("created", sa.DateTime(timezone=True), nullable=True),
            sa.Column("customer_id", sa.Text(), nullable=True),
            sa.Column("invoice_id", sa.Text(), nullable=True),
            sa.Column("status", sa.Text(), nullable=True),
            sa.Column("latest_charge_id", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not insp.has_table("stripe_charges"):
        op.create_table(
            "stripe_charges",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=True),
            sa.Column("amount_refunded", sa.Integer(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=False),
            sa.Column("created", sa.DateTime(timezone=True), nullable=True),
            sa.Column("customer_id", sa.Text(), nullable=True),
            sa.Column("invoice_id", sa.Text(), nullable=True),
            sa.Column("payment_intent_id", sa.Text(), nullable=True),
            sa.Column("balance_transaction_id", sa.Text(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("receipt_email", sa.Text(), nullable=True),
            sa.Column("paid", sa.Boolean(), nullable=True),
            sa.Column("refunded", sa.Boolean(), nullable=True),
            sa.Column("status", sa.Text(), nullable=True),
            sa.Column("failure_code", sa.Text(), nullable=True),
            sa.Column("failure_message", sa.Text(), nullable=True),
            sa.Column("livemode", sa.Boolean(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not insp.has_table("stripe_refunds"):
        op.create_table(
            "stripe_refunds",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("charge_id", sa.Text(), nullable=True),
            sa.Column("payment_intent_id", sa.Text(), nullable=True),
            sa.Column("amount", sa.Integer(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=False),
            sa.Column("created", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.Text(), nullable=True),
            sa.Column("balance_transaction_id", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not insp.has_table("stripe_balance_transactions"):
        op.create_table(
            "stripe_balance_transactions",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=True),
            sa.Column("fee", sa.Integer(), nullable=True),
            sa.Column("net", sa.Integer(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=False),
            sa.Column("type", sa.Text(), nullable=True),
            sa.Column("created", sa.DateTime(timezone=True), nullable=True),
            sa.Column("available_on", sa.DateTime(timezone=True), nullable=True),
            sa.Column("source_id", sa.Text(), nullable=True),
            sa.Column("source_type", sa.Text(), nullable=True),
            sa.Column("reporting_category", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not insp.has_table("stripe_payouts"):
        op.create_table(
            "stripe_payouts",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=True),
            sa.Column("arrival_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created", sa.DateTime(timezone=True), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("destination", sa.Text(), nullable=True),
            sa.Column("balance_transaction_id", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not insp.has_table("stripe_transfers"):
        op.create_table(
            "stripe_transfers",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=False),
            sa.Column("created", sa.DateTime(timezone=True), nullable=True),
            sa.Column("destination", sa.Text(), nullable=True),
            sa.Column("status", sa.Text(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_products_stripe_account_id ON stripe_products (stripe_account_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_products_active ON stripe_products (active)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_products_created_desc ON stripe_products (created DESC NULLS LAST)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_products_metadata_gin ON stripe_products USING GIN (metadata)"
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_prices_product_id ON stripe_prices (product_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_prices_stripe_account_id ON stripe_prices (stripe_account_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_prices_active ON stripe_prices (active)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_prices_metadata_gin ON stripe_prices USING GIN (metadata)")

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_coupons_stripe_account_id ON stripe_coupons (stripe_account_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_coupons_created_desc ON stripe_coupons (created DESC NULLS LAST)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_coupons_metadata_gin ON stripe_coupons USING GIN (metadata)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_subscriptions_customer_id ON stripe_subscriptions (customer_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_subscriptions_status ON stripe_subscriptions (status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_subscriptions_stripe_account_id ON stripe_subscriptions (stripe_account_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_subscriptions_created_desc ON stripe_subscriptions (created DESC NULLS LAST)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_subscriptions_metadata_gin ON stripe_subscriptions USING GIN (metadata)"
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_invoices_customer_id ON stripe_invoices (customer_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_invoices_subscription_id ON stripe_invoices (subscription_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_invoices_status ON stripe_invoices (status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_invoices_stripe_account_id ON stripe_invoices (stripe_account_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_invoices_created_desc ON stripe_invoices (created DESC NULLS LAST)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_invoices_metadata_gin ON stripe_invoices USING GIN (metadata)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_payment_intents_customer_id ON stripe_payment_intents (customer_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_payment_intents_status ON stripe_payment_intents (status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_payment_intents_latest_charge_id ON stripe_payment_intents (latest_charge_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_payment_intents_stripe_account_id ON stripe_payment_intents (stripe_account_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_payment_intents_created_desc ON stripe_payment_intents (created DESC NULLS LAST)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_payment_intents_metadata_gin ON stripe_payment_intents USING GIN (metadata)"
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_charges_customer_id ON stripe_charges (customer_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_charges_status ON stripe_charges (status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_charges_stripe_account_id ON stripe_charges (stripe_account_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_charges_created_desc ON stripe_charges (created DESC NULLS LAST)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_charges_metadata_gin ON stripe_charges USING GIN (metadata)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_refunds_charge_id ON stripe_refunds (charge_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_refunds_status ON stripe_refunds (status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_refunds_stripe_account_id ON stripe_refunds (stripe_account_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_refunds_created_desc ON stripe_refunds (created DESC NULLS LAST)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_refunds_metadata_gin ON stripe_refunds USING GIN (metadata)")

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_balance_transactions_type ON stripe_balance_transactions (type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_balance_transactions_available_on ON stripe_balance_transactions (available_on)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_balance_transactions_source_id ON stripe_balance_transactions (source_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_balance_transactions_stripe_account_id ON stripe_balance_transactions (stripe_account_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_balance_transactions_created_desc ON stripe_balance_transactions (created DESC NULLS LAST)"
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_payouts_status ON stripe_payouts (status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_payouts_stripe_account_id ON stripe_payouts (stripe_account_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_payouts_created_desc ON stripe_payouts (created DESC NULLS LAST)"
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_transfers_status ON stripe_transfers (status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_transfers_stripe_account_id ON stripe_transfers (stripe_account_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_transfers_created_desc ON stripe_transfers (created DESC NULLS LAST)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_stripe_transfers_created_desc")
    op.drop_index("ix_stripe_transfers_stripe_account_id", table_name="stripe_transfers")
    op.drop_index("ix_stripe_transfers_status", table_name="stripe_transfers")
    op.execute("DROP INDEX IF EXISTS ix_stripe_payouts_created_desc")
    op.drop_index("ix_stripe_payouts_stripe_account_id", table_name="stripe_payouts")
    op.drop_index("ix_stripe_payouts_status", table_name="stripe_payouts")
    op.execute("DROP INDEX IF EXISTS ix_stripe_balance_transactions_created_desc")
    op.drop_index("ix_stripe_balance_transactions_stripe_account_id", table_name="stripe_balance_transactions")
    op.drop_index("ix_stripe_balance_transactions_source_id", table_name="stripe_balance_transactions")
    op.drop_index("ix_stripe_balance_transactions_available_on", table_name="stripe_balance_transactions")
    op.drop_index("ix_stripe_balance_transactions_type", table_name="stripe_balance_transactions")
    op.execute("DROP INDEX IF EXISTS ix_stripe_refunds_metadata_gin")
    op.execute("DROP INDEX IF EXISTS ix_stripe_refunds_created_desc")
    op.drop_index("ix_stripe_refunds_stripe_account_id", table_name="stripe_refunds")
    op.drop_index("ix_stripe_refunds_status", table_name="stripe_refunds")
    op.drop_index("ix_stripe_refunds_charge_id", table_name="stripe_refunds")
    op.execute("DROP INDEX IF EXISTS ix_stripe_charges_metadata_gin")
    op.execute("DROP INDEX IF EXISTS ix_stripe_charges_created_desc")
    op.drop_index("ix_stripe_charges_stripe_account_id", table_name="stripe_charges")
    op.drop_index("ix_stripe_charges_status", table_name="stripe_charges")
    op.drop_index("ix_stripe_charges_customer_id", table_name="stripe_charges")
    op.execute("DROP INDEX IF EXISTS ix_stripe_payment_intents_metadata_gin")
    op.execute("DROP INDEX IF EXISTS ix_stripe_payment_intents_created_desc")
    op.drop_index("ix_stripe_payment_intents_stripe_account_id", table_name="stripe_payment_intents")
    op.drop_index("ix_stripe_payment_intents_latest_charge_id", table_name="stripe_payment_intents")
    op.drop_index("ix_stripe_payment_intents_status", table_name="stripe_payment_intents")
    op.drop_index("ix_stripe_payment_intents_customer_id", table_name="stripe_payment_intents")
    op.execute("DROP INDEX IF EXISTS ix_stripe_invoices_metadata_gin")
    op.execute("DROP INDEX IF EXISTS ix_stripe_invoices_created_desc")
    op.drop_index("ix_stripe_invoices_stripe_account_id", table_name="stripe_invoices")
    op.drop_index("ix_stripe_invoices_status", table_name="stripe_invoices")
    op.drop_index("ix_stripe_invoices_subscription_id", table_name="stripe_invoices")
    op.drop_index("ix_stripe_invoices_customer_id", table_name="stripe_invoices")
    op.execute("DROP INDEX IF EXISTS ix_stripe_subscriptions_metadata_gin")
    op.execute("DROP INDEX IF EXISTS ix_stripe_subscriptions_created_desc")
    op.drop_index("ix_stripe_subscriptions_stripe_account_id", table_name="stripe_subscriptions")
    op.drop_index("ix_stripe_subscriptions_status", table_name="stripe_subscriptions")
    op.drop_index("ix_stripe_subscriptions_customer_id", table_name="stripe_subscriptions")
    op.execute("DROP INDEX IF EXISTS ix_stripe_coupons_metadata_gin")
    op.execute("DROP INDEX IF EXISTS ix_stripe_coupons_created_desc")
    op.drop_index("ix_stripe_coupons_stripe_account_id", table_name="stripe_coupons")
    op.execute("DROP INDEX IF EXISTS ix_stripe_prices_metadata_gin")
    op.drop_index("ix_stripe_prices_active", table_name="stripe_prices")
    op.drop_index("ix_stripe_prices_stripe_account_id", table_name="stripe_prices")
    op.drop_index("ix_stripe_prices_product_id", table_name="stripe_prices")
    op.execute("DROP INDEX IF EXISTS ix_stripe_products_metadata_gin")
    op.execute("DROP INDEX IF EXISTS ix_stripe_products_created_desc")
    op.drop_index("ix_stripe_products_active", table_name="stripe_products")
    op.drop_index("ix_stripe_products_stripe_account_id", table_name="stripe_products")

    op.drop_table("stripe_transfers")
    op.drop_table("stripe_payouts")
    op.drop_table("stripe_balance_transactions")
    op.drop_table("stripe_refunds")
    op.drop_table("stripe_charges")
    op.drop_table("stripe_payment_intents")
    op.drop_table("stripe_invoices")
    op.drop_table("stripe_subscriptions")
    op.drop_table("stripe_coupons")
    op.drop_table("stripe_prices")
    op.drop_table("stripe_products")
