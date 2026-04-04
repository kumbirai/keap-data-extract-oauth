# 2. Schema design (Revolut Merchant API BI)

## 2.1 Design principles

- All tables share the **`revolut_merchant_`** prefix to distinguish from Revolut Business (`revolut_`) and Stripe (`stripe_`) tables.
- **No PostgreSQL foreign keys** to other systems (Keap, Stripe, Revolut Business); all cross-table links are **logical** joins on application-level identifiers.
- **`id` is always TEXT** matching the Revolut API string identifier. Do not cast to UUID unless the API guarantees UUID format.
- Common ETL columns on every table: `raw_payload JSONB` (optional), `loaded_at TIMESTAMPTZ`, `updated_at_etl TIMESTAMPTZ`.
- `loaded_at` is set on first insert and **never updated**. `updated_at_etl` is refreshed on every upsert.
- API timestamp fields (e.g. `created_at`, `updated_at`) are mapped to `TIMESTAMPTZ` columns with `UTC` normalisation in the mapper.

## 2.2 Primary fact: `revolut_merchant_orders`

One row per Revolut Merchant order `id`.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | TEXT | PK | Revolut order id |
| `token` | TEXT | Y | Public checkout token |
| `type` | TEXT | Y | e.g. `payment` |
| `state` | TEXT | Y | `pending` / `processing` / `completed` / `authorised` / `cancelled` / `failed` |
| `created_at` | TIMESTAMPTZ | Y | API creation time |
| `updated_at` | TIMESTAMPTZ | Y | API last-update time |
| `completed_at` | TIMESTAMPTZ | Y | When order reached terminal state |
| `amount` | BIGINT | Y | Order amount in minor currency units |
| `currency` | TEXT | Y | ISO 4217 |
| `outstanding_amount` | BIGINT | Y | Remaining uncaptured amount |
| `capture_mode` | TEXT | Y | `automatic` / `manual` |
| `cancel_authorised_only` | BOOLEAN | Y | |
| `customer_id` | TEXT | Y | Revolut customer id (logical FK → `revolut_merchant_customers.id`) |
| `email` | TEXT | Y | Order-level email (may differ from customer email) |
| `description` | TEXT | Y | Merchant-supplied description |
| `merchant_order_ext_ref` | TEXT | Y | Merchant's own order reference |
| `metadata` | JSONB | Y | Key-value metadata from API |
| `raw_payload` | JSONB | Y | Full API response; restricted access |
| `loaded_at` | TIMESTAMPTZ | N | First ETL insert |
| `updated_at_etl` | TIMESTAMPTZ | N | Last ETL upsert |

### Indexes (`revolut_merchant_orders`)

| Index | Columns | Purpose |
|-------|---------|---------|
| Primary | `(id)` | Upsert lookup |
| `idx_rmo_state` | `(state)` | Completed vs failed dashboards |
| `idx_rmo_created_at` | `(created_at DESC)` | Time-series queries |
| `idx_rmo_customer_id` | `(customer_id)` | Customer order history |
| `idx_rmo_currency_created` | `(currency, created_at DESC)` | Per-currency revenue |

## 2.3 Fact: `revolut_merchant_order_payments`

One row per payment attempt against an order. An order may have multiple payment attempts (e.g. first attempt declined, second succeeds).

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | TEXT | PK | Payment attempt id |
| `order_id` | TEXT | Y | Logical FK → `revolut_merchant_orders.id` |
| `state` | TEXT | Y | `pending` / `authorised` / `captured` / `declined` / `failed` / `refunded` |
| `amount` | BIGINT | Y | Amount in minor units |
| `currency` | TEXT | Y | ISO 4217 |
| `payment_method_type` | TEXT | Y | `card` / `revolut_pay` / etc. |
| `card_bin` | TEXT | Y | First 6 digits (BIN) |
| `card_last_four` | TEXT | Y | Last 4 digits |
| `card_brand` | TEXT | Y | `VISA` / `MASTERCARD` / etc. |
| `card_funding_type` | TEXT | Y | `debit` / `credit` / `prepaid` |
| `card_country` | TEXT | Y | ISO 3166-1 alpha-2 issuing country |
| `arn` | TEXT | Y | Acquirer Reference Number (23-digit) for chargebacks |
| `bank_message` | TEXT | Y | Issuer response message |
| `decline_reason` | TEXT | Y | Decline code / reason |
| `created_at` | TIMESTAMPTZ | Y | |
| `raw_payload` | JSONB | Y | Full payment object |
| `loaded_at` | TIMESTAMPTZ | N | |
| `updated_at_etl` | TIMESTAMPTZ | N | |

### Indexes (`revolut_merchant_order_payments`)

| Index | Columns | Purpose |
|-------|---------|---------|
| Primary | `(id)` | |
| `idx_rmop_order_id` | `(order_id)` | Payment attempts per order |
| `idx_rmop_state` | `(state)` | Captured vs declined analysis |
| `idx_rmop_created_at` | `(created_at DESC)` | Timeline |

## 2.4 Dimension: `revolut_merchant_customers`

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | TEXT | PK | Revolut customer id |
| `email` | TEXT | Y | PII — restrict access |
| `phone` | TEXT | Y | PII |
| `full_name` | TEXT | Y | PII |
| `business_name` | TEXT | Y | B2B customers |
| `created_at` | TIMESTAMPTZ | Y | |
| `updated_at` | TIMESTAMPTZ | Y | API last-update |
| `raw_payload` | JSONB | Y | |
| `loaded_at` | TIMESTAMPTZ | N | |
| `updated_at_etl` | TIMESTAMPTZ | N | |

