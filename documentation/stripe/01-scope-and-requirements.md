# 1. Scope and requirements (Stripe BI milestone)

## 1.1 In scope (Stripe BI milestone)

Objects are retrieved via the Stripe API (REST or the official Stripe Python SDK) and persisted for BI, reconciliation, and subscription or invoice reporting. Grouping below matches [02-schema-design.md](02-schema-design.md) and [03-extract-integration.md](03-extract-integration.md).

### Dimensions (normalized catalog)

Persist **product catalog surfaces** as relational dimensions—not every Stripe Catalog API object type is required unless you extend the extract. Baseline tables:

- **Products** (`prod_*`): names, descriptions, active flag, default price reference as exposed by the API.
- **Prices** (`price_*`): currency, unit amount or tier hints, recurring vs one-time, linkage to product id.
- **Coupons** (`coupon_*` or promotion codes if you model them): percent/amount off, duration, redemption constraints for discount reporting.

Rationale: invoice and subscription reporting often needs **human-readable offer and SKU context** without parsing nested JSON in every report.

### Facts (first-class tables)

- **`stripe_charges`** (`ch_*`): primary payment-attempt fact—amounts, status, refunds aggregate, failure fields, links to customer, invoice, payment intent, balance transaction.
- **`stripe_payment_intents`** (`pi_*`): intent lifecycle before and alongside confirmation; useful when charges are not the only payment surface or when reconciling incomplete flows.
- **`stripe_invoices`** (`in_*`): billing document grain for subscription and one-off invoice revenue views.
- **`stripe_subscriptions`** (`sub_*`): recurring relationship grain (status, current period, customer, items summary fields as needed for BI).

Rationale: charges alone do not carry full **subscription or invoice semantics**; separate tables match how Stripe models billing and avoid overloading `stripe_charges` with duplicated invoice payloads.

### Settlement and cash movement

- **`stripe_balance_transactions`** (`txn_*`): dedicated reporting table for **net amounts, fees, currency, type**, and linkage to source objects (charge, refund, payout, transfer, etc.) as the API exposes.

**Payouts** (`po_*`) and **transfers** (`tr_*`): in this milestone, treat them as **first-class tables when list/retrieve is in the extract** (`stripe_payouts`, `stripe_transfers`), or as ids reachable **only** via balance transaction source fields. [02-schema-design.md](02-schema-design.md) defines one consistent approach: optional `stripe_payouts` / `stripe_transfers` rows for payout reconciliation dashboards, always joinable from balance transactions when ids exist.

### Refunds (child dataset)

- **`stripe_refunds`** (`re_*`): one row per refund object, linked to **`charge_id`** (and **`payment_intent_id`** when the API provides it). Use alongside charge-level `amount_refunded` for **refund-line** reporting and timing.

### Idempotency (all groups)

- **Primary key** for each table: Stripe object **`id`** for that resource type (`ch_*`, `pi_*`, `in_*`, `sub_*`, `re_*`, `txn_*`, `po_*`, `tr_*`, `prod_*`, `price_*`, `coupon_*`, etc.).
- **Upsert semantics**: repeated loads must update existing rows so mutable fields (status, amounts, refund totals, subscription state) match the latest API truth.

## 1.2 Out of scope (this doc set)

See [README.md](README.md) **Explicit exclusions** (e.g. Tax/Radar-focused datasets, normalized invoice line items unless added later).

## 1.3 Credentials and configuration

