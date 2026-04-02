"""Keap REST v2 BI tables and extraction_state.api_page_token

Revision ID: 007_keap_v2_bi
Revises: 006_stripe_sprint02
Create Date: 2026-04-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "007_keap_v2_bi"
down_revision = "006_stripe_sprint02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    cols = [c["name"] for c in insp.get_columns("extraction_state")]
    if "api_page_token" not in cols:
        op.add_column("extraction_state", sa.Column("api_page_token", sa.Text(), nullable=True))

    tables = [
        (
            "keap_v2_companies",
            [
                sa.Column("id", sa.Text(), nullable=False),
                sa.Column("company_name", sa.Text(), nullable=True),
                sa.Column("notes", sa.Text(), nullable=True),
                sa.Column("website", sa.Text(), nullable=True),
                sa.Column("create_time", sa.DateTime(timezone=True), nullable=True),
                sa.Column("update_time", sa.DateTime(timezone=True), nullable=True),
                sa.Column("custom_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("id"),
            ],
        ),
        (
            "keap_v2_contact_link_types",
            [
                sa.Column("id", sa.Text(), nullable=False),
                sa.Column("name", sa.Text(), nullable=True),
                sa.Column("description", sa.Text(), nullable=True),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("id"),
            ],
        ),
        (
            "keap_v2_contact_links",
            [
                sa.Column("contact_id", sa.Integer(), nullable=False),
                sa.Column("linked_contact_id", sa.Integer(), nullable=False),
                sa.Column("link_type_id", sa.Text(), nullable=False),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("contact_id", "linked_contact_id", "link_type_id"),
            ],
        ),
        (
            "keap_v2_automation_categories",
            [
                sa.Column("id", sa.Text(), nullable=False),
                sa.Column("name", sa.Text(), nullable=True),
                sa.Column("description", sa.Text(), nullable=True),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("id"),
            ],
        ),
        (
            "keap_v2_automations",
            [
                sa.Column("id", sa.Text(), nullable=False),
                sa.Column("title", sa.Text(), nullable=True),
                sa.Column("status", sa.Text(), nullable=True),
                sa.Column("locked", sa.Boolean(), nullable=True),
                sa.Column("active_contacts", sa.Integer(), nullable=True),
                sa.Column("error_message", sa.Text(), nullable=True),
                sa.Column("published_date", sa.DateTime(timezone=True), nullable=True),
                sa.Column("published_by", sa.Text(), nullable=True),
                sa.Column("published_timezone", sa.Text(), nullable=True),
                sa.Column("categories", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("id"),
            ],
        ),
        (
            "keap_v2_category_discounts",
            [
                sa.Column("id", sa.Text(), nullable=False),
                sa.Column("name", sa.Text(), nullable=True),
                sa.Column("description", sa.Text(), nullable=True),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("id"),
            ],
        ),
        (
            "keap_v2_product_discounts",
            [
                sa.Column("id", sa.Text(), nullable=False),
                sa.Column("name", sa.Text(), nullable=True),
                sa.Column("description", sa.Text(), nullable=True),
                sa.Column("product_id", sa.Text(), nullable=True),
                sa.Column("discount_type", sa.Text(), nullable=True),
                sa.Column("discount_value", sa.Float(), nullable=True),
                sa.Column("apply_to_commissions", sa.Boolean(), nullable=True),
                sa.Column("criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("id"),
            ],
        ),
        (
            "keap_v2_order_total_discounts",
            [
                sa.Column("id", sa.Text(), nullable=False),
                sa.Column("name", sa.Text(), nullable=True),
                sa.Column("description", sa.Text(), nullable=True),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("id"),
            ],
        ),
        (
            "keap_v2_free_trial_discounts",
            [
                sa.Column("id", sa.Text(), nullable=False),
                sa.Column("name", sa.Text(), nullable=True),
                sa.Column("description", sa.Text(), nullable=True),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("id"),
            ],
        ),
        (
            "keap_v2_shipping_discounts",
            [
                sa.Column("id", sa.Text(), nullable=False),
                sa.Column("name", sa.Text(), nullable=True),
                sa.Column("description", sa.Text(), nullable=True),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("id"),
            ],
        ),
        (
            "keap_v2_campaign_goals",
            [
                sa.Column("campaign_id", sa.Integer(), nullable=False),
                sa.Column("goal_id", sa.Text(), nullable=False),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("campaign_id", "goal_id"),
            ],
        ),
        (
            "keap_v2_campaign_sequences",
            [
                sa.Column("campaign_id", sa.Integer(), nullable=False),
                sa.Column("sequence_id", sa.Text(), nullable=False),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("campaign_id", "sequence_id"),
            ],
        ),
        (
            "keap_v2_affiliate_referrals",
            [
                sa.Column("id", sa.Text(), nullable=False),
                sa.Column("affiliate_id", sa.Integer(), nullable=False),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("id"),
            ],
        ),
        (
            "keap_v2_contact_lead_scores",
            [
                sa.Column("contact_id", sa.Integer(), nullable=False),
                sa.Column("score_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("contact_id"),
            ],
        ),
        (
            "keap_v2_lead_source_categories",
            [
                sa.Column("id", sa.Text(), nullable=False),
                sa.Column("name", sa.Text(), nullable=True),
                sa.Column("description", sa.Text(), nullable=True),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("id"),
            ],
        ),
        (
            "keap_v2_lead_sources",
            [
                sa.Column("id", sa.Text(), nullable=False),
                sa.Column("name", sa.Text(), nullable=True),
                sa.Column("description", sa.Text(), nullable=True),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("id"),
            ],
        ),
        (
            "keap_v2_lead_source_expenses",
            [
                sa.Column("lead_source_id", sa.Text(), nullable=False),
                sa.Column("expense_id", sa.Text(), nullable=False),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("lead_source_id", "expense_id"),
            ],
        ),
        (
            "keap_v2_lead_source_recurring_expenses",
            [
                sa.Column("lead_source_id", sa.Text(), nullable=False),
                sa.Column("recurring_expense_id", sa.Text(), nullable=False),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("lead_source_id", "recurring_expense_id"),
            ],
        ),
        (
            "keap_v2_lead_source_recurring_expense_incurred",
            [
                sa.Column("lead_source_id", sa.Text(), nullable=False),
                sa.Column("recurring_expense_id", sa.Text(), nullable=False),
                sa.Column("incurred_id", sa.Text(), nullable=False),
                sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
                sa.PrimaryKeyConstraint("lead_source_id", "recurring_expense_id", "incurred_id"),
            ],
        ),
    ]

    for name, columns in tables:
        if not insp.has_table(name):
            op.create_table(name, *columns)

    insp2 = inspect(bind)
    if insp2.has_table("keap_v2_affiliate_referrals"):
        idx_names = {ix["name"] for ix in insp2.get_indexes("keap_v2_affiliate_referrals")}
        if "ix_keap_v2_affiliate_referrals_affiliate_id" not in idx_names:
            op.create_index(
                "ix_keap_v2_affiliate_referrals_affiliate_id",
                "keap_v2_affiliate_referrals",
                ["affiliate_id"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if insp.has_table("keap_v2_affiliate_referrals"):
        idx_names = {ix["name"] for ix in insp.get_indexes("keap_v2_affiliate_referrals")}
        if "ix_keap_v2_affiliate_referrals_affiliate_id" in idx_names:
            op.drop_index("ix_keap_v2_affiliate_referrals_affiliate_id", table_name="keap_v2_affiliate_referrals")
    for name in (
        "keap_v2_lead_source_recurring_expense_incurred",
        "keap_v2_lead_source_recurring_expenses",
        "keap_v2_lead_source_expenses",
        "keap_v2_lead_sources",
        "keap_v2_lead_source_categories",
        "keap_v2_contact_lead_scores",
        "keap_v2_affiliate_referrals",
        "keap_v2_campaign_sequences",
        "keap_v2_campaign_goals",
        "keap_v2_shipping_discounts",
        "keap_v2_free_trial_discounts",
        "keap_v2_order_total_discounts",
        "keap_v2_product_discounts",
        "keap_v2_category_discounts",
        "keap_v2_automations",
        "keap_v2_automation_categories",
        "keap_v2_contact_links",
        "keap_v2_contact_link_types",
        "keap_v2_companies",
    ):
        if insp.has_table(name):
            op.drop_table(name)
    cols = [c["name"] for c in insp.get_columns("extraction_state")]
    if "api_page_token" in cols:
        op.drop_column("extraction_state", "api_page_token")
