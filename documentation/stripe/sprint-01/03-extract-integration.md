# 3. Extract pipeline integration (multi-entity Stripe)

This document connects the **Stripe BI** table design ([02-schema-design.md](02-schema-design.md)) to the current Keap extractor codebase.

## 3.1 Where Stripe runs relative to Keap

**Default behavior (recommended)**: The full **Stripe extract** should run as part of a **full extract**, **after** all Keap entity types in [`DataLoadManager.load_all_data`](../../src/scripts/load_data_manager.py) complete. Stripe does not participate in Keap foreign-key ordering (`custom_fields` → … → `subscriptions`), so appending it at the end avoids false dependencies.

**Optional**: A dedicated CLI flag or environment guard could skip Stripe for environments without keys; when the extract runs with keys configured, it should populate **all** configured Stripe `entity_type` targets for BI alongside Keap.

## 3.2 Orchestration: `run_stripe_extract` (facade)

[`EntityLoader`](../../src/scripts/loaders/base_loader.py) is constructed with [`KeapClient`](../../src/api/keap_client.py). Stripe HTTP calls do not belong inside `KeapClient`.

**Recommended approach**: Implement a single entry point—for example **`run_stripe_extract(db_session, checkpoint_manager, ...)`**—that **orders and invokes** one loader or private function per Stripe resource (or small groups), each using the official Stripe SDK or HTTPS. Invoke **`run_stripe_extract`** from `DataLoadManager.load_all_data` after the Keap `load_order` loop so one command still refreshes both worlds.

**Naming note**: Prefer one facade over **`run_stripe_charges_extract` only**; the facade may delegate to internal helpers such as `load_stripe_charges`, `load_stripe_products`, etc.

**Alternatives (documented for maintainers)**

- **Option A**: Multiple `Stripe*Loader` classes registered in [`LoaderFactory`](../../src/scripts/loaders/loader_factory.py), each constructed without `KeapClient` for API calls (factory signature may need adjustment).
- **Option B**: Refactor the loader hierarchy around a protocol or generic “API client” (larger change, better if many non-Keap sources appear).

## 3.3 Default load order (DAG)

Run steps in this order **after Keap** unless a resource is explicitly disabled. Earlier steps reduce orphan id references in later tables (all links remain nullable at the database level).

1. **Dimensions**: `stripe_products` → `stripe_prices`; `stripe_coupons` (order relative to prices is flexible; coupons early is fine).
2. **Optional**: `stripe_customers` if implemented ([02-schema-design.md §2.7](02-schema-design.md)).
3. **Subscriptions** → **invoices** → **payment_intents** → **charges**:
   - Load **`stripe_subscriptions`** before **`stripe_invoices`** when invoice rows reference `subscription_id`.
   - Load **`stripe_invoices`** before or in parallel with **`stripe_payment_intents`** depending on volume; ensure **charges** run after **payment intents** if you rely on fresh `latest_charge_id` on intents for debugging joins.
   - **`stripe_charges`** after or tightly with intents based on your reconciliation preference (charges are the primary payment fact).
4. **Refunds**: **`stripe_refunds`** — list Refunds API with `created` filters and/or refresh refunds for charges touched in a charge lookback window.
5. **Settlement**: **`stripe_balance_transactions`**; then optional **`stripe_payouts`** and **`stripe_transfers`** if those tables are enabled.

**Listing vs expanding**: Prefer **list + retrieve** per resource with explicit column mapping. Use **`expand`** only where necessary for performance or missing fields, and document expanded paths in the loader.

## 3.4 Pagination and checkpoints

### Stripe vs Keap

- Keap list endpoints use **numeric offsets**; [`ExtractionState.api_offset`](../../src/models/oauth_models.py) is an **integer** and [`CheckpointManager`](../../src/scripts/checkpoint_manager.py) persists it.
- Stripe list APIs use **cursor** pagination (`starting_after` the last object id), not a numeric page offset.

**Do not** store a Stripe cursor in `api_offset` without an explicit, documented encoding: it is misleading and fragile.

### Practical checkpoint strategies (every `entity_type`)

1. **Watermark on `created`**: Per entity type, use `last_loaded` or `last_successful_extraction` (and/or a dedicated watermark) to set **`created[gte]`** for incremental batches. Align with [01-scope-and-requirements.md](01-scope-and-requirements.md) hybrid policy for objects that mutate after creation.
2. **Cursor resume for long backfills**: If you need durable mid-backfill resume for **any** Stripe resource, add a **migration** extending `extraction_state`, for example:
   - `pagination_cursor TEXT` holding the last seen object id **per** `entity_type`, or
   - `checkpoint_json JSONB` for Stripe-specific fields (cursor, secondary watermarks, account id for Connect)

Until that exists, **interrupting a very large initial backfill** for a given entity may require restarting list iteration from the beginning (still safe with upsert, but costly).

### `entity_type` values

Use **one string per Stripe resource** so [`ExtractionState.entity_type`](../../src/models/oauth_models.py) stays unique alongside Keap entities. Recommended literals (adjust only if implementation standardizes different names):

| `entity_type` | Table / target |
|---------------|----------------|
| `stripe_products` | `stripe_products` |
| `stripe_prices` | `stripe_prices` |
| `stripe_coupons` | `stripe_coupons` |
| `stripe_customers` | `stripe_customers` (if implemented) |
| `stripe_subscriptions` | `stripe_subscriptions` |
| `stripe_invoices` | `stripe_invoices` |
| `stripe_payment_intents` | `stripe_payment_intents` |
| `stripe_charges` | `stripe_charges` |
| `stripe_refunds` | `stripe_refunds` |
| `stripe_balance_transactions` | `stripe_balance_transactions` |
| `stripe_payouts` | `stripe_payouts` (if implemented) |
| `stripe_transfers` | `stripe_transfers` (if implemented) |

## 3.5 CLI and `LoaderFactory`

[`src/__main__.py`](../../src/__main__.py) exposes `--entity-type` with `choices=LoaderFactory.get_supported_entity_types()`. For targeted reloads:

```bash
python -m src --entity-type stripe_charges
python -m src --entity-type stripe_invoices
```

Each supported `stripe_*` value should route to the corresponding loader or branch inside `run_stripe_extract`. If Stripe is **only** invoked from `load_all_data`, CLI support can be deferred per entity, but operators benefit from **`stripe_charges`** and **`stripe_balance_transactions`** first.

## 3.6 Dependencies

When implementing code (outside this documentation pass), add the official **`stripe`** Python package to [`requirements.txt`](../../requirements.txt) and pin a major version range appropriate for your Stripe API version.

## 3.7 Database migrations vs `create_all`

The app currently registers models in [`src/models/models.py`](../../src/models/models.py) and may create tables via [`init_db`](../../src/database/init_db.py). For production, prefer **Alembic migrations** for all `stripe_*` tables to match the pattern described in [Database design](../04-database-design.md), even if historical Keap tables were created differently.

## 3.8 References

- [`load_data_manager.py`](../../src/scripts/load_data_manager.py) — `load_order` and `load_all_data`
- [`checkpoint_manager.py`](../../src/scripts/checkpoint_manager.py) — checkpoint persistence
- [`oauth_models.py`](../../src/models/oauth_models.py) — `ExtractionState`