- **Environment variable**: `STRIPE_API_KEY` (or equivalent name agreed in implementation), loaded the same way as other secrets in [`.env.example`](../../.env.example) (copy to `.env`, never commit secrets).
- **Restricted keys**: Prefer a [restricted API key](https://docs.stripe.com/keys) with **minimum read access** to every resource the pipeline lists or retrieves: Charges, PaymentIntents, Invoices, Subscriptions, Products, Prices, Coupons (and Promotion Codes if loaded), Refunds, Balance Transactions, Payouts, and Transfers if those tables are enabled. Add read scope only for related objects you actually call; avoid wildcard write permissions on extract keys.
- **Logging**: Never log the API key, full payment method details, or full raw payloads at INFO in shared logs. If `raw_payload` is stored in the database, treat it as sensitive and restrict DB access accordingly.

## 1.4 Stripe Connect (optional)

If the business uses **Stripe Connect** and objects belong to connected accounts:

- Document whether extraction runs against the **platform** or **connected accounts** and how the **`Stripe-Account`** header is chosen per run or per account loop.
- The schema should carry an optional **`stripe_account_id`** (or equivalent) on **each Stripe fact and dimension row** loaded in that context so multi-account reporting and debugging stay consistent.

If Connect is not used, the column remains null and can be omitted from filters.

## 1.5 Incremental synchronization

### Charges (detail retained)

Listing charges supports filtering on **`created`** (lower bound Unix timestamp). There is **no** general “updated since” filter on the Charges list that matches Keap’s `since` pattern for all field changes.

**Refund and status drift**: a charge created long ago can still change (`amount_refunded`, `refunded`, `status`, failure fields). Incremental fetch using only **`created[gte]`** misses those updates on older rows unless you refresh another way.

**Recommended hybrid policy for charges**:

1. **Incremental window**: fetch with **`created[gte]`** from a watermark in `extraction_state` for `stripe_charges`.
2. **Refresh strategy** (pick at least one): bounded lookback re-fetch, periodic full cursor backfill with upsert, or Events/webhooks for updates.

Document the chosen policy in runbooks.

### Other list APIs (subscriptions, invoices, payment intents, catalog, refunds, balance transactions)

Stripe list endpoints commonly support **`created`** lower bounds and **cursor** pagination (`starting_after`). Many resources also **mutate after creation** (e.g. invoice `status`, subscription `status`, payment intent `status`).

Apply the **same pattern** unless you standardize on webhooks:

- Use **`created[gte]`** watermarks per **`entity_type`** in `extraction_state` for incremental discovery of new rows.
- Add **bounded lookback** or **periodic full re-list** with upsert for objects where status and amounts drift, or consume **Events** / webhooks in a later implementation.

**Refunds**: list by `created` and/or tie refresh to charge lookback so refund rows align with updated charges.

**Balance transactions**: often high volume; prefer incremental `created` windows plus reconciliation runs that re-fetch recent `txn_*` ids seen on charges and refunds.

### Pagination vs Keap

Keap uses numeric offsets in [`ExtractionState.api_offset`](../../src/models/oauth_models.py). Stripe uses **cursors**. Do not overload `api_offset` for Stripe without a documented encoding; see [03-extract-integration.md](03-extract-integration.md).

## 1.6 Idempotency and consistency (summary)

| Group | PK pattern | Upsert goal |
|--------|------------|-------------|
| Dimensions | `prod_*`, `price_*`, `coupon_*` | Reflect active flags, amounts, names |
| Facts | `ch_*`, `pi_*`, `in_*`, `sub_*` | Reflect status, amounts, linkage ids |
| Settlement | `txn_*`, optional `po_*`, `tr_*` | Reflect fees, net, payout linkage |
| Refunds | `re_*` | Reflect status, amount, charge link |

## 1.7 References

- [Stripe API: Charge](https://docs.stripe.com/api/charges/object) · [List charges](https://docs.stripe.com/api/charges/list)
- [PaymentIntent](https://docs.stripe.com/api/payment_intents/object) · [Invoice](https://docs.stripe.com/api/invoices/object) · [Subscription](https://docs.stripe.com/api/subscriptions/object)
- [Product](https://docs.stripe.com/api/products/object) · [Price](https://docs.stripe.com/api/prices/object) · [Coupon](https://docs.stripe.com/api/coupons/object)
- [Refund](https://docs.stripe.com/api/refunds/object) · [Balance transaction](https://docs.stripe.com/api/balance_transactions/object)
