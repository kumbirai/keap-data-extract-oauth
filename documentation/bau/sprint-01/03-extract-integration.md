# 3. Extract pipeline integration (Keap REST v2)

This document connects the v2 **schema** ([02-schema-design.md](02-schema-design.md)) to the existing extractor layout (compare [Stripe integration](../stripe/sprint-01/03-extract-integration.md)).

## 3.1 Where v2 runs relative to v1 Keap

**Default behavior:** Run the **Keap v2 extract** as part of a **full extract**, **after** all v1 Keap entity types in [`DataLoadManager.load_all_data`](../../src/scripts/load_data_manager.py) complete (the `load_order` loop: `custom_fields` → … → `subscriptions`).

**Rationale:** v1 loaders assume [`KeapClient`](../../src/api/keap_client.py) and v1 pagination; v2 is a **separate adapter** with cursor pagination and different paths. Appending v2 after v1 avoids entangling [`LoaderFactory`](../../src/scripts/loaders/loader_factory.py) with a second client type until there is a clear need for v2-specific loaders.

**Ordering vs Stripe / Revolut:** Run **v2** after v1 Keap and **before** or **after** Stripe/Revolut depending on operational preference:

- **Before** Stripe/Revolut: keeps all Keap-shaped data together before third-party gateways.
- **After** Stripe/Revolut: minimizes change to current ordering; acceptable if v2 does not depend on gateway data.

Document the chosen order in the implementation PR; default recommendation is **after v1 Keap, before Stripe**.

## 3.2 Orchestration: `run_keap_v2_extract` (facade)

Introduce a single entry point, for example:

```python
def run_keap_v2_extract(
    session,
    checkpoint_manager,
    token_manager,
    update: bool = False,
) -> LoadResult:
    ...
```

**Responsibilities:**

1. If v2 extract is **disabled** (feature flag or env), log and return empty `LoadResult` (same pattern as optional Stripe when keys are missing).
2. Build **`KeapV2Client`** (or SDK-configured client) using the same `TokenManager` as v1.
3. For each configured v2 **sync spec** (entity_type, list function, mapper, model class), run **cursor-based** pagination until exhausted, upserting rows and updating checkpoints.

Delegate to helpers such as `sync_keap_v2_companies`, `sync_keap_v2_contact_links`, rather than one monolithic function.

## 3.3 Checkpoint and `CheckpointManager` alignment

[`CheckpointManager`](../../src/scripts/checkpoint_manager.py) syncs `api_offset` into [`ExtractionState`](../../src/models/oauth_models.py). v2 does **not** use offset pagination.

**Options (pick one in implementation):**

| Approach | Pros | Cons |
|----------|------|------|
| **A.** Extend `ExtractionState` (or checkpoint JSON) with `page_token` / `v2_cursor` string | Explicit, queryable | Schema migration |
| **B.** Store cursor inside existing JSON file checkpoint only | No DB migration | Harder to monitor in DB |
| **C.** Reuse `api_offset` field to store encoded cursor | No new column | Confusing semantics |

Recommendation: **A** — add nullable `api_page_token` (TEXT) or `checkpoint_extra` JSONB on `ExtractionState`, plus clear `entity_type` namespacing (`keap_v2_*`).

## 3.4 Incremental policy

- **Full crawl with upsert:** Simplest; repeat list from empty token periodically.
- **Cursor resume:** Persist last `next_page_token` per entity_type; on failure, resume from token.
- **Time-based filters:** If an endpoint supports `filter` on `update_time` or similar, combine with cursor for smaller windows (verify per resource in OpenAPI).

## 3.5 CLI and `LoaderFactory`

- Optional: register `keap_v2_*` pseudo entity types that dispatch to `run_keap_v2_extract` for a single resource, mirroring Stripe’s `--entity-type stripe_*` pattern.
- Avoid passing `KeapV2Client` into existing v1 loaders; keep v1 `KeapClient` unchanged.

## 3.6 Error handling

Reuse [`KeapBaseClient`](../../src/api/base_client.py) exception types (`KeapRateLimitError`, `KeapQuotaExhaustedError`, etc.) from the shared HTTP layer so decorators and logging stay consistent.

## 3.7 Default v2 load order (DAG sketch)

Order within `run_keap_v2_extract` should respect **reference data before facts** when foreign keys exist, for example:

1. `keap_v2_contact_link_types` (if loading links)
2. `keap_v2_companies`
3. `keap_v2_contact_links`
4. Other dimensions (automation categories, discount catalogs, …)
5. Heavier or dependent facts last

Adjust per actual API id requirements discovered during implementation.
