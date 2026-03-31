# 2. Schema design (Stripe BI sprint-02)

All sprint-01 design principles carry forward unchanged — see
[../sprint-01/02-schema-design.md](../sprint-01/02-schema-design.md). This document covers only
the six new tables.

**Common columns on every table** (inherited from sprint-01):

| Column | Type | Notes |
|--------|------|-------|
| `metadata` | JSONB | App-specific key/value pairs from Stripe object |
| `stripe_account_id` | TEXT | Connected account id; null for platform |
| `loaded_at` | TIMESTAMPTZ | First pipeline insert (preserved on upsert) |
| `updated_at` | TIMESTAMPTZ | Last pipeline update |

`raw_payload` (JSONB, full API object) is included on tables where the full object is not already
available via a parent table, and where it provides unique debugging value.

---

## 2.1 `stripe_customers` (new dimension)

**PK**: `id` (`cus_*`). Promoted from "optional" in sprint-01 §2.7 to a required first-class
dimension.

### Columns

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | TEXT | NOT NULL (PK) | `cus_*` |
| `email` | TEXT | nullable | Primary contact email; use `lower()` for joins |
| `name` | TEXT | nullable | Customer display name |
| `phone` | TEXT | nullable | |
| `description` | TEXT | nullable | Internal description |
| `currency` | TEXT | nullable | Default currency (ISO 3-letter, lowercase) |
| `balance` | INTEGER | nullable | Customer balance in smallest unit (negative = credit) |
| `delinquent` | BOOLEAN | nullable | Set by Stripe when payment is past due |
| `created` | TIMESTAMPTZ | nullable | |
| `default_source` | TEXT | nullable | Default payment source id (`card_*`, `ba_*`, etc.) |
| `invoice_prefix` | TEXT | nullable | Prefix applied to invoices for this customer |
| `tax_exempt` | TEXT | nullable | `none`, `exempt`, or `reverse` |
| `metadata` | JSONB | nullable | |
| `raw_payload` | JSONB | nullable | Full API object — contains PII; restrict access |
| `stripe_account_id` | TEXT | nullable | Connect; null for platform |
| `loaded_at` | TIMESTAMPTZ | nullable | |
| `updated_at` | TIMESTAMPTZ | nullable | |

### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| Primary key | `(id)` | |
| `ix_stripe_customers_email` | `(email)` | Email-based joins to Keap, cross-system lookups |
| `ix_stripe_customers_created` | `(created DESC)` | Incremental watermark queries |
| `ix_stripe_customers_delinquent` | `(delinquent)` | Operations dashboards |
| `ix_stripe_customers_account` | `(stripe_account_id)` | Connect multi-account filtering |
| `ix_stripe_customers_metadata` | `GIN (metadata)` | Metadata key searches |

---

## 2.2 `stripe_invoice_line_items` (child normalization)

**PK**: `id` (`il_*`). Normalizes the `lines` array currently nested in
`stripe_invoices.raw_payload`.

`raw_payload` is intentionally omitted — the parent invoice already stores it.

### Columns

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | TEXT | NOT NULL (PK) | `il_*` |
| `invoice_id` | TEXT | NOT NULL | → `stripe_invoices.id` |
| `subscription_id` | TEXT | nullable | `sub_*` when line item is a subscription charge |
| `subscription_item_id` | TEXT | nullable | `si_*` — links back to subscription item |
| `price_id` | TEXT | nullable | → `stripe_prices.id` |
| `product_id` | TEXT | nullable | → `stripe_products.id`; denormalized from price for join convenience |
| `quantity` | INTEGER | nullable | Seats / units |
| `amount` | INTEGER | NOT NULL | Smallest currency unit; negative for credits / prorations |
| `currency` | TEXT | NOT NULL | ISO 3-letter, lowercase |
| `description` | TEXT | nullable | Line item description |
| `period_start` | TIMESTAMPTZ | nullable | Service period start |
| `period_end` | TIMESTAMPTZ | nullable | Service period end |
| `type` | TEXT | nullable | `subscription` or `invoiceitem` |
| `proration` | BOOLEAN | nullable | Whether this line is a proration adjustment |
| `metadata` | JSONB | nullable | |
| `stripe_account_id` | TEXT | nullable | Connect; null for platform |
| `loaded_at` | TIMESTAMPTZ | nullable | |
| `updated_at` | TIMESTAMPTZ | nullable | |

### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| Primary key | `(id)` | |
| `ix_stripe_ili_invoice_id` | `(invoice_id)` | Primary join from parent invoice |
| `ix_stripe_ili_subscription_id` | `(subscription_id)` | Subscription revenue rollup |
| `ix_stripe_ili_price_id` | `(price_id)` | Price/product analytics |
| `ix_stripe_ili_product_id` | `(product_id)` | Direct product-level joins |
| `ix_stripe_ili_period` | `(period_start, period_end)` | Period-based revenue reporting |
| `ix_stripe_ili_type` | `(type)` | Filter subscription vs one-off lines |
| `ix_stripe_ili_account` | `(stripe_account_id)` | Connect multi-account filtering |

---

## 2.3 `stripe_subscription_items` (child normalization)

**PK**: `id` (`si_*`). Normalizes the `items.data` array currently nested in
`stripe_subscriptions.raw_payload`.

`raw_payload` is intentionally omitted — the parent subscription already stores it.

### Columns

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | TEXT | NOT NULL (PK) | `si_*` |
| `subscription_id` | TEXT | NOT NULL | → `stripe_subscriptions.id` |
| `price_id` | TEXT | nullable | → `stripe_prices.id` |
| `product_id` | TEXT | nullable | → `stripe_products.id`; denormalized for join convenience |
| `quantity` | INTEGER | nullable | Seats / units |
| `created` | TIMESTAMPTZ | nullable | When this item was added to the subscription |
| `metadata` | JSONB | nullable | |
| `stripe_account_id` | TEXT | nullable | Connect; null for platform |
| `loaded_at` | TIMESTAMPTZ | nullable | |
| `updated_at` | TIMESTAMPTZ | nullable | |

### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| Primary key | `(id)` | |
| `ix_stripe_si_subscription_id` | `(subscription_id)` | Primary join from parent subscription |
| `ix_stripe_si_price_id` | `(price_id)` | Price/product analytics |
| `ix_stripe_si_product_id` | `(product_id)` | Direct product-level joins, MRR by product |
| `ix_stripe_si_account` | `(stripe_account_id)` | Connect multi-account filtering |

---

## 2.4 `stripe_disputes` (fact)

**PK**: `id` (`dp_*`). One row per dispute (chargeback). Disputes are long-lived and mutate
through the entire evidence and review lifecycle.

### Columns

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | TEXT | NOT NULL (PK) | `dp_*` |
| `charge_id` | TEXT | NOT NULL | → `stripe_charges.id` |
| `payment_intent_id` | TEXT | nullable | → `stripe_payment_intents.id` when available |
| `amount` | INTEGER | NOT NULL | Disputed amount (smallest currency unit) |
| `currency` | TEXT | NOT NULL | ISO 3-letter, lowercase |
| `status` | TEXT | nullable | `warning_needs_response`, `needs_response`, `under_review`, `charge_refunded`, `won`, `lost` |
| `reason` | TEXT | nullable | `duplicate`, `fraudulent`, `subscription_canceled`, `product_unacceptable`, `product_not_received`, `unrecognized`, `credit_not_processed`, `general`, `incorrect_account_details`, `insufficient_funds`, `bank_cannot_process`, `debit_not_authorized`, `customer_initiated` |
| `created` | TIMESTAMPTZ | nullable | |
| `evidence_due_by` | TIMESTAMPTZ | nullable | Deadline for submitting evidence |
| `is_charge_refundable` | BOOLEAN | nullable | Whether the underlying charge can be refunded outside the dispute |
| `metadata` | JSONB | nullable | |
| `raw_payload` | JSONB | nullable | Full dispute object including evidence details |
| `stripe_account_id` | TEXT | nullable | Connect; null for platform |
| `loaded_at` | TIMESTAMPTZ | nullable | |
| `updated_at` | TIMESTAMPTZ | nullable | |

### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| Primary key | `(id)` | |
| `ix_stripe_disputes_charge_id` | `(charge_id)` | Primary join to charges |
| `ix_stripe_disputes_status` | `(status)` | Open vs closed disputes operations dashboard |
| `ix_stripe_disputes_created` | `(created DESC)` | Recency and incremental filtering |
| `ix_stripe_disputes_due_by` | `(evidence_due_by)` | Alert queries: approaching deadlines |
| `ix_stripe_disputes_account` | `(stripe_account_id)` | Connect multi-account filtering |

---

## 2.5 `stripe_promotion_codes` (dimension)

**PK**: `id` (`promo_*`). Promotion codes apply a coupon to a customer or checkout session.
They sit between `stripe_coupons` and the discount objects on subscriptions and invoices.

