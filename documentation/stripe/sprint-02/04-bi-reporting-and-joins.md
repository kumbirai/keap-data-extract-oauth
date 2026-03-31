# 4. BI reporting and joins (Stripe BI sprint-02)

This document extends [../sprint-01/04-bi-reporting-and-joins.md](../sprint-01/04-bi-reporting-and-joins.md)
with the six sprint-02 entities. All sprint-01 join patterns, double-counting warnings, and the
source-of-truth matrix remain valid unless explicitly updated here.

---

## 4.1 Updated source-of-truth matrix

| Dataset | Grain | Use for |
|---------|-------|---------|
| **`stripe_customers`** | Customer | Named customer dimension; joins all facts by name/email |
| `stripe_charges` | Charge attempt | Cash-like gateway activity, failures, charge-level refund aggregate |
| `stripe_invoices` | Billing document | Invoice totals, dunning, subscription billing cycles |
| `stripe_subscriptions` | Recurring agreement | MRR, churn, subscription status |
| `stripe_payment_intents` | Payment attempt | Checkout funnel, incomplete payments |
| `stripe_refunds` | Refund line | Per-refund amount, timing, link to charge |
| `stripe_balance_transactions` | Ledger movement | **Net after fees**, settlement, payout reconciliation |
| **`stripe_invoice_line_items`** | Invoice line | Per-line revenue by price/product, proration detection |
| **`stripe_subscription_items`** | Subscription seat | Per-seat product analytics, MRR decomposition |
| **`stripe_disputes`** | Chargeback | Dispute exposure, win/loss rate, reason codes |
| **`stripe_promotion_codes`** | Code | Discount attribution, code effectiveness |
| **`stripe_credit_notes`** | Invoice credit | Invoice-level adjustments, credit vs refund distinction |
| `stripe_products` / `stripe_prices` / `stripe_coupons` | Dimensions | Catalog context |

**New double-counting risks (sprint-02)**:

- `stripe_credit_notes.amount` and `stripe_refunds.amount` can both represent "money back to
  customer" but from different sources. A credit note **with** a `refund_id` issued a cash refund;
  one **without** `refund_id` applied a balance credit or account adjustment. Never sum them
  together without separating these cases.
- `stripe_invoice_line_items.amount` summed per invoice should approximate `stripe_invoices.total`
  but may differ due to unapplied credits or rounding. Use invoice totals for financial reporting;
  use line items for product attribution only.

---

## 4.2 Complete join chains

### Chain 1: Balance transaction → charge → customer

This is the primary gap closed by sprint-02.

```sql
-- Net settlement with customer context
SELECT
    bt.id                       AS balance_transaction_id,
    bt.type                     AS txn_type,
    bt.amount                   AS gross_amount,
    bt.fee                      AS stripe_fee,
    bt.net                      AS net_amount,
    bt.currency,
    bt.available_on,
    ch.id                       AS charge_id,
    ch.status                   AS charge_status,
    cust.id                     AS customer_id,
    cust.email                  AS customer_email,
    cust.name                   AS customer_name,
    cust.delinquent
FROM stripe_balance_transactions bt
LEFT JOIN stripe_charges ch
    ON ch.id = bt.source_id
   AND bt.source_type = 'charge'
LEFT JOIN stripe_customers cust
    ON cust.id = ch.customer_id
WHERE bt.type = 'charge'
ORDER BY bt.created DESC;
```

For refund-type balance transactions, swap the charge join for a refund join:

```sql
-- Refund settlement with customer context
SELECT
    bt.id                   AS balance_transaction_id,
    bt.net                  AS net_settlement,
    r.id                    AS refund_id,
    r.amount                AS refund_amount,
    ch.customer_id,
    cust.email              AS customer_email,
    cust.name               AS customer_name
FROM stripe_balance_transactions bt
LEFT JOIN stripe_refunds r
    ON r.id = bt.source_id
   AND bt.source_type = 'refund'
LEFT JOIN stripe_charges ch
    ON ch.id = r.charge_id
LEFT JOIN stripe_customers cust
    ON cust.id = ch.customer_id
WHERE bt.type = 'refund';
```

