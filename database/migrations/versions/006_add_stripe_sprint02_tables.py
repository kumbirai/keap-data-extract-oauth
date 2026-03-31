"""add stripe bi sprint-02 tables

Revision ID: 006_stripe_sprint02
Revises: 005_revolut_bi
Create Date: 2026-03-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "006_stripe_sprint02"
down_revision = "005_revolut_bi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if not insp.has_table("stripe_customers"):
        op.create_table(
            "stripe_customers",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("email", sa.Text(), nullable=True),
            sa.Column("name", sa.Text(), nullable=True),
            sa.Column("phone", sa.Text(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=True),
            sa.Column("balance", sa.Integer(), nullable=True),
            sa.Column("delinquent", sa.Boolean(), nullable=True),
            sa.Column("created", sa.DateTime(timezone=True), nullable=True),
            sa.Column("default_source", sa.Text(), nullable=True),
            sa.Column("invoice_prefix", sa.Text(), nullable=True),
            sa.Column("tax_exempt", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if not insp.has_table("stripe_invoice_line_items"):
        op.create_table(
            "stripe_invoice_line_items",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("invoice_id", sa.Text(), nullable=False),
            sa.Column("subscription_id", sa.Text(), nullable=True),
            sa.Column("subscription_item_id", sa.Text(), nullable=True),
            sa.Column("price_id", sa.Text(), nullable=True),
            sa.Column("product_id", sa.Text(), nullable=True),
            sa.Column("quantity", sa.Integer(), nullable=True),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("currency", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
            sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("type", sa.Text(), nullable=True),
            sa.Column("proration", sa.Boolean(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if not insp.has_table("stripe_subscription_items"):
        op.create_table(
            "stripe_subscription_items",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("subscription_id", sa.Text(), nullable=False),
            sa.Column("price_id", sa.Text(), nullable=True),
            sa.Column("product_id", sa.Text(), nullable=True),
            sa.Column("quantity", sa.Integer(), nullable=True),
            sa.Column("created", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if not insp.has_table("stripe_disputes"):
        op.create_table(
            "stripe_disputes",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("charge_id", sa.Text(), nullable=False),
            sa.Column("payment_intent_id", sa.Text(), nullable=True),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("currency", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created", sa.DateTime(timezone=True), nullable=True),
            sa.Column("evidence_due_by", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_charge_refundable", sa.Boolean(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if not insp.has_table("stripe_promotion_codes"):
        op.create_table(
            "stripe_promotion_codes",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("code", sa.Text(), nullable=True),
            sa.Column("coupon_id", sa.Text(), nullable=False),
            sa.Column("customer_id", sa.Text(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=True),
            sa.Column("created", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("max_redemptions", sa.Integer(), nullable=True),
            sa.Column("times_redeemed", sa.Integer(), nullable=True),
            sa.Column("restrictions_minimum_amount", sa.Integer(), nullable=True),
            sa.Column("restrictions_minimum_amount_currency", sa.Text(), nullable=True),
            sa.Column("restrictions_first_time_transaction", sa.Boolean(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if not insp.has_table("stripe_credit_notes"):
        op.create_table(
            "stripe_credit_notes",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("invoice_id", sa.Text(), nullable=False),
            sa.Column("customer_id", sa.Text(), nullable=True),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("currency", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=True),
            sa.Column("type", sa.Text(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("memo", sa.Text(), nullable=True),
            sa.Column("out_of_band_amount", sa.Integer(), nullable=True),
            sa.Column("refund_id", sa.Text(), nullable=True),
            sa.Column("created", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("stripe_account_id", sa.Text(), nullable=True),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_customers_email ON stripe_customers (email)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_customers_created_desc ON stripe_customers (created DESC NULLS LAST)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_customers_delinquent ON stripe_customers (delinquent)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_customers_stripe_account_id ON stripe_customers (stripe_account_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_customers_metadata_gin ON stripe_customers USING GIN (metadata)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_ili_invoice_id ON stripe_invoice_line_items (invoice_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_ili_subscription_id ON stripe_invoice_line_items (subscription_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_ili_price_id ON stripe_invoice_line_items (price_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_ili_product_id ON stripe_invoice_line_items (product_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_ili_period ON stripe_invoice_line_items (period_start, period_end)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_ili_type ON stripe_invoice_line_items (type)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_ili_stripe_account_id ON stripe_invoice_line_items (stripe_account_id)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_si_subscription_id ON stripe_subscription_items (subscription_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_si_price_id ON stripe_subscription_items (price_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_si_product_id ON stripe_subscription_items (product_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_si_stripe_account_id ON stripe_subscription_items (stripe_account_id)"
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_disputes_charge_id ON stripe_disputes (charge_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_disputes_status ON stripe_disputes (status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_disputes_created_desc ON stripe_disputes (created DESC NULLS LAST)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_disputes_evidence_due_by ON stripe_disputes (evidence_due_by)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_disputes_stripe_account_id ON stripe_disputes (stripe_account_id)"
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_promo_coupon_id ON stripe_promotion_codes (coupon_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_promo_customer_id ON stripe_promotion_codes (customer_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_promo_active ON stripe_promotion_codes (active)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_promo_code ON stripe_promotion_codes (code)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_promo_stripe_account_id ON stripe_promotion_codes (stripe_account_id)"
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_cn_invoice_id ON stripe_credit_notes (invoice_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_cn_customer_id ON stripe_credit_notes (customer_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_cn_created_desc ON stripe_credit_notes (created DESC NULLS LAST)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_cn_status ON stripe_credit_notes (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stripe_cn_refund_id ON stripe_credit_notes (refund_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stripe_cn_stripe_account_id ON stripe_credit_notes (stripe_account_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_stripe_cn_stripe_account_id")
    op.execute("DROP INDEX IF EXISTS ix_stripe_cn_refund_id")
    op.execute("DROP INDEX IF EXISTS ix_stripe_cn_status")
    op.execute("DROP INDEX IF EXISTS ix_stripe_cn_created_desc")
    op.execute("DROP INDEX IF EXISTS ix_stripe_cn_customer_id")
    op.execute("DROP INDEX IF EXISTS ix_stripe_cn_invoice_id")

    op.execute("DROP INDEX IF EXISTS ix_stripe_promo_stripe_account_id")
    op.execute("DROP INDEX IF EXISTS ix_stripe_promo_code")
    op.execute("DROP INDEX IF EXISTS ix_stripe_promo_active")
    op.execute("DROP INDEX IF EXISTS ix_stripe_promo_customer_id")
    op.execute("DROP INDEX IF EXISTS ix_stripe_promo_coupon_id")

    op.execute("DROP INDEX IF EXISTS ix_stripe_disputes_stripe_account_id")
    op.execute("DROP INDEX IF EXISTS ix_stripe_disputes_evidence_due_by")
    op.execute("DROP INDEX IF EXISTS ix_stripe_disputes_created_desc")
    op.execute("DROP INDEX IF EXISTS ix_stripe_disputes_status")
    op.execute("DROP INDEX IF EXISTS ix_stripe_disputes_charge_id")

    op.execute("DROP INDEX IF EXISTS ix_stripe_si_stripe_account_id")
    op.execute("DROP INDEX IF EXISTS ix_stripe_si_product_id")
    op.execute("DROP INDEX IF EXISTS ix_stripe_si_price_id")
    op.execute("DROP INDEX IF EXISTS ix_stripe_si_subscription_id")

    op.execute("DROP INDEX IF EXISTS ix_stripe_ili_stripe_account_id")
    op.execute("DROP INDEX IF EXISTS ix_stripe_ili_type")
    op.execute("DROP INDEX IF EXISTS ix_stripe_ili_period")
    op.execute("DROP INDEX IF EXISTS ix_stripe_ili_product_id")
    op.execute("DROP INDEX IF EXISTS ix_stripe_ili_price_id")
    op.execute("DROP INDEX IF EXISTS ix_stripe_ili_subscription_id")
    op.execute("DROP INDEX IF EXISTS ix_stripe_ili_invoice_id")

    op.execute("DROP INDEX IF EXISTS ix_stripe_customers_metadata_gin")
    op.execute("DROP INDEX IF EXISTS ix_stripe_customers_stripe_account_id")
    op.execute("DROP INDEX IF EXISTS ix_stripe_customers_delinquent")
    op.execute("DROP INDEX IF EXISTS ix_stripe_customers_created_desc")
    op.execute("DROP INDEX IF EXISTS ix_stripe_customers_email")

    bind = op.get_bind()
    for t in (
        "stripe_subscription_items",
        "stripe_invoice_line_items",
        "stripe_credit_notes",
        "stripe_promotion_codes",
        "stripe_disputes",
        "stripe_customers",
    ):
        if inspect(bind).has_table(t):
            op.drop_table(t)
