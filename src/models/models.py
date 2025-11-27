"""Database models - combines all models for Alembic."""
# Import Base from base module
from src.models.base import Base

# Import OAuth models to register them with Base
from src.models.oauth_models import OAuthToken, ExtractionState

# Import all entity models to register them with Base
from src.models.entity_models import (
    AccountProfile, Affiliate, AffiliateClawback, AffiliateCommission,
    AffiliatePayment, AffiliateProgram, AffiliateRedirect, AffiliateSummary,
    AffiliateRedirectProgram, BusinessGoal, Campaign, CampaignSequence,
    Contact, ContactAddress, ContactCustomFieldValue, CreditCard,
    CustomField, CustomFieldMetaData, EmailAddress, FaxNumber, Note,
    NoteCustomFieldValue, Opportunity, OpportunityCustomFieldValue,
    Order, OrderCustomFieldValue, OrderItem, OrderPayment, OrderTransaction,
    PaymentGateway, PaymentPlan, PhoneNumber, Product, ProductOption,
    ShippingInformation, Subscription, SubscriptionCustomFieldValue,
    SubscriptionPlan, Tag, TagCategory, Task
)

__all__ = [
    'Base', 'OAuthToken', 'ExtractionState',
    'AccountProfile', 'Affiliate', 'AffiliateClawback', 'AffiliateCommission',
    'AffiliatePayment', 'AffiliateProgram', 'AffiliateRedirect', 'AffiliateSummary',
    'AffiliateRedirectProgram', 'BusinessGoal', 'Campaign', 'CampaignSequence',
    'Contact', 'ContactAddress', 'ContactCustomFieldValue', 'CreditCard',
    'CustomField', 'CustomFieldMetaData', 'EmailAddress', 'FaxNumber', 'Note',
    'NoteCustomFieldValue', 'Opportunity', 'OpportunityCustomFieldValue',
    'Order', 'OrderCustomFieldValue', 'OrderItem', 'OrderPayment', 'OrderTransaction',
    'PaymentGateway', 'PaymentPlan', 'PhoneNumber', 'Product', 'ProductOption',
    'ShippingInformation', 'Subscription', 'SubscriptionCustomFieldValue',
    'SubscriptionPlan', 'Tag', 'TagCategory', 'Task'
]

