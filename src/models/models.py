"""Database models - combines all models for Alembic."""
# Import Base from base module
from src.models.base import Base

# Import OAuth models to register them with Base
from src.models.oauth_models import OAuthToken, ExtractionState

# Revolut BI tables
from src.models.revolut_models import RevolutAccount, RevolutTransaction

# Keap REST v2 BI tables
from src.models.keap_v2_models import (
    KeapV2AffiliateReferral,
    KeapV2Automation,
    KeapV2AutomationCategory,
    KeapV2CampaignGoal,
    KeapV2CampaignSequenceV2,
    KeapV2CategoryDiscount,
    KeapV2Company,
    KeapV2ContactLeadScore,
    KeapV2ContactLink,
    KeapV2ContactLinkType,
    KeapV2FreeTrialDiscount,
    KeapV2LeadSource,
    KeapV2LeadSourceCategory,
    KeapV2LeadSourceExpense,
    KeapV2LeadSourceRecurringExpense,
    KeapV2LeadSourceRecurringExpenseIncurred,
    KeapV2OrderTotalDiscount,
    KeapV2ProductDiscount,
    KeapV2ShippingDiscount,
)

# Stripe BI tables
from src.models.stripe_models import (
    StripeBalanceTransaction,
    StripeCharge,
    StripeCoupon,
    StripeCreditNote,
    StripeCustomer,
    StripeDispute,
    StripeInvoice,
    StripeInvoiceLineItem,
    StripePaymentIntent,
    StripePayout,
    StripePrice,
    StripeProduct,
    StripePromotionCode,
    StripeRefund,
    StripeSubscription,
    StripeSubscriptionItem,
    StripeTransfer,
)

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
    'KeapV2AffiliateReferral',
    'KeapV2Automation',
    'KeapV2AutomationCategory',
    'KeapV2CampaignGoal',
    'KeapV2CampaignSequenceV2',
    'KeapV2CategoryDiscount',
    'KeapV2Company',
    'KeapV2ContactLeadScore',
    'KeapV2ContactLink',
    'KeapV2ContactLinkType',
    'KeapV2FreeTrialDiscount',
    'KeapV2LeadSource',
    'KeapV2LeadSourceCategory',
    'KeapV2LeadSourceExpense',
    'KeapV2LeadSourceRecurringExpense',
    'KeapV2LeadSourceRecurringExpenseIncurred',
    'KeapV2OrderTotalDiscount',
    'KeapV2ProductDiscount',
    'KeapV2ShippingDiscount',
    'RevolutAccount', 'RevolutTransaction',
    'StripeBalanceTransaction', 'StripeCharge', 'StripeCoupon', 'StripeCreditNote',
    'StripeCustomer', 'StripeDispute', 'StripeInvoice', 'StripeInvoiceLineItem',
    'StripePaymentIntent', 'StripePayout', 'StripePrice', 'StripeProduct',
    'StripePromotionCode', 'StripeRefund', 'StripeSubscription', 'StripeSubscriptionItem',
    'StripeTransfer',
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

