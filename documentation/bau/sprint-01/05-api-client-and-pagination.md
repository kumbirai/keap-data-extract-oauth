# 5. API client, host verification, and pagination (Keap REST v2)

## 5.1 Host and token spike (completed procedure)

**Goal:** Confirm that the **same OAuth2 access token** obtained via [`OAuth2Client`](../../src/auth/oauth2_client.py) works against Keap’s v2 HTTP surface, and which **host** the tenant should use.

### Steps

1. Obtain a valid access token using the existing authorize flow (`python -m src.auth.authorize` or equivalent).
2. Issue a read-only request to the same path on both hosts, for example:
   - `GET https://api.keap.com/crm/rest/v2/contacts?page_size=1`
   - `GET https://api.infusionsoft.com/crm/rest/v2/contacts?page_size=1`
3. Header: `Authorization: Bearer <access_token>`, `Accept: application/json`.
4. Record:
   - HTTP status (expect **200** with a small payload when authorized).
   - Which host the organization standardizes on (update config accordingly).

### Unauthenticated baseline (CI / smoke)

Without a token, both hosts return **401** for the v2 contacts path, which confirms the route exists and is protected. Example (run locally):

```bash
curl -sS -o /dev/null -w "%{http_code}\n" \
  "https://api.keap.com/crm/rest/v2/contacts?page_size=1"
curl -sS -o /dev/null -w "%{http_code}\n" \
  "https://api.infusionsoft.com/crm/rest/v2/contacts?page_size=1"
```

Both returned `401` in the environment used to author this sprint doc—**not** a substitute for an authenticated spike; repeat with a real token before locking configuration.

### Configuration recommendation

- Add something like `KEAP_REST_API_HOST=https://api.keap.com/crm` (or the Infusionsoft host if that is what works for the token) rather than hardcoding inside code paths.
- v1 can remain `https://api.infusionsoft.com/crm/rest/v1` until the team chooses to consolidate hosts; v2 base path remains `/rest/v2/...` under the configured CRM host.

## 5.2 Pagination contract (v2)

v2 list methods use **cursor** parameters, not v1 `limit`/`offset` + `next` URL parsing.

From the OpenAPI-generated model [ListContactsResponse](https://raw.githubusercontent.com/infusionsoft/keap-sdk/main/sdks/v2/python/docs/ListContactsResponse.md):

| Field | Role |
|-------|------|
| `contacts` | Array of results |
| `next_page_token` | Opaque cursor for the next page; absent or empty when done |

Typical request query parameters (see `ContactApi.list_contacts` in the SDK):

| Parameter | Role |
|-----------|------|
| `page_size` | Page size |
| `page_token` | Cursor from previous response |
| `filter` | API-specific filter string |
| `order_by` | Sort |

**Extract loop:**

1. Call list with `page_size` only.
2. If `next_page_token` present, repeat with `page_token=next_page_token`.
3. Stop when `next_page_token` is missing or empty.

Other resources follow the same pattern in the SDK; confirm per operation because some responses may use different property names for the list array.

## 5.3 Reusing v1 infrastructure vs separate client

### Shared layer (recommended)

Extract from [`KeapBaseClient`](../../src/api/base_client.py):

- `TokenManager` integration and `_update_headers`
- `requests.Session` lifecycle
- `_handle_response` (quota/throttle headers, 401 refresh attempt, 429 mapping)

into a small internal module, e.g. `KeapAuthenticatedHttp`, parameterized by **base URL** (v1 vs v2 root).

### Two API surfaces

| Class | Base URL (example) | Endpoints | Pagination |
|-------|-------------------|-----------|------------|
| `KeapClient` (existing) | `.../crm/rest/v1` | Current v1 strings | offset / `next` URL |
| `KeapV2Client` (new) | `.../crm` | Paths starting `rest/v2/...` | `page_token` loop |

**Do not** point the existing `KeapBaseClient.base_url` at v2 and reuse v1 endpoint strings; path and pagination semantics differ.

## 5.4 `KeapV2Client` vs official `keap_core_v2_client`

| Criterion | Raw `requests` + `KeapV2Client` | Official [keap-core-v2-sdk](https://github.com/infusionsoft/keap-sdk/tree/main/sdks/v2/python) |
|-----------|-----------------------------------|--------------------------------------------------------------------------------------------------|
| **Drift** | Manual path/query maintenance | Generated from OpenAPI; paths stay aligned |
| **Pagination** | Implement once per wrapper | SDK methods already expose `page_token` / `page_size` |
| **Typing** | Dicts or hand-written dataclasses | Typed models (`ListContactsResponse`, etc.) |
| **Dependencies** | None extra | New package + generator version bumps |
| **Token injection** | Trivial: set `Authorization` on session | `Configuration(access_token=..., host=...)` with shared token from `TokenManager` |
| **Error handling** | Reuse shared `_handle_response` by running requests through session | Map `ApiException` to existing Keap exceptions or wrap SDK calls in an adapter |

**Recommendation:**

- For **fast vertical slices**, a thin `KeapV2Client` using **shared auth + response handling** and **manual** first endpoints is acceptable.
- For **broad v2 coverage**, adopt the **official SDK** as an **adapter** inside the hex boundary: the application depends on a port interface; the SDK sits in the infrastructure adapter, converting SDK models to domain dicts or ORM inputs.

Either way, **one** OAuth token stack; **two** logical clients (v1 vs v2).

## 5.5 Testing strategy

- **Unit:** Pagination loop with mocked responses (varying `next_page_token`).
- **Integration:** One sandbox Keap app, read-only scopes, single entity list.
- **Contract:** When upgrading the SDK or changing host config, re-run the authenticated spike and a golden test entity.

## 5.6 Response shape note

[`KeapBaseClient._handle_response`](../../src/api/base_client.py) logs v1-centric keys (`contacts`, `tags`, …). When sharing this code with v2, generalize debug logging or gate it by API version to avoid misleading diagnostics.