---

### Chain 2: Balance transaction → charge → invoice → line items → price → product

Full revenue attribution from net settlement to product.

```sql
SELECT
    bt.id                   AS balance_transaction_id,
    bt.net                  AS net_settlement,
    bt.fee                  AS stripe_fee,
    ch.id                   AS charge_id,
    inv.id                  AS invoice_id,
    ili.id                  AS line_item_id,
    ili.description         AS line_description,
    ili.amount              AS line_amount,
    ili.quantity,
    ili.type                AS line_type,
    ili.proration,
    pr.id                   AS price_id,
    pr.unit_amount,
    pr.type                 AS price_type,
    pr.recurring_interval,
    p.id                    AS product_id,
    p.name                  AS product_name
FROM stripe_balance_transactions bt
LEFT JOIN stripe_charges ch
    ON ch.id = bt.source_id
   AND bt.source_type = 'charge'
LEFT JOIN stripe_invoices inv
    ON inv.id = ch.invoice_id
LEFT JOIN stripe_invoice_line_items ili
    ON ili.invoice_id = inv.id
LEFT JOIN stripe_prices pr
    ON pr.id = ili.price_id
LEFT JOIN stripe_products p
    ON p.id = ili.product_id
WHERE bt.type = 'charge'
  AND bt.created >= '2025-01-01'
ORDER BY bt.created DESC, ili.id;
```

---

### Chain 3: Subscription → items → price → product + customer (MRR)

```sql
SELECT
    sub.id                          AS subscription_id,
    sub.status,
    sub.current_period_start,
    sub.current_period_end,
    cust.id                         AS customer_id,
    cust.email                      AS customer_email,
    cust.name                       AS customer_name,
    si.id                           AS subscription_item_id,
    si.quantity,
    pr.id                           AS price_id,
    pr.unit_amount,
    pr.currency,
    pr.recurring_interval,
    pr.recurring_interval_count,
    p.name                          AS product_name,
    -- MRR approximation (normalize to monthly)
    CASE pr.recurring_interval
        WHEN 'day'   THEN si.quantity * pr.unit_amount * 30
        WHEN 'week'  THEN si.quantity * pr.unit_amount * 4
        WHEN 'month' THEN si.quantity * pr.unit_amount / NULLIF(pr.recurring_interval_count, 0)
        WHEN 'year'  THEN si.quantity * pr.unit_amount / 12
        ELSE NULL
    END                             AS approx_mrr_smallest_unit
FROM stripe_subscriptions sub
LEFT JOIN stripe_customers cust
    ON cust.id = sub.customer_id
LEFT JOIN stripe_subscription_items si
    ON si.subscription_id = sub.id
LEFT JOIN stripe_prices pr
    ON pr.id = si.price_id
LEFT JOIN stripe_products p
    ON p.id = si.product_id
WHERE sub.status IN ('active', 'trialing')
ORDER BY sub.customer_id, sub.id, si.id;
```

---

### Chain 4: Dispute → charge → customer

```sql
SELECT
    d.id                    AS dispute_id,
    d.amount                AS disputed_amount,
    d.currency,
    d.status                AS dispute_status,
    d.reason                AS dispute_reason,
    d.created               AS dispute_created,
    d.evidence_due_by,
    d.is_charge_refundable,
    ch.id                   AS charge_id,
    ch.amount               AS charge_amount,
    ch.created              AS charge_created,
    cust.id                 AS customer_id,
    cust.email              AS customer_email,
    cust.name               AS customer_name
FROM stripe_disputes d
LEFT JOIN stripe_charges ch
    ON ch.id = d.charge_id
LEFT JOIN stripe_customers cust
    ON cust.id = ch.customer_id
ORDER BY d.created DESC;
```

