# 4. BI reporting and joins (Stripe BI + Keap)

## 4.1 Source-of-truth matrix

| Dataset | Typical grain | Use for |
|---------|----------------|---------|
| **Keap** — [`orders`](../../src/models/entity_models.py), [`order_payments`](../../src/models/entity_models.py), [`order_transactions`](../../src/models/entity_models.py) | CRM / commerce transaction | Recognized revenue in Keap, fulfillment, internal invoices |
| **`stripe_subscriptions`** | Recurring agreement | MRR / churn / subscription status reporting |
| **`stripe_invoices`** | Billing document | Invoice-level totals, dunning, tax display as Stripe exposes |
| **`stripe_payment_intents`** | Payment attempt | Checkout funnel, incomplete payments, intent status before charge |
| **`stripe_charges`** | Captured (or attempted) card/network charge | **Cash-like** gateway activity, failures, charge-level refunds aggregate |
| **`stripe_refunds`** | Refund line | Refund timing and status **per refund**; ties to charge (and optionally PI) |
| **`stripe_balance_transactions`** | Ledger movement | **Net after fees**, settlement timing, reconciliation to payouts |
| **`stripe_products` / `stripe_prices` / `stripe_coupons`** | Dimension | Descriptions and pricing context for invoice or subscription analytics (often via `raw_payload` until line items are normalized) |

**Double-counting risk**

- **Keap vs Stripe**: A single payment may appear in Keap and as a Stripe charge. Do not sum both as “revenue” without rules.
- **Stripe facts vs each other**: **Invoice totals**, **subscription MRR**, **charge amounts**, and **balance transaction net** measure different things. Pick **one primary metric per report** (e.g. “B2B invoice revenue” from `stripe_invoices` vs “cash collected” from charges vs “net settlement” from balance transactions).
- **Refunds**: Summing **`stripe_refunds.amount`** and **`stripe_charges.amount_refunded`** for the same period without deduplication **double-counts** refund value. Prefer **either** refund lines **or** charge-level aggregates for a given chart, or join and allocate explicitly.

## 4.2 Joins within Stripe (sketches)

Adjust column names to match migrations. All joins are **logical**; validate nulls and id formats in production.

### Price → product

```sql
SELECT pr.id AS price_id, p.name AS product_name, pr.currency, pr.unit_amount
FROM stripe_prices pr
LEFT JOIN stripe_products p ON p.id = pr.product_id;
```

### Invoice → subscription → customer (ids on invoice)

```sql
SELECT inv.id AS invoice_id, inv.status, sub.status AS subscription_status, inv.customer_id
FROM stripe_invoices inv
LEFT JOIN stripe_subscriptions sub ON sub.id = inv.subscription_id;
```

### Charge → payment intent → invoice

```sql
SELECT ch.id AS charge_id, ch.status AS charge_status,
       pi.id AS payment_intent_id, pi.status AS pi_status,
       inv.id AS invoice_id, inv.status AS invoice_status
FROM stripe_charges ch
LEFT JOIN stripe_payment_intents pi ON pi.id = ch.payment_intent_id
LEFT JOIN stripe_invoices inv ON inv.id = ch.invoice_id;
```

### Refund → charge → balance transaction

```sql
SELECT r.id AS refund_id, r.amount AS refund_amount, r.status AS refund_status,
       ch.id AS charge_id, ch.amount AS charge_amount,
       r.balance_transaction_id
FROM stripe_refunds r
JOIN stripe_charges ch ON ch.id = r.charge_id;
```

### Balance transaction → charge or payout (via source)

```sql
-- Illustrative: map source_type to joins in your semantic layer
SELECT bt.id, bt.type, bt.net, bt.source_id, bt.source_type
FROM stripe_balance_transactions bt
WHERE bt.type IN ('charge', 'refund', 'payout');
-- Join to stripe_charges when source_type = 'charge' and source_id = ch.id, etc.
```

## 4.3 Optional join paths to Keap (best effort)

None of these are guaranteed unless your Stripe integration writes stable correlation data.

### Metadata → Keap ids

If charges (or invoices) include metadata such as `keap_contact_id` or `keap_order_id`:

```sql
SELECT c.*
FROM stripe_charges sc
JOIN contacts c ON c.id = (sc.metadata->>'keap_contact_id')::int;
```

Use defensive casting and handle missing or malformed metadata.

### Email overlap

If `stripe_charges.receipt_email` is populated and Keap [`email_addresses`](../../src/models/entity_models.py) is maintained:

```sql
SELECT sc.id AS stripe_charge_id, ea.contact_id
FROM stripe_charges sc
JOIN email_addresses ea ON lower(ea.email) = lower(sc.receipt_email);
```

Emails are not unique globally; deduplicate or apply business rules before production metrics.

### Order linkage

Joining to [`orders`](../../src/models/entity_models.py) usually requires a **shared external identifier** in Stripe `metadata` or a separate mapping table maintained outside this repo.

## 4.4 Example analytical SQL (sketches)

### Daily successful charge volume by currency

```sql
SELECT
  date_trunc('day', created AT TIME ZONE 'UTC') AS charge_day_utc,
  currency,
  count(*) AS charge_count,
  sum(amount) AS total_amount_smallest_unit
FROM stripe_charges
WHERE status = 'succeeded'
GROUP BY 1, 2
ORDER BY 1 DESC, 2;
```

### Failed charges for operations review

```sql
SELECT id, created, amount, currency, failure_code, failure_message
FROM stripe_charges
WHERE status = 'failed'
ORDER BY created DESC
LIMIT 100;
```

### Refund activity (charge-level aggregate vs refund lines)

**Charge-level** (one row per charge with partial totals):

```sql
SELECT
  date_trunc('week', created AT TIME ZONE 'UTC') AS week_utc,
  currency,
  sum(amount_refunded) AS total_refunded_smallest_unit
FROM stripe_charges
WHERE amount_refunded > 0
GROUP BY 1, 2
ORDER BY 1 DESC;
```

**Refund-line** (one row per refund):

```sql
SELECT
  date_trunc('week', r.created AT TIME ZONE 'UTC') AS week_utc,
  r.currency,
  sum(r.amount) AS total_refund_amount_smallest_unit
FROM stripe_refunds r
WHERE r.status = 'succeeded'
GROUP BY 1, 2
ORDER BY 1 DESC;
```

Do not add both summaries into one “total refunds” KPI without documentation.

### Open invoice amount by customer

```sql
SELECT customer_id, currency, sum(amount_due) AS open_amount_due
FROM stripe_invoices
WHERE status = 'open'
GROUP BY 1, 2;
```

Amounts are in **smallest currency units** unless your ETL converts them; document units in the semantic layer.

## 4.5 Modeling notes for semantic layers

- Expose **`created`** and period fields as **UTC** or with explicit timezone labels.
- Document **`amount`**, **`amount_refunded`**, **`fee`**, **`net`** unit rules per currency (Stripe’s model).
- **Grain**: declare whether a report is **invoice**, **charge**, **refund line**, or **balance transaction**; avoid mixing grains in one fact.
- **Invoice line items**: until a `stripe_invoice_line_items` table exists, line detail may live only in **`stripe_invoices.raw_payload`**—hide raw JSON from default analyst views or wrap in controlled views.
- If `raw_payload` exists on any table, hide it from default BI models to reduce accidental PII exposure.

## 4.6 Related reading

- [02-schema-design.md](02-schema-design.md) — tables, columns, indexes
- [01-scope-and-requirements.md](01-scope-and-requirements.md) — incremental sync and drift
- [03-extract-integration.md](03-extract-integration.md) — load order and `entity_type` values
