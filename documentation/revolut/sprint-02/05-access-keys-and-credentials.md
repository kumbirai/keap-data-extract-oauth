# 5. Access keys and credentials (Revolut Merchant API)

## 5.1 Authentication model

The Revolut Merchant API uses a **static Bearer API key** — there is no OAuth2 flow, no JWT signing, and no refresh token management. This is simpler than the Sprint-01 Business API.

Every request requires two headers:

```
Authorization: Bearer <REVOLUT_MERCHANT_API_KEY>
Revolut-Api-Version: 2025-12-04
```

## 5.2 Obtaining the API key

1. Log in to the [Revolut Merchant Dashboard](https://merchant.revolut.com).
2. Navigate to **Settings → API**.
3. Generate a **Production API key** (or **Sandbox API key** for testing).
4. Copy the key immediately — it is shown only once.
5. Store it in your secrets manager or environment file (see §5.4).

The Sandbox environment (`https://sandbox-merchant.revolut.com`) uses a separate key issued from the sandbox dashboard.

## 5.3 Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REVOLUT_MERCHANT_API_KEY` | **Yes** | — | Bearer token for Merchant API |
| `REVOLUT_MERCHANT_USE_SANDBOX` | No | `false` | Set `true` to use sandbox base URL |
| `REVOLUT_MERCHANT_API_VERSION` | No | `2025-12-04` | API version header value |
| `REVOLUT_MERCHANT_LOOKBACK_DAYS` | No | `7` | Re-sync window for orders (days) |
| `REVOLUT_MERCHANT_DISPUTE_LOOKBACK_DAYS` | No | `30` | Re-sync window for disputes (days) |
| `REVOLUT_MERCHANT_INITIAL_HISTORY_DAYS` | No | `730` | Days of history on first run |
| `REVOLUT_MERCHANT_PAGE_SIZE` | No | `100` | Pagination page size |
| `REVOLUT_MERCHANT_STORE_RAW_PAYLOAD` | No | `false` | Persist full API JSON to `raw_payload` columns |

**All `REVOLUT_*` Business API variables from Sprint-01 remain unchanged.** The Merchant variables use the `REVOLUT_MERCHANT_` prefix to avoid conflicts.

## 5.4 Local development `.env` example

```dotenv
# Revolut Merchant API (Sprint-02)
REVOLUT_MERCHANT_API_KEY=sk_sandbox_AbCdEfGhIjKlMnOpQrStUvWx
REVOLUT_MERCHANT_USE_SANDBOX=true
# REVOLUT_MERCHANT_API_VERSION=2025-12-04
REVOLUT_MERCHANT_STORE_RAW_PAYLOAD=false
REVOLUT_MERCHANT_LOOKBACK_DAYS=7
REVOLUT_MERCHANT_INITIAL_HISTORY_DAYS=730
```

Never commit `.env` files containing real keys. The `.gitignore` should already exclude them.

## 5.5 Production secrets management

Recommended storage options (in order of preference):

1. **OS environment variables** injected by your process manager (systemd, Docker `--env-file`, Kubernetes Secrets).
2. **HashiCorp Vault** or **AWS Secrets Manager** with a startup script that exports to env.
3. **Encrypted `.env` file** with restricted filesystem permissions (`chmod 600`).

The API key is passed as a plain string in the `Authorization` header. Ensure:
- TLS is enforced for all API calls (HTTPS only — the client should raise on non-HTTPS).
- The key never appears in application logs, error messages, or checkpoint files.

## 5.6 Key rotation

To rotate the Merchant API key:

1. In the Revolut Merchant Dashboard, generate a **new API key**.
2. Update `REVOLUT_MERCHANT_API_KEY` in your secrets store.
3. Restart the extract process (or reload env).
4. Verify with a test run: `python -m src --entity-type revolut_merchant_locations`.
5. Revoke the old key in the dashboard once the new key is confirmed working.

No database state needs to be updated — unlike the Business API OAuth tokens, Merchant keys are stateless.

## 5.7 API versioning

The `Revolut-Api-Version` header pins the API contract. Current supported versions:

| Version | Status |
|---------|--------|
| `2025-12-04` | Current (recommended) |
| `2024-09-01` | Supported |
| `2024-05-01` | Supported |
| `2023-09-01` | Supported (older) |

When Revolut releases a new version, update `REVOLUT_MERCHANT_API_VERSION` after reviewing breaking changes in the [Revolut changelog](https://developer.revolut.com/docs/merchant/changelog).

## 5.8 Sandbox vs Production

| Parameter | Sandbox | Production |
|-----------|---------|-----------|
| Base URL | `https://sandbox-merchant.revolut.com` | `https://merchant.revolut.com` |
| API key prefix | `sk_sandbox_` (typically) | `sk_prod_` (typically) |
| Data | Test data only | Live merchant data |
| Set via | `REVOLUT_MERCHANT_USE_SANDBOX=true` | `REVOLUT_MERCHANT_USE_SANDBOX=false` (default) |

Always test against sandbox first when changing mapper logic or adding new entity types.

## 5.9 Security checklist

- [ ] `REVOLUT_MERCHANT_API_KEY` not in version control
- [ ] Key not logged at any log level
- [ ] HTTPS enforced in `merchant_client.py` (assert `api_base_url.startswith("https://")`)
- [ ] `raw_payload` disabled in production unless explicitly required and access-controlled
- [ ] `revolut_merchant_customers` table access restricted to authorised roles (PII: email, phone, name)
- [ ] Key rotation procedure documented in runbook

## 5.10 References

- [Revolut Merchant API Authentication](https://developer.revolut.com/docs/merchant/merchant-api#authentication)
- [Sprint-01 credentials](../sprint-01/05-access-keys-and-credentials.md) — Business API JWT/OAuth2 (separate from this)