---

### Chain 5: Promotion code → coupon → customer (redemption analytics)

```sql
SELECT
    pc.id                   AS promo_code_id,
    pc.code,
    pc.active,
    pc.times_redeemed,
    pc.max_redemptions,
    pc.created              AS code_created,
    pc.expires_at,
    c.id                    AS coupon_id,
    c.name                  AS coupon_name,
    c.percent_off,
    c.amount_off,
    c.currency              AS coupon_currency,
    c.duration,
    cust.id                 AS restricted_customer_id,
    cust.email              AS restricted_customer_email
FROM stripe_promotion_codes pc
LEFT JOIN stripe_coupons c
    ON c.id = pc.coupon_id
LEFT JOIN stripe_customers cust
    ON cust.id = pc.customer_id
ORDER BY pc.times_redeemed DESC NULLS LAST;
```

**Note on discount attribution**: Stripe's invoice object carries a `discount` field with a
`promotion_code` id. Until a `stripe_invoice_discounts` table is added, full
promotion-to-invoice attribution requires parsing `stripe_invoices.raw_payload->>'discount'`.
Document this limitation in your semantic layer.

---

### Chain 6: Credit note vs refund comparison

```sql
-- Combined view: invoice-level credits and charge-level refunds
-- Use adjustment_type to avoid double-counting
SELECT
    'credit_note'           AS adjustment_type,
    cn.id                   AS adjustment_id,
    cn.created,
    cn.amount,
    cn.currency,
    cn.status,
    cn.reason,
    cn.invoice_id           AS parent_id,
    cn.customer_id,
    cust.email              AS customer_email,
    cn.refund_id            AS linked_refund_id   -- non-null = cash was also refunded
FROM stripe_credit_notes cn
LEFT JOIN stripe_customers cust ON cust.id = cn.customer_id
WHERE cn.status = 'issued'

UNION ALL

SELECT
    'refund'                AS adjustment_type,
    r.id                    AS adjustment_id,
    r.created,
    r.amount,
    r.currency,
    r.status,
    NULL                    AS reason,
    r.charge_id             AS parent_id,
    ch.customer_id,
    cust.email              AS customer_email,
    NULL                    AS linked_refund_id
FROM stripe_refunds r
LEFT JOIN stripe_charges ch   ON ch.id = r.charge_id
LEFT JOIN stripe_customers cust ON cust.id = ch.customer_id
WHERE r.status = 'succeeded'

ORDER BY created DESC;
```

**Semantic note**: a credit note row with `linked_refund_id IS NOT NULL` and its corresponding
refund row in this result set both represent the same underlying cash movement. Never add their
`amount` columns together for the same event.

---

## 4.3 Analytical SQL examples

### Open dispute exposure by customer

```sql
SELECT
    cust.email,
    cust.name,
    count(d.id)             AS open_dispute_count,
    sum(d.amount)           AS total_disputed_amount,
    d.currency,
    min(d.evidence_due_by)  AS earliest_deadline
FROM stripe_disputes d
LEFT JOIN stripe_charges ch   ON ch.id = d.charge_id
LEFT JOIN stripe_customers cust ON cust.id = ch.customer_id
WHERE d.status IN ('needs_response', 'warning_needs_response', 'under_review')
GROUP BY cust.email, cust.name, d.currency
ORDER BY total_disputed_amount DESC;
```

### Dispute win rate by reason code

```sql
SELECT
    reason,
    count(*)                                        AS total_disputes,
    count(*) FILTER (WHERE status = 'won')          AS won,
    count(*) FILTER (WHERE status = 'lost')         AS lost,
    round(
        100.0 * count(*) FILTER (WHERE status = 'won')
              / NULLIF(count(*), 0), 1
    )                                               AS win_rate_pct,
    sum(amount)                                     AS total_disputed_amount,
    currency
FROM stripe_disputes
WHERE status IN ('won', 'lost')
GROUP BY reason, currency
ORDER BY total_disputes DESC;
```

