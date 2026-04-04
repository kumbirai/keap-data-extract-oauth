# 1. Scope and requirements (Revolut BI milestone)

## 1.1 Business objectives

| Objective | Description | Success criteria (examples) |
|-----------|-------------|-----------------------------|
| **Accepted payments reporting** | Finance and operations can report volume and value of **successfully completed** Revolut payment activity suitable for management and reconciliation views. | Dashboards and SQL can filter **accepted** payments with a documented, signed-off rule (state, type, and account scope). |
| **Local transaction history** | An **up-to-date** copy of Revolut **transactions** (including types that represent **charges and fees**) is stored in PostgreSQL for BI tools (e.g. Power BI) without relying on ad-hoc CSV export. | Scheduled or on-demand extract refreshes tables within agreed **latency**; historical backfill completes for the agreed **lookback window**. |
| **Fee and charge visibility** | Reports can attribute **fees** and **card/payment charges** alongside gross amounts, consistent with how the Revolut API models those movements (embedded fields, related transaction rows, or dedicated types). | BI semantic layer documents one **primary metric per chart** (gross vs net vs fee-only) to avoid double counting. |

## 1.2 Stakeholders

- **Finance / reconciliation**: Accepted payments, refunds/reversals, fees, currency and account breakdowns.
- **BI / analytics**: Star-schema–friendly tables, stable keys, refresh cadence.
- **Operations**: Monitoring extract health, data freshness, and incident response.
- **Compliance / security** (as applicable): Retention, access control, and minimization of sensitive card or personal data (see [§1.8](#18-security-logging-and-data-minimization) and [Security considerations](../06-security-considerations.md)).

## 1.3 Definitions

- **Revolut transaction (API grain)**: One row returned by the Business API for a transaction resource (unique **`id`** from Revolut). This is the **primary fact grain** for `revolut_transactions` unless a future design normalizes legs explicitly.
- **Accepted payment (reporting)** — *requires business sign-off*: For card-acquiring style activity, the baseline filter is **`state = completed`** combined with transaction **`type`** values that represent inbound card or merchant payment flows (e.g. **`card_payment`** where applicable). The exact **allow-list of `type` values** must be confirmed against [Revolut transaction documentation](https://developer.revolut.com/docs/business/transactions) and approved by finance; do not assume all `completed` rows are “revenue.”
- **Charge**: In Revolut terms, treat **charges** as transaction rows or amount fields that represent money movement for a payment or fee as documented by the API response (implementation maps fields in [02-schema-design.md](02-schema-design.md)).
- **Fee**: Fees may appear as **separate transactions**, **nested structures**, or **deductions** depending on type; the extract must persist enough structure (columns + optional `raw_payload`) for BI to report fees without losing auditability.

## 1.4 In scope (Revolut BI milestone)

### Dimensions

- **Accounts** (`revolut_accounts`): Business accounts or wallets the API exposes (id, name, currency, state, balances if available). Used to scope transaction lists and dashboards.

### Facts

- **Transactions** (`revolut_transactions`): Full history required for BI within the agreed window, including:
  - Payment-like types (e.g. card payments) across **pending → completed** (or **declined / failed / reverted**) lifecycle as the API reports.
  - **Transfers**, **exchanges**, and other types needed for cash-movement reporting when the business requests them (confirm list with stakeholders).
  - **Fee-related** representation per API (see [02-schema-design.md](02-schema-design.md)).

### Cross-cutting

- **Idempotency**: Primary key = Revolut transaction **`id`**. Repeated loads **upsert** so mutable fields (`state`, amounts, timestamps) match latest API truth.
- **Incremental synchronization**: Time-windowed extraction plus **lookback** or re-fetch policy for state drift (see [§1.6](#16-incremental-synchronization)).
- **Credentials**: Documented setup for certificates, JWT client assertion, and tokens in [05-access-keys-and-credentials.md](05-access-keys-and-credentials.md).

## 1.5 Out of scope (this doc set)

See [README.md](README.md) **Explicit exclusions**. Additionally:

- Building **payment initiation** or **write** workflows inside this extractor.
- **Guaranteed** automated join keys from Revolut transactions to Keap orders or Stripe objects unless the organization standardizes **reference metadata** or **manual mapping** tables (optional future work).

## 1.6 Incremental synchronization

Revolut list endpoints typically support **date range** filters (e.g. `from` / `to` in ISO 8601) and **pagination** with a maximum page size per request. Lists are often sorted by **`created_at`** in reverse chronological order. **Implementation must match the current API reference** ([Retrieve a list of transactions](https://developer.revolut.com/docs/business/get-transactions)).

### State drift

A transaction created in an earlier run can later move from **pending** to **completed**, **declined**, **failed**, or **reverted**. A strategy that only ingests **new** rows by forward time window **misses** updates to older ids unless supplemented.

**Recommended hybrid policy**

1. **Forward window**: For each account (or global run), advance a **`from` watermark** stored per `entity_type` in `extraction_state` (or dedicated fields—see [03-extract-integration.md](03-extract-integration.md)).
2. **Lookback refresh**: Re-query a **bounded lookback** period (configurable days, e.g. `REVOLUT_TRANSACTION_LOOKBACK_DAYS`) overlapping the last successful window and **upsert** by transaction `id`.
3. **Optional deep reconciliation**: Periodic job to re-fetch known **open-state** ids or a full historical backfill in maintenance windows for small datasets.

Document the chosen policy in runbooks and environment defaults.

### Pagination vs Keap

Keap uses numeric offsets in [`ExtractionState.api_offset`](../../src/models/oauth_models.py). Revolut pagination is **not** the same model. **Do not** overload `api_offset` for Revolut without a documented encoding; prefer **dedicated checkpoint fields** (e.g. `checkpoint_json` or `pagination_cursor`) as described in [03-extract-integration.md](03-extract-integration.md).

## 1.7 Non-functional requirements

| Area | Requirement |
|------|----------------|
| **Availability** | Extract fails gracefully when Revolut is unavailable; retries with backoff on rate limits and 5xx responses. |
| **Performance** | Respect API rate limits; use maximum safe `count` per page; parallelize per account only if documented safe. |
| **Freshness** | Agree SLA with business (e.g. “lag under one hour” for near–real-time needs vs daily batch). |
| **Observability** | Structured logs: run id, account id, page counts, errors **without** secrets or full PAN. |
| **Portability** | Configuration via environment variables; no secrets in repository (see [05-access-keys-and-credentials.md](05-access-keys-and-credentials.md)). |

## 1.8 Security, logging, and data minimization

- **Scopes**: Use **READ** (and sub-scopes the API offers for read-only access) for extract keys; avoid **WRITE**, **PAY**, or **READ_SENSITIVE_CARD_DATA** unless a separate risk assessment requires them.
- **Logging**: Never log client assertion JWTs, access tokens, refresh tokens, private keys, full card numbers, or CVV. If `raw_payload` is stored in the database, restrict DB roles and BI connectivity.
- **Alignment**: Follow [Security considerations](../06-security-considerations.md) and organizational data-classification policy.

## 1.9 Solution architecture alignment

- **Hexagonal / ports and adapters**: Revolut HTTP and token exchange live behind an **adapter**; orchestration (`run_revolut_extract`) coordinates use cases without embedding Revolut in [`KeapClient`](../../src/api/keap_client.py).
- **CQRS / events** (optional later): Batch extract is the **query-side** sync into the warehouse; domain events are out of scope unless the product adds real-time notification ingestion.

## 1.10 Idempotency summary

| Table | PK | Upsert goal |
|-------|-----|-------------|
| `revolut_accounts` | Revolut account `id` | Balances, name, state, currency |
| `revolut_transactions` | Revolut transaction `id` | State, amounts, fee-related fields, timestamps |

## 1.11 References

- [Revolut Business API](https://developer.revolut.com/docs/business/business-api/)
- [Transactions](https://developer.revolut.com/docs/business/transactions)
- [Retrieve a list of transactions](https://developer.revolut.com/docs/business/get-transactions)
- [Retrieve a transaction](https://developer.revolut.com/docs/business/get-transaction)
- [Accounts and transactions syncing (guide)](https://developer.revolut.com/docs/guides/manage-accounts/use-cases/accounts-and-transactions-syncing)
