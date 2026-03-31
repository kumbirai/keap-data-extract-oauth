# 1. Scope and requirements (Stripe BI sprint-02)

## 1.1 Context: the sprint-01 gap

Sprint-01 gave every Stripe fact table a `customer_id` (`cus_*`) column but deferred the matching
dimension table. The most visible consequence is in the settlement path:

```
stripe_balance_transactions.source_id
  → stripe_charges.id
      → stripe_charges.customer_id
          → ??? (no customer dimension table)
```

Until `stripe_customers` exists, any BI report that needs customer name, email, or currency
alongside a balance transaction or refund must either rely on `raw_payload` or do an ad-hoc API
lookup. Sprint-02 closes this gap.

Sprint-01 also stored invoice line detail in `stripe_invoices.raw_payload` and subscription items
in `stripe_subscriptions.raw_payload`. As report complexity grows, querying nested JSON is fragile
and slow; normalized tables are required.

## 1.2 In-scope entities

### 1.2.1 `stripe_customers` (new dimension)

- Top-level list API: `stripe.Customer.list()`
- One row per customer. Mutable fields include `email`, `name`, `balance`, `delinquent`, `default_source`.
- Required before all sprint-02 facts (disputes, promotion codes, credit notes) because they carry
  `customer_id`.
- **Load order priority**: first in sprint-02, loaded immediately after sprint-01 catalog
  dimensions (`stripe_products`, `stripe_prices`, `stripe_coupons`).

### 1.2.2 `stripe_invoice_line_items` (child list — normalization)

- Child list API: `stripe.Invoice.list_line_items(invoice_id)` — there is **no** top-level
  `stripe.InvoiceLineItem.list()`.
- Extraction pattern differs from all sprint-01 entities: the extractor must query
  `stripe_invoices.id` from the database, then call the child API per invoice.
- Natural `id` field is `il_*`.
- Incremental: re-fetch line items for invoices created or updated within the lookback window,
  plus all invoices in a mutable status (`draft`, `open`).
- Idempotency: upsert on `id`; line items are stable once the invoice is `paid` or `void` but
  may change while `draft` or `open`.

### 1.2.3 `stripe_subscription_items` (child list — normalization)

- Child list API: `stripe.SubscriptionItem.list(subscription=sub_id)`.
- Same parent-iteration extraction pattern as invoice line items.
- Natural `id` field is `si_*`.
- Incremental: re-fetch items for subscriptions whose `current_period_start` is within the
  lookback window or whose status is `active`, `past_due`, or `trialing`.

### 1.2.4 `stripe_disputes` (fact — top-level list)

- Top-level list API: `stripe.Dispute.list()` supports `created` filtering.
- Links to `stripe_charges.id` via `charge_id` and optionally to `stripe_payment_intents.id`.
- `status` values: `warning_needs_response`, `needs_response`, `under_review`,
  `charge_refunded`, `won`, `lost`.
- Disputes mutate significantly over their lifecycle (evidence submission, review outcome);
  standard lookback re-fetch applies.

### 1.2.5 `stripe_promotion_codes` (dimension — top-level list)

- Top-level list API: `stripe.PromotionCode.list()`.
- Links to `stripe_coupons.id` via `coupon_id`.
- Links optionally to `stripe_customers.id` via `customer_id` (customer-restricted codes).
- Relatively slow-changing; still needs upsert for `active` and `times_redeemed` mutations.

### 1.2.6 `stripe_credit_notes` (fact — top-level list)

- Top-level list API: `stripe.CreditNote.list()`.
- Links to `stripe_invoices.id` via `invoice_id` and `stripe_customers.id` via `customer_id`.
- Semantically distinct from refunds: a credit note adjusts an invoice; a refund adjusts a
  charge. A credit note may or may not trigger a cash refund (`refund_id` is nullable).

## 1.3 Out of scope (sprint-02)

- Credit note line items (`stripe.CreditNoteLineItem`) — may be added in a later sprint.
- Subscription schedules.
- Stripe Tax objects, Radar fraud analytics, Capital products.
- Payment links, Checkout sessions.
- Webhook ingestion as a real-time update mechanism (documented as a future option only).
- Discount objects as a first-class table (discount attribution via `raw_payload` until added).

