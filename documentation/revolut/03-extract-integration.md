# 3. Extract pipeline integration (Revolut)

This document connects the **Revolut BI** table design ([02-schema-design.md](02-schema-design.md)) to the Keap extractor codebase patterns (see [Stripe integration](../stripe/03-extract-integration.md) for a concrete precedent).

## 3.1 Where Revolut runs relative to Keap and Stripe

**Default behavior (recommended)**: Run the **Revolut extract** as part of a **full extract**, **after** all Keap entity types in [`DataLoadManager.load_all_data`](../../src/scripts/load_data_manager.py) complete. Revolut does not participate in Keap foreign-key ordering.

**Ordering vs Stripe**: Revolut and Stripe are **independent**. Recommended order:

1. Keap `load_order` loop
2. **`run_stripe_extract`** (if `STRIPE_API_KEY` configured)
3. **`run_revolut_extract`** (if Revolut credentials configured)

Either gateway can be skipped when keys are absent. This keeps side-effect-free ordering and avoids implying cross-gateway dependencies.

## 3.2 Orchestration: `run_revolut_extract` (facade)

[`EntityLoader`](../../src/scripts/loaders/base_loader.py) is constructed with [`KeapClient`](../../src/api/keap_client.py). Revolut HTTP calls do **not** belong inside `KeapClient`.

**Recommended approach**: Implement **`run_revolut_extract(db_session, checkpoint_manager, update: bool = False)`** that:

1. Loads **settings from environment** (see [05-access-keys-and-credentials.md](05-access-keys-and-credentials.md)); if mandatory variables are missing, **log and return** without failure (same pattern as Stripe when `STRIPE_API_KEY` is unset).
2. Obtains or refreshes a **Bearer access token** using the JWT client assertion flow (implementation detail in application code).
3. Syncs **`revolut_accounts`** (list or retrieve accounts per current API).
4. For **each account** to include (or a configured allow-list), syncs **`revolut_transactions`** with date range + pagination + upsert.

Delegate to helpers such as `load_revolut_accounts` and `load_revolut_transactions` rather than one monolithic function.

**Alternatives (for maintainers)**

- **Option A**: Register `Revolut*Loader` types in [`LoaderFactory`](../../src/scripts/loaders/loader_factory.py) with a factory signature that does not require `KeapClient` for Revolut loaders.
- **Option B**: Shared “HTTP extract” protocol used by Stripe and Revolut (larger refactor).

## 3.3 Default load order (DAG)

1. **`revolut_accounts`** — refresh dimension so transaction rows resolve `account_id` labels and currencies in BI.
2. **`revolut_transactions`** — for each account, list transactions within the **from/to** window and paginate until complete.

If the API supports **retrieve single transaction** by id, use it **sparingly** for reconciliation or error recovery, not as the primary list path.

## 3.4 Pagination and checkpoints

### Revolut vs Keap

- Keap uses **numeric offsets** in [`ExtractionState.api_offset`](../../src/models/oauth_models.py).
- Revolut list APIs use **pagination** parameters documented for [Retrieve a list of transactions](https://developer.revolut.com/docs/business/get-transactions) (e.g. `count`, and a cursor or offset—**verify current docs**).

**Do not** store an opaque Revolut cursor in `api_offset` without a documented encoding.

### Practical checkpoint strategies

1. **Per-entity watermarks**: Use `extraction_state` rows with `entity_type` values such as `revolut_accounts` and `revolut_transactions` (or `revolut_transactions:{account_id}` if you need **per-account** watermarks—prefer a dedicated key scheme documented here).

2. **Transaction incremental window**: Store the last successfully processed **`from`** instant (or end of window) per account. Next run advances the window, **plus** applies [lookback](01-scope-and-requirements.md#16-incremental-synchronization) for upsert of state changes.

3. **Mid-backfill resume**: If a single account’s history exceeds one run budget, add **Stripe-style** extensions:
   - `pagination_cursor TEXT` or `checkpoint_json JSONB` on `extraction_state` (migration) holding the **next page token** or **last seen transaction id** as defined by the API.

### Recommended `entity_type` literals

| `entity_type` | Table / target |
|---------------|----------------|
| `revolut_accounts` | `revolut_accounts` |
| `revolut_transactions` | `revolut_transactions` (global watermark) **or** split per account with a suffix convention |

If using per-account suffixes, document the format (e.g. `revolut_transactions:uuid`) in runbooks so operators can query `extraction_state` predictably.

## 3.5 Token lifecycle

- Access tokens expire on a **short TTL** (Revolut documentation commonly cites on the order of **40 minutes**; confirm in current docs).
- The extract should **refresh** tokens using the issued **refresh_token** or repeat the **client assertion** exchange as required by the API, **without** logging secrets.
- Consider **in-memory** token cache for a single run; **persist** refresh tokens only via secure configuration or OS secret store—not in application logs.

## 3.6 CLI and `LoaderFactory`

[`src/__main__.py`](../../src/__main__.py) exposes `--entity-type` with `choices=LoaderFactory.get_supported_entity_types()`. When implementing:

- Add `revolut_accounts` and `revolut_transactions` (or a single `revolut_all` that runs the facade) to operator workflows.
- Operators benefit from **`revolut_transactions`** for targeted reloads after fixing mapper bugs.

## 3.7 Dependencies

When implementing code (outside this documentation pass), add an HTTP client library if not already present (e.g. `httpx` or `requests`) and a **JWT** library able to sign with **RS256** (per Revolut’s [Make your first API request](https://developer.revolut.com/docs/guides/manage-accounts/get-started/make-your-first-api-request)) and the private key format Revolut expects. Pin versions in [`requirements.txt`](../../requirements.txt).

## 3.8 Database migrations vs `create_all`

For production, prefer **Alembic migrations** for all `revolut_*` tables to match the pattern described in [Database design](../04-database-design.md).

## 3.9 References

- [`load_data_manager.py`](../../src/scripts/load_data_manager.py) — `load_all_data`
- [`checkpoint_manager.py`](../../src/scripts/checkpoint_manager.py) — checkpoint persistence
- [`oauth_models.py`](../../src/models/oauth_models.py) — `ExtractionState`
- [Stripe extract integration](../stripe/03-extract-integration.md) — parallel patterns
