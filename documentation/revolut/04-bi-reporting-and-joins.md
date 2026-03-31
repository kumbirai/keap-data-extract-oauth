# 4. BI reporting and joins (Revolut + Keap + Stripe)

## 4.1 Source-of-truth matrix

| Dataset | Typical grain | Use for |
|---------|----------------|---------|
| **Keap** — [`orders`](../../src/models/entity_models.py), [`order_payments`](../../src/models/entity_models.py), [`order_transactions`](../../src/models/entity_models.py) | CRM / commerce | Recognized revenue in Keap, fulfillment, internal payment records |
| **`stripe_charges`** / **`stripe_balance_transactions`** | Gateway / ledger (Stripe) | Stripe-specific reconciliation and subscription billing when Stripe is the PSP |
| **`revolut_accounts`** | Revolut account / wallet | Scoping dashboards, balances, currency |
| **`revolut_transactions`** | Revolut transaction | **Revolut Business** cash and card movements, fees, transfers, exchanges as modeled by Revolut |

**Double-counting risk**

- **Keap vs Revolut**: A single customer payment might be recorded in Keap **and** appear as a Revolut transaction if Keap records the order while Revolut captures the card. **Do not** sum both as one revenue metric without explicit rules.
- **Stripe vs Revolut**: If the business uses **both** PSPs, each transaction set is valid **for its rail** only unless you maintain a **canonical payment fact** elsewhere.
- **Gross vs net vs fees**: **`amount`** on a transaction may be gross; **fees** may be separate rows or fields. Define **one primary measure per visual** (e.g. “accepted card gross” vs “fees” vs “estimated net”).

## 4.2 Definition: accepted Revolut payments

**Baseline rule** (must be **ratified** by finance and validated against current API enums):

- **`state = 'completed'`** (or the API’s equivalent terminal success state).
- **Type allow-list** — typically includes **`card_payment`** for card-acquiring; **exclude** internal transfers unless the report is explicitly “all completed money-in.”

Document the approved **`type` allow-list** in your semantic layer or a shared **data dictionary** so dashboards do not drift.

## 4.3 Joins within Revolut

### Transaction → account

```sql
SELECT t.id, t.type, t.state, t.amount, t.currency, t.completed_at,
       a.name AS account_name, a.currency AS account_currency
FROM revolut_transactions t
LEFT JOIN revolut_accounts a ON a.id = t.account_id;
```

### Fee row → related payment (if `related_transaction_id` is populated)

```sql
SELECT fee.id AS fee_id, fee.amount AS fee_amount, fee.currency AS fee_currency,
       pay.id AS payment_id, pay.type AS payment_type, pay.amount AS payment_amount
FROM revolut_transactions fee
JOIN revolut_transactions pay ON pay.id = fee.related_transaction_id
WHERE fee.type = 'fee';  -- illustrative; confirm API type strings
```

If the API does **not** expose a stable link column, use **`raw_payload`** only with **restricted** access and parse in a controlled ELT step—not ad hoc in every report.

## 4.4 Accepted payments (example sketch)

```sql
-- Illustrative only: confirm state/type literals against Revolut API documentation
SELECT
  DATE(completed_at AT TIME ZONE 'UTC') AS payment_date_utc,
  account_id,
  currency,
  SUM(amount) AS accepted_gross_minor_units,
  COUNT(*) AS accepted_payment_count
FROM revolut_transactions
WHERE state = 'completed'
  AND type IN ('card_payment')  -- extend per business sign-off
  AND completed_at IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 2, 3;
```

Convert **minor units** to decimal in BI or using `amount / 100.0` for two-decimal currencies only when that matches the currency’s minor units.

## 4.5 Optional join paths to Keap (best effort)

None of these are guaranteed unless your integration stores stable correlation ids.

### Reference in description or metadata

If Revolut transactions include **order references** in `description` or `metadata`, you may build **fuzzy** or **manual** mapping tables. Treat such joins as **low confidence** unless validated.

### Stripe metadata parity

If the organization uses Stripe for some flows and Revolut for others, maintain a **bridge table** keyed by internal `order_id` with optional `stripe_charge_id` and `revolut_transaction_id` populated by application logic—not by guessing in SQL.

## 4.6 Reporting checklist

- [ ] **Signed-off** `type` and `state` filters for “accepted payment”
- [ ] **Time zone** convention documented (UTC in warehouse vs local reporting)
- [ ] **Currency** handling: one currency per row vs multi-currency dashboards
- [ ] **Fee** logic documented (scalar vs separate rows)
- [ ] **Refresh cadence** communicated to consumers

## 4.7 References

- [01-scope-and-requirements.md](01-scope-and-requirements.md) — definitions and sync policy
- [02-schema-design.md](02-schema-design.md) — column list
- [Stripe BI reporting](../stripe/04-bi-reporting-and-joins.md) — parallel gateway guidance
