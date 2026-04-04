# 2. Schema design (Revolut BI)

## 2.1 Design principles

- **`revolut_transactions` is the primary transaction fact** at the **API object grain** (one row per Revolut transaction `id`).
- **No foreign keys to Keap** unless the organization adds explicit bridge tables or metadata conventions; joins to Keap remain **logical** (see [04-bi-reporting-and-joins.md](04-bi-reporting-and-joins.md)).
- **Revolut cross-table links** (e.g. transaction → account) use nullable **`TEXT`** or **`UUID`** columns matching Revolut identifiers, unless you later add PostgreSQL FK constraints for integrity.
- **Table prefix**: `revolut_` avoids confusion with Keap `order_payments`, `order_transactions`, and `stripe_*` tables.
- **Common optional columns**: `metadata` `JSONB` (if API exposes metadata), `raw_payload` `JSONB`, `loaded_at`, `updated_at`. Treat `raw_payload` as **sensitive** and restrict access.

## 2.2 Dimension: `revolut_accounts`

**Primary key**: `id` — type **`UUID`** or **`TEXT`** consistent with API identifiers for accounts.

### Core columns (map from Revolut account APIs)

| Column | Purpose |
|--------|---------|
| `id` | Revolut account id (PK) |
| `name` | Human-readable label, nullable if not provided |
| `currency` | ISO 4217 code when applicable |
| `state` | e.g. active / inactive per API |
| `balance` | Current balance in minor units if exposed as a scalar; nullable |
| `balance_updated_at` | When balance was observed, nullable |
| `raw_payload` | Optional `JSONB` — full account object |
| `loaded_at` | First insert by this pipeline |
| `updated_at` | Last update by this pipeline |

### Indexes (`revolut_accounts`)

- `(currency)` — filtering dashboards
- `(state)` — active accounts only

**Note**: If the API returns **multiple balance buckets** (available vs pending), prefer storing them in `raw_payload` until the business requires normalized columns.

## 2.3 Primary fact: `revolut_transactions`

**Primary key**: `id` — Revolut transaction id (**UUID** or **TEXT** per API).

### Core columns (map from transaction object)

Exact field names **must** be aligned to the live API response. The table below lists **logical** BI columns; implementation renames to match SQLAlchemy and API casing.

| Column | Purpose |
|--------|---------|
| `id` | Revolut transaction id (PK) |
| `account_id` | Owning account id (FK optional to `revolut_accounts.id`) |
| `type` | API transaction type (e.g. `card_payment`, `transfer`, `exchange`, `fee`) |
| `state` | Lifecycle state (e.g. `pending`, `completed`, `declined`, `failed`, `reverted`, `created`) |
| `amount` | Amount in **minor currency units** (integer/bigint) when the API uses integer minor units |
| `currency` | ISO 4217 |
| `fee_amount` | Total fee in minor units if exposed as a scalar; nullable |
| `fee_currency` | Nullable if fee currency differs |
| `bill_amount` | Optional bill amount if API separates bill vs transaction currency |
| `bill_currency` | Nullable |
| `created_at` | `timestamptz` (UTC) |
| `updated_at` | API `updated_at` if present; else nullable |
| `completed_at` | When payment completed; nullable for non-completed states |

### Merchant and counterparty (optional denormalized columns)

Populate only if the business needs reporting without JSON parsing and **privacy review** allows persistence:

| Column | Purpose |
|--------|---------|
| `merchant_name` | Nullable |
| `merchant_city` | Nullable |
| `merchant_category_code` | Nullable (MCC) |
| `description` | Nullable narrative |
| `counterparty_id` | Nullable Revolut counterparty id if exposed |

If any of these carry **personal data**, prefer leaving them in **`raw_payload`** with restricted access or **omit** per data minimization policy.

### Fee and charge modeling

Revolut may represent fees in one or more of these ways:

1. **Scalar fields** on the payment transaction (`fee_amount`, etc.) — map to columns above.
2. **Separate transaction rows** of type `fee` (or equivalent) **linked** to a parent payment via an id or nested structure in `raw_payload`.
3. **Nested JSON** only — persist in `raw_payload` and extract key scalars to columns when agreed.

**Recommendation**

- Always store **`raw_payload`** (optional but valuable for reconciliation) if security sign-off allows.
- If the API provides a **stable related-transaction id** for fees, add nullable **`related_transaction_id`** on `revolut_transactions` and index it for BI joins from fee rows to payments.

### ETL columns

| Column | Purpose |
|--------|---------|
| `metadata` | `JSONB` if API provides key/value metadata |
| `raw_payload` | Optional `JSONB` — full API object |
| `loaded_at` | First insert by this pipeline |
| `updated_at_etl` | Last upsert by this pipeline (rename if you prefer `updated_at` only on the row for API + ETL combined—pick one convention in implementation) |

Use a single `updated_at` column **only if** you clearly define whether it mirrors API or ETL; many pipelines keep **`loaded_at` / `updated_at`** for ETL only and map API timestamps to explicit `*_at` columns.

### Indexes (`revolut_transactions`)

- `(account_id, created_at DESC)` — per-account time series
- `(state)` — accepted vs failed dashboards
- `(type)` — filter card vs transfer vs fee
- `(completed_at DESC)` where not null — accepted payment reporting
- `(related_transaction_id)` if present — fee-to-payment joins
- `GIN (raw_payload)` only if you query JSON keys in SQL (optional; has storage and maintenance cost)

## 2.4 Optional extensions (future)

- **`revolut_counterparties`**: If the business needs a dimension table built from counterparty list APIs.
- **`revolut_transaction_legs`**: If the API exposes explicit multi-leg splits requiring normalized line grain.

## 2.5 Consistency with Stripe and Keap

- **Stripe** remains the source for card network objects modeled as `stripe_*`. **Revolut** models **Revolut Business** ledger and card-acquiring movements. The same real-world payment might appear in more than one system only if the business uses both rails; reporting must choose **one source per metric** (see [04-bi-reporting-and-joins.md](04-bi-reporting-and-joins.md)).

## 2.6 References

- [Transactions](https://developer.revolut.com/docs/business/transactions)
- [Map transaction data (guide)](https://developer.revolut.com/docs/guides/manage-accounts/accounts-and-transactions/map-transaction-data)
