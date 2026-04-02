# 2. Schema design (Keap REST v2 BI)

## 2.1 Design principles

- **Prefix:** Use `keap_v2_` for tables whose **primary** source is the v2 API, to avoid colliding with existing Keap v1 table names. Domain-prefixed names (`keap_v2_company`, `keap_v2_contact_link`) are acceptable when they improve clarity.
- **Do not duplicate v1 grains** unless the team agrees v2 is the new **source of truth** for that grain; otherwise v2 tables **supplement** v1 (see [04-bi-reporting-and-joins.md](04-bi-reporting-and-joins.md)).
- **Foreign keys to v1:** Prefer **logical** joins on stable ids (`contact_id`, `order_id`, `product_id`, etc.) already present in v1 tables. Use PostgreSQL FK constraints only where keys are guaranteed to exist and migrations enforce them.
- **Common optional columns** (pattern match to Stripe docs): `metadata` `JSONB`, `raw_payload` `JSONB`, `loaded_at`, `updated_at` `timestamptz`.
- **Tenant:** If multi-account or multi-app appears later, add `keap_tenant_id` or equivalent from response headers / config; for single-tenant extract, omit.

## 2.2 Example target tables (illustrative)

Concrete columns should be taken from the OpenAPI models in the [Keap v2 SDK](https://github.com/infusionsoft/keap-sdk/tree/main/sdks/v2/python). The following are **starting points** for vertical slices.

### `keap_v2_companies`

**Grain:** one row per company record from `GET /rest/v2/companies` and `GET /rest/v2/companies/{company_id}`.

| Column | Purpose |
|--------|---------|
| `id` | Company id from API (PK) |
| `company_name` | Display name |
| `create_time` / `update_time` | If exposed |
| `custom_fields` | `JSONB` if not exploded to side tables |
| `raw_payload` | Optional full object |
| `loaded_at` / `updated_at` | ETL housekeeping |

**Indexes:** `(update_time DESC)` if used for incremental strategy; `GIN (custom_fields)` if queried.

### `keap_v2_contact_links`

**Grain:** one row per linked relationship from `GET /rest/v2/contacts/{contact_id}/links`.

| Column | Purpose |
|--------|---------|
| Composite PK | e.g. `(contact_id, linked_contact_id, link_type_id)` per API uniqueness |
| `contact_id` | Anchor contact (FK logical to `contacts`) |
| `linked_contact_id` | Other contact |
| `link_type_id` | From link type catalog |
| `raw_payload` | Optional |
| `loaded_at` / `updated_at` | ETL housekeeping |

### `keap_v2_contact_link_types`

**Grain:** one row per type from `GET /rest/v2/contacts/links/types`.

| Column | Purpose |
|--------|---------|
| `id` | Type id (PK) |
| `name` / `description` | As returned |
| `loaded_at` / `updated_at` | ETL housekeeping |

### `keap_v2_automations` / `keap_v2_automation_categories`

**Grain:** automation metadata from `GET /rest/v2/automations` and categories from `GET /rest/v2/automationCategory`.

Use separate tables if the API returns stable ids suitable for dimensions; store nested structures in `JSONB` when not needed for relational joins.

### Discount and catalog-adjacent resources

Category discounts, product discounts, order-total discounts, and free-trial discounts (`/rest/v2/discounts/...`) can be **normalized dimensions** for revenue reporting. Start with one table per discount family if shapes differ; merge only if OpenAPI shows compatible models.

## 2.3 Checkpoints and extract state

- Prefer **`entity_type`** values namespaced for v2, e.g. `keap_v2_companies`, `keap_v2_contact_links`, to avoid clashing with v1 `entity_type` in [`ExtractionState`](../../src/models/oauth_models.py).
- Store **cursor state** in a way that survives restarts (see [03-extract-integration.md](03-extract-integration.md)).

## 2.4 Migrations

- Use Alembic revisions per table group or per vertical slice.
- Keep backward-compatible adds; avoid destructive drops without a runbook.

## 2.5 What not to model blindly

- **Model** endpoints (`.../model`, custom field definitions) are **configuration**, not transactional facts—load only if BI needs historical snapshots of definitions.
- **Binary file content**—prefer metadata rows unless required.