### Columns

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | TEXT | NOT NULL (PK) | `promo_*` |
| `code` | TEXT | nullable | Human-readable code string (e.g. `SUMMER2025`) |
| `coupon_id` | TEXT | NOT NULL | → `stripe_coupons.id` |
| `customer_id` | TEXT | nullable | → `stripe_customers.id`; null = universal code |
| `active` | BOOLEAN | nullable | Whether the code can still be redeemed |
| `created` | TIMESTAMPTZ | nullable | |
| `expires_at` | TIMESTAMPTZ | nullable | Hard expiry timestamp |
| `max_redemptions` | INTEGER | nullable | Cap on total redemptions; null = unlimited |
| `times_redeemed` | INTEGER | nullable | Current redemption count |
| `restrictions_minimum_amount` | INTEGER | nullable | Minimum order amount (smallest currency unit) |
| `restrictions_minimum_amount_currency` | TEXT | nullable | ISO code for minimum amount currency |
| `restrictions_first_time_transaction` | BOOLEAN | nullable | Only valid on customer's first transaction |
| `metadata` | JSONB | nullable | |
| `stripe_account_id` | TEXT | nullable | Connect; null for platform |
| `loaded_at` | TIMESTAMPTZ | nullable | |
| `updated_at` | TIMESTAMPTZ | nullable | |

### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| Primary key | `(id)` | |
| `ix_stripe_promo_coupon_id` | `(coupon_id)` | Join to coupon dimension |
| `ix_stripe_promo_customer_id` | `(customer_id)` | Customer-specific codes |
| `ix_stripe_promo_active` | `(active)` | Active vs expired code analytics |
| `ix_stripe_promo_code` | `(code)` | Lookup by human-readable code string |
| `ix_stripe_promo_account` | `(stripe_account_id)` | Connect multi-account filtering |

---

## 2.6 `stripe_credit_notes` (fact)

**PK**: `id` (`cn_*`). Credit notes are invoice-level adjustments, distinct from charge-level
refunds. A credit note may or may not correspond to a cash refund.

### Columns

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | TEXT | NOT NULL (PK) | `cn_*` |
| `invoice_id` | TEXT | NOT NULL | → `stripe_invoices.id` |
| `customer_id` | TEXT | nullable | → `stripe_customers.id` |
| `amount` | INTEGER | NOT NULL | Credit amount in smallest currency unit |
| `currency` | TEXT | NOT NULL | ISO 3-letter, lowercase |
| `status` | TEXT | nullable | `issued` or `void` |
| `type` | TEXT | nullable | `pre_payment` or `post_payment` |
| `reason` | TEXT | nullable | `duplicate`, `fraudulent`, `order_change`, `product_unsatisfactory` |
| `memo` | TEXT | nullable | Internal note visible on the credit note |
| `out_of_band_amount` | INTEGER | nullable | Portion not refunded via Stripe (manual/external refund) |
| `refund_id` | TEXT | nullable | → `stripe_refunds.id`; populated when a Stripe refund was issued |
| `created` | TIMESTAMPTZ | nullable | |
| `metadata` | JSONB | nullable | |
| `raw_payload` | JSONB | nullable | Full object including line items |
| `stripe_account_id` | TEXT | nullable | Connect; null for platform |
| `loaded_at` | TIMESTAMPTZ | nullable | |
| `updated_at` | TIMESTAMPTZ | nullable | |

### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| Primary key | `(id)` | |
| `ix_stripe_cn_invoice_id` | `(invoice_id)` | Primary join to invoice |
| `ix_stripe_cn_customer_id` | `(customer_id)` | Customer-level credit analytics |
| `ix_stripe_cn_created` | `(created DESC)` | Recency and incremental filtering |
| `ix_stripe_cn_status` | `(status)` | Filter issued vs voided credit notes |
| `ix_stripe_cn_refund_id` | `(refund_id)` | Join to refunds for combined credit/refund reporting |
| `ix_stripe_cn_account` | `(stripe_account_id)` | Connect multi-account filtering |

---

## 2.7 Updated relationship diagram (all 17 tables)

```
DIMENSIONS
──────────
stripe_products ──── stripe_prices
                         │
stripe_coupons ──── stripe_promotion_codes ─────── stripe_customers
                                                         │
                    ┌────────────────────────────────────┤
                    │                    │               │
              stripe_subscriptions  stripe_invoices  stripe_payment_intents
                    │         │          │    │              │
        stripe_sub_ │         └──────────┘    └──────── stripe_charges
           _items   │                │                      │      │
                    │       stripe_invoice_               stripe_  stripe_
                    │          _line_items               _refunds  _disputes
                    │                                       │
                    └──────────────────────────────── stripe_balance_transactions
                                                            │
                                                    stripe_payouts
                                                    stripe_transfers

stripe_credit_notes ── stripe_invoices (invoice_id)
stripe_credit_notes ── stripe_customers (customer_id)
stripe_credit_notes ─· stripe_refunds (refund_id, optional)
```

