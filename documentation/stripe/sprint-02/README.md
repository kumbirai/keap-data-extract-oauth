# Stripe BI sprint-02

This folder extends the sprint-01 Stripe BI extract with six additional entities that close the
primary customer-dimension gap, normalize nested data currently stored in `raw_payload`, and add
chargeback, promotion, and credit-note analytics.

## Sprint-01 baseline

Sprint-01 established the schema and pipeline for:

| Group | Tables |
|-------|--------|
| Dimensions | `stripe_products`, `stripe_prices`, `stripe_coupons` |
| Facts | `stripe_charges`, `stripe_payment_intents`, `stripe_invoices`, `stripe_subscriptions` |
| Settlement | `stripe_balance_transactions`, `stripe_payouts`, `stripe_transfers` |
| Children | `stripe_refunds` |

Sprint-01 deferred `stripe_customers` as optional and stored invoice line items and subscription
items in `raw_payload` on their respective parent tables.

## Sprint-02 additions

| New table | Stripe id prefix | Type | Purpose |
|-----------|-----------------|------|---------|
| `stripe_customers` | `cus_*` | Dimension | Customer dimension; links all facts by name/email |
| `stripe_invoice_line_items` | `il_*` | Child normalization | Normalized invoice line detail |
| `stripe_subscription_items` | `si_*` | Child normalization | Normalized items within subscriptions |
| `stripe_disputes` | `dp_*` | Fact | Chargebacks linked to charges |
| `stripe_promotion_codes` | `promo_*` | Dimension | Promotion codes applying coupons |
| `stripe_credit_notes` | `cn_*` | Fact | Invoice-level credits |

## The primary gap this sprint closes

Every sprint-01 fact table carries a `customer_id` column, but no customer dimension table existed.
The most visible consequence is in the settlement path:

```
stripe_balance_transactions.source_id
  → stripe_charges.id
      → stripe_charges.customer_id
          → ??? (no customer dimension table)
```

After sprint-02, BI developers can write the complete settlement-to-customer chain as a standard
SQL join. See [04-bi-reporting-and-joins.md](04-bi-reporting-and-joins.md) §4.2 Chain 1.

## Documents

| Document | Purpose |
|----------|---------|
| [01-scope-and-requirements.md](01-scope-and-requirements.md) | Sprint-02 scope, customer-dimension gap, child list API pattern, incremental sync |
| [02-schema-design.md](02-schema-design.md) | All six new tables, columns, indexes, full relationship diagram |
| [03-extract-integration.md](03-extract-integration.md) | Load order DAG, child entity extraction design, mapper stubs, SQLAlchemy models |
| [04-bi-reporting-and-joins.md](04-bi-reporting-and-joins.md) | Complete join chains, analytical SQL, updated source-of-truth matrix |

## Architecture (updated)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Extract run                                                          │
│  ┌─────────────────┐   ┌───────────────────────────────────────┐   │
│  │ Keap loaders    │   │ run_stripe_extract                    │   │
│  └────────┬────────┘   └──────────────────┬────────────────────┘   │
└───────────┼────────────────────────────────┼───────────────────────┘
            │                                │
            ▼                                ▼
┌───────────────────────────────────────────────────────────────────┐
│ PostgreSQL keap_db                                                 │
│                                                                    │
│  Keap tables          Stripe sprint-01          Stripe sprint-02  │
│  ─────────────        ─────────────────         ────────────────  │
│  contacts             stripe_products           stripe_customers   │
│  orders               stripe_prices             stripe_invoice_    │
│  order_items          stripe_coupons              _line_items      │
│  ...                  stripe_subscriptions      stripe_sub_        │
│                       stripe_invoices             _items           │
│                       stripe_payment_intents   stripe_disputes     │
│                       stripe_charges           stripe_promotion_   │
│                       stripe_refunds             _codes            │
│                       stripe_balance_          stripe_credit_      │
│                         _transactions            _notes            │
│                       stripe_payouts                               │
│                       stripe_transfers                             │
└───────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                           BI layer / reporting
```

## Related project docs

- [Sprint-01 documentation](../sprint-01/README.md)
- [Database design (Keap core)](../../04-database-design.md)
- [Data extraction design](../../03-data-extraction-design.md)
