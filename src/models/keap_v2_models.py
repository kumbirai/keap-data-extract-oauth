"""SQLAlchemy models for Keap REST v2 BI tables (documentation/bau/sprint-01)."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, PrimaryKeyConstraint, Text

from sqlalchemy.dialects.postgresql import JSONB

from src.models.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class KeapV2Company(Base):
    __tablename__ = "keap_v2_companies"

    id = Column(Text, primary_key=True)
    company_name = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    website = Column(Text, nullable=True)
    create_time = Column(DateTime(timezone=True), nullable=True)
    update_time = Column(DateTime(timezone=True), nullable=True)
    custom_fields = Column(JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class KeapV2ContactLinkType(Base):
    __tablename__ = "keap_v2_contact_link_types"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class KeapV2ContactLink(Base):
    __tablename__ = "keap_v2_contact_links"

    contact_id = Column(Integer, nullable=False)
    linked_contact_id = Column(Integer, nullable=False)
    link_type_id = Column(Text, nullable=False)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint("contact_id", "linked_contact_id", "link_type_id"),
    )


class KeapV2AutomationCategory(Base):
    __tablename__ = "keap_v2_automation_categories"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class KeapV2Automation(Base):
    __tablename__ = "keap_v2_automations"

    id = Column(Text, primary_key=True)
    title = Column(Text, nullable=True)
    status = Column(Text, nullable=True)
    locked = Column(Boolean, nullable=True)
    active_contacts = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    published_date = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(Text, nullable=True)
    published_timezone = Column(Text, nullable=True)
    categories = Column(JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class KeapV2CategoryDiscount(Base):
    __tablename__ = "keap_v2_category_discounts"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class KeapV2ProductDiscount(Base):
    __tablename__ = "keap_v2_product_discounts"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    product_id = Column(Text, nullable=True)
    discount_type = Column(Text, nullable=True)
    discount_value = Column(Float, nullable=True)
    apply_to_commissions = Column(Boolean, nullable=True)
    criteria = Column(JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class KeapV2OrderTotalDiscount(Base):
    __tablename__ = "keap_v2_order_total_discounts"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class KeapV2FreeTrialDiscount(Base):
    __tablename__ = "keap_v2_free_trial_discounts"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class KeapV2ShippingDiscount(Base):
    __tablename__ = "keap_v2_shipping_discounts"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class KeapV2CampaignGoal(Base):
    __tablename__ = "keap_v2_campaign_goals"

    campaign_id = Column(Integer, nullable=False)
    goal_id = Column(Text, nullable=False)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (PrimaryKeyConstraint("campaign_id", "goal_id"),)


class KeapV2CampaignSequenceV2(Base):
    """v2 API campaign sequences (distinct from v1 ``campaign_sequences``)."""

    __tablename__ = "keap_v2_campaign_sequences"

    campaign_id = Column(Integer, nullable=False)
    sequence_id = Column(Text, nullable=False)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (PrimaryKeyConstraint("campaign_id", "sequence_id"),)


class KeapV2AffiliateReferral(Base):
    __tablename__ = "keap_v2_affiliate_referrals"

    id = Column(Text, primary_key=True)
    affiliate_id = Column(Integer, nullable=False, index=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class KeapV2ContactLeadScore(Base):
    __tablename__ = "keap_v2_contact_lead_scores"

    contact_id = Column(Integer, primary_key=True)
    score_payload = Column(JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class KeapV2LeadSourceCategory(Base):
    __tablename__ = "keap_v2_lead_source_categories"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class KeapV2LeadSource(Base):
    __tablename__ = "keap_v2_lead_sources"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class KeapV2LeadSourceExpense(Base):
    __tablename__ = "keap_v2_lead_source_expenses"

    lead_source_id = Column(Text, nullable=False)
    expense_id = Column(Text, nullable=False)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (PrimaryKeyConstraint("lead_source_id", "expense_id"),)


class KeapV2LeadSourceRecurringExpense(Base):
    __tablename__ = "keap_v2_lead_source_recurring_expenses"

    lead_source_id = Column(Text, nullable=False)
    recurring_expense_id = Column(Text, nullable=False)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (PrimaryKeyConstraint("lead_source_id", "recurring_expense_id"),)


class KeapV2LeadSourceRecurringExpenseIncurred(Base):
    __tablename__ = "keap_v2_lead_source_recurring_expense_incurred"

    lead_source_id = Column(Text, nullable=False)
    recurring_expense_id = Column(Text, nullable=False)
    incurred_id = Column(Text, nullable=False)
    raw_payload = Column(JSONB, nullable=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint("lead_source_id", "recurring_expense_id", "incurred_id"),
    )