### Key relationships (all logical; no FK constraints in DB)

| From | Column | To | Notes |
|------|--------|----|-------|
| `stripe_prices` | `product_id` | `stripe_products.id` | |
| `stripe_promotion_codes` | `coupon_id` | `stripe_coupons.id` | |
| `stripe_promotion_codes` | `customer_id` | `stripe_customers.id` | nullable |
| `stripe_subscriptions` | `customer_id` | `stripe_customers.id` | |
| `stripe_invoices` | `customer_id` | `stripe_customers.id` | |
| `stripe_invoices` | `subscription_id` | `stripe_subscriptions.id` | |
| `stripe_invoice_line_items` | `invoice_id` | `stripe_invoices.id` | NOT NULL |
| `stripe_invoice_line_items` | `subscription_id` | `stripe_subscriptions.id` | nullable |
| `stripe_invoice_line_items` | `subscription_item_id` | `stripe_subscription_items.id` | nullable |
| `stripe_invoice_line_items` | `price_id` | `stripe_prices.id` | nullable |
| `stripe_invoice_line_items` | `product_id` | `stripe_products.id` | nullable, denormalized |
| `stripe_subscription_items` | `subscription_id` | `stripe_subscriptions.id` | NOT NULL |
| `stripe_subscription_items` | `price_id` | `stripe_prices.id` | nullable |
| `stripe_subscription_items` | `product_id` | `stripe_products.id` | nullable, denormalized |
| `stripe_payment_intents` | `customer_id` | `stripe_customers.id` | |
| `stripe_payment_intents` | `invoice_id` | `stripe_invoices.id` | |
| `stripe_payment_intents` | `latest_charge_id` | `stripe_charges.id` | |
| `stripe_charges` | `customer_id` | `stripe_customers.id` | |
| `stripe_charges` | `invoice_id` | `stripe_invoices.id` | |
| `stripe_charges` | `payment_intent_id` | `stripe_payment_intents.id` | |
| `stripe_charges` | `balance_transaction_id` | `stripe_balance_transactions.id` | |
| `stripe_refunds` | `charge_id` | `stripe_charges.id` | NOT NULL |
| `stripe_refunds` | `balance_transaction_id` | `stripe_balance_transactions.id` | |
| `stripe_balance_transactions` | `source_id` | varies by `source_type` | see note below |
| `stripe_disputes` | `charge_id` | `stripe_charges.id` | NOT NULL |
| `stripe_disputes` | `payment_intent_id` | `stripe_payment_intents.id` | nullable |
| `stripe_credit_notes` | `invoice_id` | `stripe_invoices.id` | NOT NULL |
| `stripe_credit_notes` | `customer_id` | `stripe_customers.id` | nullable |
| `stripe_credit_notes` | `refund_id` | `stripe_refunds.id` | nullable |

**`stripe_balance_transactions.source_id` join rules:**

| `source_type` value | Join target |
|--------------------|-------------|
| `charge` | `stripe_charges.id` |
| `refund` | `stripe_refunds.id` |
| `payout` | `stripe_payouts.id` |
| `transfer` | `stripe_transfers.id` |
| other | No normalized join target; use `raw_payload` |

---

## 2.8 Sprint-01 tables updated by sprint-02

No sprint-01 table schemas change. The `stripe_invoice_line_items` and `stripe_subscription_items`
tables replace the need to query `raw_payload` on their parents, but the parent columns and indexes
are unchanged.

---

## 2.9 Amount and currency conventions (unchanged from sprint-01)

- All monetary amounts in smallest currency unit (cents for USD, pence for GBP, etc.).
- Currency stored as 3-letter ISO code, lowercase (`usd`, `gbp`, `eur`).
- `stripe_subscription_items` has no amount column; amounts are derived from
  `price.unit_amount × quantity` in the BI layer.
- `stripe_credit_notes.out_of_band_amount`: the portion of the credit not refunded through Stripe
  (e.g. a manual bank transfer). The total credit to the customer is `amount`; `out_of_band_amount`
  is a subset.

---

## 2.10 References

- [Sprint-01 schema design](../sprint-01/02-schema-design.md)
- [Stripe: Customer object](https://docs.stripe.com/api/customers/object)
- [Stripe: InvoiceLineItem object](https://docs.stripe.com/api/invoices/line_item)
- [Stripe: SubscriptionItem object](https://docs.stripe.com/api/subscription_items/object)
- [Stripe: Dispute object](https://docs.stripe.com/api/disputes/object)
- [Stripe: PromotionCode object](https://docs.stripe.com/api/promotion_codes/object)
- [Stripe: CreditNote object](https://docs.stripe.com/api/credit_notes/object)