## 1.4 Credentials and configuration

All credential rules from sprint-01 §1.3 apply unchanged. The restricted API key must
additionally have **read scope** for:

- `Customer` (list, retrieve)
- `Dispute` (list, retrieve)
- `PromotionCode` (list, retrieve)
- `CreditNote` (list, retrieve)
- `InvoiceLineItem` (list via parent invoice)
- `SubscriptionItem` (list via parent subscription)

No new environment variables are required for sprint-02.

## 1.5 Incremental synchronization

### Top-level entities (customers, disputes, promotion codes, credit notes)

Follow the sprint-01 hybrid policy:
- `created[gte]` watermark from `checkpoint_json.accounts[key].max_created_unix` minus
  `STRIPE_CHARGE_LOOKBACK_DAYS * 86400` seconds.
- Mutations after creation (e.g. dispute status transitions, delinquent flag on customers) are
  caught by the lookback window.

### Child entities (invoice line items, subscription items)

Child list APIs do not expose a `created` filter on the child; only the parent can be
time-filtered. **Recommended approach**:

1. Query the database for parent ids within the lookback window **plus** parents in mutable
   statuses:

   ```sql
   -- Invoice line items: parents to refresh
   SELECT id FROM stripe_invoices
   WHERE created >= :watermark
      OR status IN ('draft', 'open')

   -- Subscription items: parents to refresh
   SELECT id FROM stripe_subscriptions
   WHERE current_period_start >= :watermark
      OR status IN ('active', 'past_due', 'trialing')
   ```

2. For each qualifying parent id, call the child list API and upsert all returned rows.

3. Checkpoints for child entities track the watermark used for parent selection plus a
   `last_parent_id` cursor so a long run can resume without restarting from the beginning.

**Full initial load**: On first run (no checkpoint), query all parent ids. For very large parent
counts, process in batches of `settings.list_limit` parents and save the `last_parent_id` to
`checkpoint_json` after each batch so a restart resumes at the last completed parent.

## 1.6 Idempotency summary

| Entity | PK | Mutable after creation? | Lookback / refresh strategy |
|--------|----|-----------------------|------------------------------|
| `stripe_customers` | `cus_*` | Yes (email, balance, delinquent) | `created[gte]` watermark |
| `stripe_invoice_line_items` | `il_*` | While invoice is `draft`/`open` | Parent invoice status filter |
| `stripe_subscription_items` | `si_*` | Quantity, price can change | Active/past_due/trialing sub filter |
| `stripe_disputes` | `dp_*` | Yes (status, evidence, outcome) | `created[gte]` + lookback |
| `stripe_promotion_codes` | `promo_*` | Yes (active, times_redeemed) | `created[gte]` watermark |
| `stripe_credit_notes` | `cn_*` | Status may change (`issued`→`void`) | `created[gte]` watermark |

Upsert semantics on `id` (primary key) match the sprint-01 pattern in
`src/database/batch_upsert.py`. `loaded_at` is preserved on conflict; all other columns take
the latest API value.

## 1.7 References

- [Stripe API: Customer](https://docs.stripe.com/api/customers/object) · [List](https://docs.stripe.com/api/customers/list)
- [Stripe API: InvoiceLineItem](https://docs.stripe.com/api/invoices/line_item) · [List for invoice](https://docs.stripe.com/api/invoices/invoice_lines)
- [Stripe API: SubscriptionItem](https://docs.stripe.com/api/subscription_items/object) · [List](https://docs.stripe.com/api/subscription_items/list)
- [Stripe API: Dispute](https://docs.stripe.com/api/disputes/object) · [List](https://docs.stripe.com/api/disputes/list)
- [Stripe API: PromotionCode](https://docs.stripe.com/api/promotion_codes/object) · [List](https://docs.stripe.com/api/promotion_codes/list)
- [Stripe API: CreditNote](https://docs.stripe.com/api/credit_notes/object) · [List](https://docs.stripe.com/api/credit_notes/list)
- [Sprint-01 scope and requirements](../sprint-01/01-scope-and-requirements.md)