### Monthly net settlement by product

```sql
SELECT
    date_trunc('month', bt.available_on AT TIME ZONE 'UTC') AS settlement_month,
    p.name                                                   AS product_name,
    pr.currency,
    sum(ili.amount)                                          AS gross_line_amount,
    sum(bt.fee)                                              AS total_stripe_fee,
    sum(bt.net)                                              AS total_net_settlement,
    count(DISTINCT bt.id)                                    AS transaction_count
FROM stripe_balance_transactions bt
JOIN stripe_charges ch
    ON ch.id = bt.source_id AND bt.source_type = 'charge'
JOIN stripe_invoices inv
    ON inv.id = ch.invoice_id
JOIN stripe_invoice_line_items ili
    ON ili.invoice_id = inv.id
LEFT JOIN stripe_prices pr
    ON pr.id = ili.price_id
LEFT JOIN stripe_products p
    ON p.id = ili.product_id
WHERE bt.type = 'charge'
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 4 DESC;
```

### MRR by product (active subscriptions)

```sql
SELECT
    p.name              AS product_name,
    pr.currency,
    count(si.id)        AS active_items,
    sum(
        si.quantity *
        CASE pr.recurring_interval
            WHEN 'year'  THEN pr.unit_amount / 12
            WHEN 'month' THEN pr.unit_amount / NULLIF(pr.recurring_interval_count, 0)
            WHEN 'week'  THEN pr.unit_amount * 4
            WHEN 'day'   THEN pr.unit_amount * 30
            ELSE 0
        END
    )                   AS approx_mrr_smallest_unit
FROM stripe_subscription_items si
JOIN stripe_subscriptions sub ON sub.id = si.subscription_id
JOIN stripe_prices pr          ON pr.id  = si.price_id
LEFT JOIN stripe_products p    ON p.id   = si.product_id
WHERE sub.status IN ('active', 'trialing')
  AND pr.type = 'recurring'
GROUP BY p.name, pr.currency
ORDER BY approx_mrr_smallest_unit DESC NULLS LAST;
```

### Customer lifetime value (net settlement basis)

```sql
SELECT
    cust.id,
    cust.email,
    cust.name,
    cust.delinquent,
    count(DISTINCT ch.id)   AS total_charges,
    sum(ch.amount)          AS gross_charged,
    sum(ch.amount_refunded) AS total_refunded,
    sum(bt.fee)             AS total_fees_paid,
    sum(bt.net)             AS net_lifetime_settlement,
    min(ch.created)         AS first_charge,
    max(ch.created)         AS last_charge
FROM stripe_customers cust
LEFT JOIN stripe_charges ch
    ON ch.customer_id = cust.id AND ch.status = 'succeeded'
LEFT JOIN stripe_balance_transactions bt
    ON bt.source_id = ch.id AND bt.source_type = 'charge'
GROUP BY cust.id, cust.email, cust.name, cust.delinquent
ORDER BY net_lifetime_settlement DESC NULLS LAST;
```

### Subscription churn analysis

```sql
SELECT
    date_trunc('month', sub.canceled_at AT TIME ZONE 'UTC') AS churn_month,
    count(sub.id)                                           AS churned_subscriptions,
    sub.currency
FROM stripe_subscriptions sub
WHERE sub.status = 'canceled'
  AND sub.canceled_at IS NOT NULL
GROUP BY 1, 3
ORDER BY 1 DESC;
```

### Promotion code redemption tracking

