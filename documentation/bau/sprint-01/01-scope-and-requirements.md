# 1. Scope and requirements (Keap REST v2 BI)

## 1.1 In scope

- **Inventory** all v2 **GET** (read) endpoints relevant to BI, and classify them against the existing **v1 extract** (see [keap-v2-get-endpoints-inventory.csv](keap-v2-get-endpoints-inventory.csv) and [README.md](README.md) Appendix A).
- **Design** PostgreSQL tables (or views) for v2-sourced data that are **not** adequately represented by the current v1 models, or that are **materially richer** in v2.
- **Integrate** extraction **after** the v1 `load_order` in [`DataLoadManager.load_all_data`](../../src/scripts/load_data_manager.py) using a dedicated facade (see [03-extract-integration.md](03-extract-integration.md)), analogous to Stripe’s `run_stripe_extract`.
- **Document** reporting joins between v2 tables and existing v1 facts/dimensions ([04-bi-reporting-and-joins.md](04-bi-reporting-and-joins.md)).

## 1.2 Out of scope (this sprint documentation)

- Replacing the entire v1 pipeline with v2 for entities already stable on v1, unless a follow-on explicitly defines **cutover** (grain, keys, and backfill).
- Write-heavy or operational v2 APIs (create/update/delete) except where needed for future webhook or correction flows.
- Full normalization of every nested v2 object: start with **star-schema friendly** flattening plus optional `raw_payload` JSONB where needed.

## 1.3 OAuth2 and scopes

- Reuse the existing token endpoint and refresh flow ([`OAuth2Client`](../../src/auth/oauth2_client.py), [`TokenManager`](../../src/auth/token_manager.py)).
- **Action:** In the Keap developer console, ensure the application’s scopes include **read** access for every v2 resource group you plan to call. The v2 docs ([Keap REST API v2](https://developer.infusionsoft.com/docs/restv2/)) list required scopes per area; missing scopes surface as **403** or empty results—log and surface clearly in the extract.

## 1.4 PII, sensitivity, and logging

- v2 exposes the same classes of data as v1 (contacts, emails, payment methods, files, etc.). Apply the same discipline as the rest of the project: **no** tokens or secrets in logs; minimize PII at INFO; treat `raw_payload` as restricted if stored.
- **Files** and **email** content endpoints may be large or binary; default extract should **metadata-only** unless product owners require full content in the warehouse.

## 1.5 Rate limits and quotas

- v2 responses are expected to carry the same family of **quota/throttle** headers already handled in [`KeapBaseClient._handle_response`](../../src/api/base_client.py). The v2 client layer should **reuse** that handling (see [05-api-client-and-pagination.md](05-api-client-and-pagination.md)).
- Plan **sequential** or **low-concurrency** v2 batches after v1 to avoid doubling burst traffic; tune backoff using existing patterns (`KeapRateLimitError`, etc.).

## 1.6 Incremental synchronization

- v2 list APIs use **cursor** pagination (`page_token`), not v1-style `offset` (see [05-api-client-and-pagination.md](05-api-client-and-pagination.md)).
- **Checkpoints** must store **opaque** `page_token` strings (and optional `filter`/`order_by` fingerprint) per `entity_type`. [`CheckpointManager`](../../src/scripts/checkpoint_manager.py) today persists `api_offset`; v2 may need an additional field or a JSON checkpoint blob—see [03-extract-integration.md](03-extract-integration.md).

## 1.7 Idempotency and upserts

- Primary keys for v2-sourced rows should follow **stable API identifiers** (numeric ids, string keys, or composite keys as documented per resource).
- Repeated runs must **upsert** so BI reflects current API truth.

## 1.8 Explicit exclusions (examples)

- **Locale reference** data (countries/provinces) unless reporting explicitly needs it in-database versus app-side lookup.
- **Settings** and **application configuration** snapshots unless ops/BI requires historical configuration auditing.
- **Report execution** APIs under `/rest/v2/reporting/reports` unless replacing an external reporting dependency—treat as optional.
