"""Stripe entity_type strings (no stripe SDK import — safe for LoaderFactory)."""

STRIPE_TOP_LEVEL_ENTITY_TYPES = [
    "stripe_products",
    "stripe_prices",
    "stripe_coupons",
    "stripe_customers",
    "stripe_subscriptions",
    "stripe_invoices",
    "stripe_payment_intents",
    "stripe_charges",
    "stripe_disputes",
    "stripe_promotion_codes",
    "stripe_credit_notes",
    "stripe_refunds",
    "stripe_balance_transactions",
    "stripe_payouts",
    "stripe_transfers",
]

STRIPE_CHILD_ENTITY_TYPES = [
    "stripe_invoice_line_items",
    "stripe_subscription_items",
]

STRIPE_ENTITY_TYPES = STRIPE_TOP_LEVEL_ENTITY_TYPES + STRIPE_CHILD_ENTITY_TYPES

STRIPE_ALL_ENTITY_TYPE = "stripe_all"