```sql
SELECT
    pc.code,
    c.name              AS coupon_name,
    c.percent_off,
    c.amount_off,
    pc.times_redeemed,
    pc.active,
    pc.expires_at,
    pc.max_redemptions,
    -- remaining capacity
    CASE
        WHEN pc.max_redemptions IS NULL THEN NULL
        ELSE pc.max_redemptions - COALESCE(pc.times_redeemed, 0)
    END                 AS remaining_redemptions
FROM stripe_promotion_codes pc
JOIN stripe_coupons c ON c.id = pc.coupon_id
ORDER BY pc.times_redeemed DESC NULLS LAST;
```

---

## 4.4 Optional join paths to Keap (updated)

The sprint-01 email-overlap and metadata-based Keap joins remain unchanged. With `stripe_customers`
now available, the email join path is cleaner than going through `stripe_charges.receipt_email`:

```sql
-- Email bridge: Keap contacts → Stripe customers → lifetime charges
SELECT
    c.id                AS keap_contact_id,
    cust.id             AS stripe_customer_id,
    cust.email,
    count(ch.id)        AS total_charges,
    sum(ch.amount)      AS total_charged
FROM contacts c
JOIN stripe_customers cust
    ON lower(cust.email) = lower(c.email_address)   -- adjust column name to match Keap schema
LEFT JOIN stripe_charges ch
    ON ch.customer_id = cust.id AND ch.status = 'succeeded'
GROUP BY c.id, cust.id, cust.email;
```

**Caveats**:
- Keap stores emails in an `email_addresses` child table; adjust the join accordingly.
- Multiple Keap contacts can share an email; multiple Stripe customers can share an email. Apply
  deduplication business rules before using in production metrics.
- `stripe_customers.metadata` may carry a `keap_contact_id` key if the integration was built to
  write it at customer creation time — this is the most reliable join when available.

---

## 4.5 Modeling notes for semantic layers

All sprint-01 notes carry forward. Additional guidance for sprint-02:

**`stripe_invoice_line_items.amount`**
- In the same currency and unit as the parent invoice.
- Negative amounts indicate credits or prorations.
- For simple revenue lines: filter `proration = false AND amount > 0`.
- Expose a normalized MRR column in the semantic layer rather than requiring analysts to implement
  the interval normalization formula.

**`stripe_subscription_items.quantity`**
- Multiply `quantity × price.unit_amount` for seat-level revenue.
- No `amount` column exists on this table by design; the price carries the rate.

**`stripe_disputes`**
- Expose `evidence_due_by` prominently in operations dashboards.
- Consider alerting when `status IN ('needs_response', 'warning_needs_response')` and
  `evidence_due_by < now() + interval '3 days'`.
- `raw_payload` contains detailed evidence text — restrict to data-engineering roles; do not
  expose in default BI views.

**`stripe_credit_notes`**
- Document clearly in the semantic layer that this is an invoice adjustment, not a direct cash
  movement, unless `refund_id IS NOT NULL`.
- Do not expose both `stripe_credit_notes.amount` and `stripe_refunds.amount` in the same
  "total refunds" KPI without the deduplication logic from Chain 6.

**`stripe_customers` PII**
- `email`, `name`, and `phone` are PII.
- Apply the same access controls as `stripe_charges.receipt_email` and `raw_payload`.
- In masked/anonymized environments, expose only hashed or truncated email for join keys.

**Amounts reminder (all sprint-02 tables)**
- All integer amounts are in smallest currency unit (cents for USD).
- `stripe_customers.balance` can be negative (indicates customer credit on account).
- `stripe_credit_notes.out_of_band_amount` is a subset of `amount`, not additive to it.

---

## 4.6 Related reading

- [02-schema-design.md](02-schema-design.md) — tables, columns, indexes, full relationship diagram
- [01-scope-and-requirements.md](01-scope-and-requirements.md) — incremental sync and child list strategy
- [03-extract-integration.md](03-extract-integration.md) — load order DAG, entity_type values
- [Sprint-01 BI reporting and joins](../sprint-01/04-bi-reporting-and-joins.md) — base join patterns and double-counting rules
