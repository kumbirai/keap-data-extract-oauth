# 1. Scope and requirements (Revolut Merchant API BI)

## 1.1 Business objectives

- Bring **Revolut Merchant** e-commerce data (orders, payments, customers, disputes) into the same PostgreSQL warehouse as Keap CRM, Stripe, and Revolut Business data.
- Enable BI reporting on **order conversion, payment success rates, chargeback exposure, and customer purchase history** without requiring direct Revolut Merchant API access from reporting tools.
- Provide a single source of truth for accepted Merchant payments, independent of Stripe (which covers a different payment rail).

## 1.2 In scope — GET endpoints

All **read-only** GET endpoints from the Revolut Merchant API that carry BI-relevant data:

| Resource | Endpoint | Notes |
|----------|----------|-------|
| Orders | `GET /api/orders` | Paginated list; primary fact |
| Order (single) | `GET /api/orders/{id}` | Used for targeted reloads |
| Order Payments | `GET /api/orders/{id}/payments` | Fan-out per order |
| Customers | `GET /api/customers` | Dimension |
| Customer (single) | `GET /api/customers/{id}` | |
| Payment Methods | `GET /api/customers/{id}/payment-methods` | Fan-out per customer |
| Disputes | `GET /api/disputes` | Risk fact |
| Dispute (single) | `GET /api/disputes/{id}` | |
| Locations | `GET /api/locations` | Small dimension; full sync |

## 1.3 Out of scope

- **Webhooks** (`GET /api/webhooks`, `GET /api/webhooks/synchronous`): configuration metadata, not analytical data.
- **Write endpoints**: order creation, refunds, dispute responses, webhook registration.
- **Real-time/event-driven ingestion**: out of scope for this sprint; batch scheduled extract assumed.
- **Revolut Business API**: accounts and transactions remain unchanged in Sprint-01 tables.
- **Counterparty master table**: Merchant customer data is stored in `revolut_merchant_customers`; no additional normalisation of card issuer or bank data beyond what the API provides.

## 1.4 Authentication model

The Merchant API uses a **static Bearer API key** — significantly simpler than the Sprint-01 Business API which required OAuth2 + JWT client assertion:

```
Authorization: Bearer <REVOLUT_MERCHANT_API_KEY>
Revolut-Api-Version: 2024-09-01
```

- No token exchange, no JWT signing, no refresh token management.
- One environment variable: `REVOLUT_MERCHANT_API_KEY`.
- Key rotation: replace env var value; no database state to update.

## 1.5 Idempotency

- All tables use **`INSERT … ON CONFLICT (id) DO UPDATE`** (PostgreSQL upsert).
- Re-running the extract over the same window produces identical row counts and field values.
- `loaded_at` records the **first insert time** and is never overwritten on subsequent upserts.
- `updated_at_etl` records the **most recent upsert time** and is always refreshed.

## 1.6 Incremental synchronisation

| Entity | Strategy | Rationale |
|--------|----------|-----------|
| Orders | Time-windowed incremental. Re-fetch last `lookback_days` (default 7) to capture state changes (e.g. pending → completed). | Orders can transition state after creation. |
| Order Payments | Fan-out from each order fetched in the current window. No independent watermark. | Payment list is small per order; piggybacks on order window. |
| Customers | Full sync on first run; `updated_at`-based incremental if API supports filtering; otherwise full re-sync. | Customer volume expected to be manageable. |
| Payment Methods | Fan-out per customer during customer sync. | Methods are tied to customer lifecycle. |
| Disputes | Time-windowed with `lookback_days` re-sync window (default 30 for disputes — state transitions are slow). | Disputes can stay open for weeks. |
| Locations | Full sync each run. Expected < 100 rows; checkpoint overhead not warranted. | |

## 1.7 Security and data minimisation

- **`raw_payload` column**: disabled by default (`REVOLUT_MERCHANT_STORE_RAW_PAYLOAD=false`). Storing it captures full API responses for debugging but may contain PII.
- **Card data**: Only `bin`, `last_four`, `expiry_month`, `expiry_year`, `brand`, `funding_type` stored as columns — sufficient for BI without storing full PANs. Full card objects stored in `raw_payload` only when enabled.
- **Customer PII**: `email`, `phone`, `full_name` stored in `revolut_merchant_customers`. Access to this table should be restricted to authorised analysts. Consider column-level security in PostgreSQL if required.
- **API key**: stored as environment variable only; never persisted to database or logged.
- **No secrets in logs**: API key must not appear in log output, HTTP request logs, or checkpoint state.

## 1.8 Non-functional requirements

| Requirement | Target |
|-------------|--------|
| Extract duration | Full initial load ≤ 60 min; incremental daily ≤ 10 min |
| Retry behaviour | Exponential backoff on HTTP 429 / 5xx (6 attempts, up to 60 s max delay) |
| Graceful degradation | If `REVOLUT_MERCHANT_API_KEY` is absent, log a warning and return empty `LoadResult`; do not fail the full extract run |
| Idempotency | Re-runs over same window produce stable row counts |
| Observability | Per-entity record counts logged at INFO; errors at ERROR with entity id |
| Test coverage | Unit tests for all mapper functions and checkpoint state utilities |

## 1.9 References

- [Revolut Merchant API](https://developer.revolut.com/docs/merchant/merchant-api)
- [Sprint-01 scope](../../sprint-01/01-scope-and-requirements.md) — Business API context