### Indexes (`revolut_merchant_customers`)

| Index | Columns | Purpose |
|-------|---------|---------|
| Primary | `(id)` | |
| `idx_rmc_email` | `(email)` | Customer lookup by email |
| `idx_rmc_created_at` | `(created_at DESC)` | Customer acquisition timeline |

## 2.5 Dimension: `revolut_merchant_payment_methods`

One row per stored payment method per customer.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | TEXT | PK | Payment method id |
| `customer_id` | TEXT | Y | Logical FK → `revolut_merchant_customers.id` |
| `type` | TEXT | Y | `card` / `revolut_pay` / etc. |
| `card_bin` | TEXT | Y | |
| `card_last_four` | TEXT | Y | |
| `card_expiry_month` | INTEGER | Y | |
| `card_expiry_year` | INTEGER | Y | |
| `card_cardholder_name` | TEXT | Y | PII |
| `card_brand` | TEXT | Y | |
| `card_funding_type` | TEXT | Y | |
| `card_issuer` | TEXT | Y | Issuing bank name |
| `billing_street_line_1` | TEXT | Y | PII |
| `billing_city` | TEXT | Y | |
| `billing_postcode` | TEXT | Y | |
| `billing_country` | TEXT | Y | ISO 3166-1 alpha-2 |
| `raw_payload` | JSONB | Y | |
| `loaded_at` | TIMESTAMPTZ | N | |
| `updated_at_etl` | TIMESTAMPTZ | N | |

### Indexes (`revolut_merchant_payment_methods`)

| Index | Columns | Purpose |
|-------|---------|---------|
| Primary | `(id)` | |
| `idx_rmpm_customer_id` | `(customer_id)` | Methods per customer |
| `idx_rmpm_type` | `(type)` | Card vs Revolut Pay split |
| `idx_rmpm_card_brand` | `(card_brand)` | Network analysis |

## 2.6 Fact: `revolut_merchant_disputes`

One row per chargeback / dispute.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | TEXT | PK | Dispute id |
| `order_id` | TEXT | Y | Logical FK → `revolut_merchant_orders.id` |
| `state` | TEXT | Y | `needs_response` / `under_review` / `won` / `lost` |
| `reason` | TEXT | Y | Dispute reason code |
| `amount` | BIGINT | Y | Disputed amount in minor units |
| `currency` | TEXT | Y | ISO 4217 |
| `created_at` | TIMESTAMPTZ | Y | |
| `updated_at` | TIMESTAMPTZ | Y | |
| `due_at` | TIMESTAMPTZ | Y | Response deadline |
| `raw_payload` | JSONB | Y | |
| `loaded_at` | TIMESTAMPTZ | N | |
| `updated_at_etl` | TIMESTAMPTZ | N | |

### Indexes (`revolut_merchant_disputes`)

| Index | Columns | Purpose |
|-------|---------|---------|
| Primary | `(id)` | |
| `idx_rmd_state` | `(state)` | Open vs resolved |
| `idx_rmd_order_id` | `(order_id)` | Dispute per order join |
| `idx_rmd_created_at` | `(created_at DESC)` | Timeline |

## 2.7 Dimension: `revolut_merchant_locations`

Store / terminal locations associated with the merchant account.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | TEXT | PK | Location id |
| `name` | TEXT | Y | Human-readable label |
| `type` | TEXT | Y | e.g. `store` / `online` |
| `address_line_1` | TEXT | Y | |
| `address_city` | TEXT | Y | |
| `address_country` | TEXT | Y | ISO 3166-1 alpha-2 |
| `currency` | TEXT | Y | Default currency |
| `raw_payload` | JSONB | Y | |
| `loaded_at` | TIMESTAMPTZ | N | |
| `updated_at_etl` | TIMESTAMPTZ | N | |

### Indexes (`revolut_merchant_locations`)

| Index | Columns | Purpose |
|-------|---------|---------|
| Primary | `(id)` | |
| `idx_rml_currency` | `(currency)` | |
| `idx_rml_type` | `(type)` | |

## 2.8 Relationship summary

```
revolut_merchant_customers (1) ──< revolut_merchant_orders (many)
revolut_merchant_customers (1) ──< revolut_merchant_payment_methods (many)
revolut_merchant_orders    (1) ──< revolut_merchant_order_payments (many)
revolut_merchant_orders    (1) ──< revolut_merchant_disputes (many, typically 0-1)
```

All relationships are **logical** (no PostgreSQL FK constraints enforced) to keep the extract append-safe when customers or orders arrive out of order.

## 2.9 Consistency with other tables

- Revolut Business (`revolut_accounts`, `revolut_transactions`) is independent — different API, different schema prefix.
- Stripe tables (`stripe_charges`, `stripe_customers`, etc.) cover the Stripe payment rail. The same real-world customer may appear in both `stripe_customers` and `revolut_merchant_customers`; do **not** assume shared identifiers. See [04-bi-reporting-and-joins.md](04-bi-reporting-and-joins.md).
- Keap tables remain the source for CRM contacts and internal order records.

## 2.10 References

- [Revolut Merchant API — Orders](https://developer.revolut.com/docs/merchant/orders)
- [Revolut Merchant API — Customers](https://developer.revolut.com/docs/merchant/customers)
- [Revolut Merchant API — Disputes](https://developer.revolut.com/docs/merchant/disputes)
- [Sprint-01 schema design](../sprint-01/02-schema-design.md)
