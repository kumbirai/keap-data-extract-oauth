# 4. BI reporting and joins (Revolut Merchant API)

## 4.1 Source-of-truth matrix

| Metric | Source | Table | Notes |
|--------|--------|-------|-------|
| Merchant order volume | Revolut Merchant | `revolut_merchant_orders` | |
| Merchant revenue (captured) | Revolut Merchant | `revolut_merchant_orders` where `state = 'completed'` | Amount in minor units — divide by 100 for display |
| Payment success rate | Revolut Merchant | `revolut_merchant_order_payments` | captured / total attempts |
| Decline rate by card brand | Revolut Merchant | `revolut_merchant_order_payments` | |
| Chargeback rate | Revolut Merchant | `revolut_merchant_disputes` | disputes / completed orders |
| Customer lifetime value | Revolut Merchant | join `customers` → `orders` | |
| Stored card breakdown | Revolut Merchant | `revolut_merchant_payment_methods` | |
| Business account movements | Revolut Business | `revolut_transactions` | Sprint-01 |
| Stripe card payments | Stripe | `stripe_charges` | Different rail |
| CRM contacts / pipeline | Keap | `contact`, `opportunity` | |

**Rule**: Choose one source per metric. Do **not** combine Revolut Merchant and Stripe to produce a single "total revenue" figure without explicitly resolving double-counting (e.g. if a charge is also processed on the Revolut Business ledger).

## 4.2 Accepted payment definition (Revolut Merchant)

An "accepted payment" in Revolut Merchant context:

```sql
SELECT *
FROM revolut_merchant_orders
WHERE state = 'completed'
  AND amount IS NOT NULL;
```

For financial reconciliation, also filter by `currency` to avoid mixing amounts across denominations.

## 4.3 Example SQL

### Daily order revenue (last 30 days)

```sql
SELECT
    DATE_TRUNC('day', created_at AT TIME ZONE 'UTC') AS order_date,
    currency,
    COUNT(*)                        AS order_count,
    SUM(amount) / 100.0             AS revenue,
    COUNT(*) FILTER (WHERE state = 'completed')  AS completed_count,
    COUNT(*) FILTER (WHERE state = 'failed')     AS failed_count
FROM revolut_merchant_orders
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY 1, 2
ORDER BY 1 DESC, 2;
```

### Payment method success rate by card brand

```sql
SELECT
    card_brand,
    COUNT(*)                                                    AS attempts,
    COUNT(*) FILTER (WHERE state = 'captured')                  AS captured,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE state = 'captured') / NULLIF(COUNT(*), 0),
        2
    )                                                           AS capture_rate_pct
FROM revolut_merchant_order_payments
WHERE created_at >= NOW() - INTERVAL '90 days'
GROUP BY 1
ORDER BY attempts DESC;
```

### Orders with dispute flag

```sql
SELECT
    o.id              AS order_id,
    o.created_at,
    o.amount / 100.0  AS order_amount,
    o.currency,
    o.state           AS order_state,
    d.id              AS dispute_id,
    d.state           AS dispute_state,
    d.reason          AS dispute_reason,
    d.due_at          AS dispute_due
FROM revolut_merchant_orders o
LEFT JOIN revolut_merchant_disputes d ON d.order_id = o.id
WHERE d.id IS NOT NULL
ORDER BY d.created_at DESC;
```

### Customer order history with payment methods

```sql
SELECT
    c.id              AS customer_id,
    c.email,
    COUNT(o.id)       AS order_count,
    SUM(o.amount) / 100.0  AS total_spent,
    o.currency,
    MAX(o.created_at) AS last_order_at,
    COUNT(DISTINCT pm.id)  AS saved_cards
FROM revolut_merchant_customers c
LEFT JOIN revolut_merchant_orders o  ON o.customer_id = c.id AND o.state = 'completed'
LEFT JOIN revolut_merchant_payment_methods pm ON pm.customer_id = c.id
GROUP BY c.id, c.email, o.currency
ORDER BY total_spent DESC NULLS LAST;
```

### Chargeback rate (last 90 days)

```sql
WITH completed AS (
    SELECT currency, COUNT(*) AS cnt
    FROM revolut_merchant_orders
    WHERE state = 'completed'
      AND created_at >= NOW() - INTERVAL '90 days'
    GROUP BY currency
),
disputed AS (
    SELECT o.currency, COUNT(DISTINCT d.id) AS cnt
    FROM revolut_merchant_disputes d
    JOIN revolut_merchant_orders o ON o.id = d.order_id
    WHERE d.created_at >= NOW() - INTERVAL '90 days'
    GROUP BY o.currency
)
SELECT
    c.currency,
    c.cnt                                  AS completed_orders,
    COALESCE(d.cnt, 0)                     AS disputes,
    ROUND(100.0 * COALESCE(d.cnt, 0) / NULLIF(c.cnt, 0), 4) AS chargeback_rate_pct
FROM completed c
LEFT JOIN disputed d USING (currency);
```

## 4.4 Joining Merchant data with Keap CRM

There is no shared identifier between Revolut Merchant customers and Keap contacts. Joins must use **email address** as a bridging key (with its associated data-quality caveats):

```sql
SELECT
    k.id               AS keap_contact_id,
    k.email1           AS email,
    COUNT(o.id)        AS revolut_order_count,
    SUM(o.amount) / 100.0  AS revolut_total_spent,
    o.currency
FROM contact k
JOIN revolut_merchant_customers rc ON LOWER(rc.email) = LOWER(k.email1)
JOIN revolut_merchant_orders o      ON o.customer_id = rc.id AND o.state = 'completed'
GROUP BY 1, 2, o.currency;
```

**Cautions**:
- Email matching is case-insensitive but not collision-safe across contact records.
- A Revolut customer may not have a corresponding Keap contact (e.g. guest checkout).
- A Keap contact may have multiple email addresses.

## 4.5 Joining Merchant data with Revolut Business

Revolut Business transactions (`revolut_transactions`) record **ledger movements** — settlements and payouts. Merchant orders represent the **acquiring side**. They may reconcile through payout batch references if the merchant uses Revolut Business as the settlement account.

**Do not** assume `revolut_transactions.amount` equals `revolut_merchant_orders.amount` — they operate at different grains (settlement batch vs individual order).

## 4.6 Amount conventions

All `amount` columns store values in **minor currency units** (e.g. pence, cents). Divide by 100 for GBP/EUR/USD display. For non-decimal currencies (e.g. JPY), no division is needed — confirm per ISO 4217.

```sql
-- Correct for GBP/EUR/USD:
SELECT amount / 100.0 AS display_amount FROM revolut_merchant_orders;

-- Currency-aware helper (PostgreSQL):
SELECT
    amount,
    currency,
    CASE currency
        WHEN 'JPY' THEN amount::numeric
        ELSE amount / 100.0
    END AS display_amount
FROM revolut_merchant_orders;
```

## 4.7 References

- [Sprint-01 BI reporting](../sprint-01/04-bi-reporting-and-joins.md)
- [Schema design](02-schema-design.md)
