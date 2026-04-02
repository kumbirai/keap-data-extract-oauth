# 4. BI reporting and joins (Keap v2 ↔ v1)

## 4.1 Source-of-truth matrix

| Subject area | v1 extract today | v2 role | BI guidance |
|--------------|------------------|---------|-------------|
| Contacts core | Yes (`contacts`) | Overlapping `GET /rest/v2/contacts` | Stay on v1 for baseline contact grain unless migrating; use v2 for **additional** fields via join on `contact_id` or selective v2-only tables |
| Companies | Not in v1 load order | `GET /rest/v2/companies` | **v2 primary** for company dimension |
| Contact links | Not typical in v1 | `GET /rest/v2/contacts/{id}/links`, link types | **v2 primary**; join to v1 `contacts` on both endpoints |
| Orders / products | Yes | v2 `orders`, `products` | Prefer v1 for historical parity; v2 for **new** attributes or future cutover |
| Opportunities, notes, campaigns | Yes | v2 equivalents + campaign goals/sequences | v1 baseline; v2 for **goals/sequences** subdimensions |
| Automations | No | `GET /rest/v2/automations` | **v2 primary** for automation metadata reporting |
| Discounts | Partial / indirect | Multiple `/rest/v2/discounts/...` | **v2 primary** for promotion/discount dimensions |
| Affiliate extensions | Partial | Referrals, programs, payments in v2 | Extend affiliate reporting with v2 child facts |
| Files, emails | Limited | v2 list/get | Metadata-only unless approved |

Refine this table as each resource goes through implementation.

## 4.2 Join patterns

### Companies to contacts

The v1 [`contacts`](../../src/models/entity_models.py) table has `company_name` (and legacy `company` string fields), **not** a numeric `company_id`. Join to `keap_v2_companies` for reporting via **name matching** (exact or normalized), or add a future bridge column/migration if you need a stable company key from v2.

### Contact links (graph-style reporting)

- `keap_v2_contact_links` → v1 `contacts` on `contact_id` and `linked_contact_id`.
- `keap_v2_contact_links` → `keap_v2_contact_link_types` on `link_type_id`.

### Orders and discounts

- `orders` (v1) → discount dimension tables on ids returned on order line or order payloads **if** those ids exist in v1; otherwise load discount dimensions from v2 only and join on v2 order retrieve.

### Lead scores and lead sources (v2 tables)

- `keap_v2_contact_lead_scores.contact_id` → `contacts.id`.
- `keap_v2_lead_source_expenses` / `keap_v2_lead_source_recurring_expenses` / `keap_v2_lead_source_recurring_expense_incurred` → `keap_v2_lead_sources.id` on `lead_source_id` (text, from the v2 API).
- v1 `contacts.lead_source_id` is an integer; cast/compare carefully to `keap_v2_lead_sources.id` if your tenant aligns those identifiers.

## 4.3 Example SQL (illustrative)

**Companies with contact counts** (name-based join until a stable company key exists on v1 contacts):

```sql
SELECT c.id AS company_id,
       c.company_name,
       COUNT(ct.id) AS contact_count
FROM keap_v2_companies c
LEFT JOIN contacts ct ON LOWER(TRIM(ct.company_name)) = LOWER(TRIM(c.company_name))
GROUP BY c.id, c.company_name;
```

Prefer tightening this join (normalization rules, handling NULL names) for production dashboards.

**Duplicate prevention:** For entities present in both APIs, BI dashboards should pick **one** primary source per measure to avoid double counting; document the choice in this file.

## 4.4 Views for analysts

Recommend **reporting views** that hide v1/v2 split, for example `rpt_contact_with_company` combining v1 contact fields with `keap_v2_companies` names.

## 4.5 Refresh cadence

Align v2 incremental policy ([03-extract-integration.md](03-extract-integration.md)) with dashboard refresh: full upsert sweeps may be acceptable nightly; cursor-resume for large tables.
