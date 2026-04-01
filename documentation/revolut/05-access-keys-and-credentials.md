# 5. Access keys and credentials (Revolut Business API)

This document explains how to **register the application**, **create signing keys**, obtain **access tokens**, and configure **this project** for a read-only extract. Exact menu labels in the Revolut Business UI may change; always cross-check [Revolut Developer documentation](https://developer.revolut.com/docs/business/business-api/).

## 5.1 Prerequisites

- A **Revolut Business** account with permission to **manage API access** (role varies by organization).
- Agreement to use **READ**-appropriate scopes only for BI extract (avoid **PAY** / **WRITE** unless required for a different use case).

## 5.2 Sandbox vs production

Revolut provides **sandbox** and **production** environments. Use **sandbox** for development and mapper validation; use **production** only on secured hosts with restricted secrets.

- Base URLs and OAuth/token endpoints differ by environment. **Copy hostnames from the official “Make your first API request” or Business API overview** at implementation time.
- Set a project-level flag (recommended environment variable below) so the same codebase targets the correct hosts.

## 5.3 Register the application and certificates

Revolut Business API authentication typically uses a **JWT client assertion** signed with a **private key** whose **public certificate** is registered on the application. Revolut documents **step 1 — add your certificate** in [Make your first API request](https://developer.revolut.com/docs/guides/manage-accounts/get-started/make-your-first-api-request); use that guide for the full first-request flow.

**High-level steps** (confirm against current guides):

1. In the **Revolut Business** web application, open **Developer** or **API** settings (wording may vary).
2. **Create** a new API application (or use an existing one dedicated to this extract).
3. Generate an **RSA key pair** and **public certificate** for signing (Revolut commonly documents **PS256** and certificate upload steps).
4. **Upload** the **public** certificate to Revolut; **retain** the **private** key **only** in a secret store or secure file path on the server—**never** commit it to git.

Official guides to follow:

- [Update application certificates](https://developer.revolut.com/docs/guides/build-banking-apps/manage-your-applications/update-certificates) (rotation)
- [Work with JSON Web Tokens](https://developer.revolut.com/docs/guides/build-banking-apps/tutorials/work-with-json-web-tokens)

## 5.3.1 Access token vs client assertion (what goes where)

Revolut uses two different string types; do not confuse them:

| Artifact | Role | Typical lifetime | In this project |
|----------|------|------------------|-----------------|
| **Access token** | Sent on every Business API call as `Authorization: Bearer <access_token>` | Short (often on the order of **~40 minutes** in production—confirm `expires_in` from the token response) | **`REVOLUT_ACCESS_TOKEN`** for a **manual / short-lived** setup only, **or** obtained automatically when using OAuth variables below |
| **Client assertion JWT** | Proves the client to the **token** endpoint; signed with your **private key** matching the uploaded certificate | Minutes | Built in code (`build_client_assertion_jwt`); not stored as a single long-lived string in `.env` |

**Verify connectivity** (replace the placeholder with a current access token; never commit real tokens):

```bash
curl https://b2b.revolut.com/api/1.0/accounts \
  -H "Authorization: Bearer <your_access_token>"
```

For **scheduled extracts**, prefer **`REVOLUT_REFRESH_TOKEN`** (plus client id, private key, `kid`) so the app exchanges the client assertion for a fresh **access token** before each run or when the cached token nears expiry. When an access token expires, obtain a new one using the **token** endpoint and the **client assertion JWT** (and refresh token or initial authorization code) per Revolut’s docs—not by reusing an expired access token.

## 5.4 JWT client assertion (conceptual)

The client assertion is a **short-lived JWT** signed with **PS256** using your **private key**. Claims commonly include (names and required values **must match current Revolut documentation**):

- **`iss`** — issuer (often your **client id**)
- **`sub`** — subject (often the same client id)
- **`aud`** — audience Revolut expects for the token endpoint
- **`iat`**, **`exp`** — issued-at and expiry (keep the window small; e.g. minutes)
- **`jti`** — unique jwt id per request (recommended)

The JWT header typically includes **`kid`** referencing the **uploaded certificate** key id Revolut assigns.

**Use the official JWT creation guide** for exact claim sets:

- [Create a JWT](https://developer.revolut.com/docs/guides/build-banking-apps/register-your-application-using-dcr/create-a-jwt)

## 5.5 Exchanging assertion for tokens

Post the client assertion (or follow the documented grant type) to the Revolut **token** endpoint. A successful response returns at least:

- **`access_token`** — send as `Authorization: Bearer <access_token>` on API calls
- **`refresh_token`** — store securely for renewing access without repeating user steps (if issued for your flow)
- **`expires_in`** — schedule refresh before expiry

Access tokens are **short-lived**; the extractor must **refresh** or re-exchange per run. **Do not** log token values.

## 5.6 Scopes for read-only extract

Request the **minimum** scopes required:

- **READ** for accounts and transactions listing and retrieval
- Avoid **READ_SENSITIVE_CARD_DATA** unless compliance approves storage and access of those fields
- Avoid **WRITE** and **PAY** for this BI pipeline

## 5.7 Environment variables (this project)

Align with [`.env.example`](../../.env.example) (copy to `.env`; never commit secrets).

| Variable | Purpose |
|----------|---------|
| `REVOLUT_ACCESS_TOKEN` | Optional. **Only** the current **access token** (`oa_prod_…` / sandbox equivalent). Use **without** `REVOLUT_REFRESH_TOKEN` and **without** `REVOLUT_AUTHORIZATION_CODE` for a static bearer. **Rotate manually** in `.env` when Revolut expires the token. If `REVOLUT_REFRESH_TOKEN` (or authorization code) is set, OAuth mode is used and this variable is ignored. |
| `REVOLUT_USE_SANDBOX` | `true` / `false` — selects sandbox vs production hosts |
| `REVOLUT_CLIENT_ID` | OAuth / API client id from Revolut |
| `REVOLUT_JWT_KID` | Key id Revolut assigns to the uploaded certificate (`kid` in the client assertion header) |
| `REVOLUT_ISSUER` | If distinct from client id for JWT `iss` (optional; omit if same) |
| `REVOLUT_JWT_AUDIENCE` | Override JWT `aud` if token exchange fails (default `https://revolut.com`) |
| `REVOLUT_PRIVATE_KEY_PATH` | Filesystem path to PEM private key (server only) |
| `REVOLUT_PRIVATE_KEY_PASSPHRASE` | If the key is encrypted (optional) |
| `REVOLUT_REFRESH_TOKEN` | Persisted refresh token (recommended for production; prefer secret manager on the VPS) |
| `REVOLUT_AUTHORIZATION_CODE` | One-shot alternative to refresh token for initial exchange |
| `REVOLUT_TRANSACTION_LOOKBACK_DAYS` | Bounded lookback for state drift (see [01-scope-and-requirements.md](01-scope-and-requirements.md)) |
| `REVOLUT_STORE_RAW_PAYLOAD` | `true` / `false` — store full JSON in DB (default `false` in high-sensitivity environments) |

If the token endpoint or JWT claims require additional ids (e.g. redirect URI for some flows), add variables **only** when Revolut’s current docs require them.

## 5.8 Secret handling and rotation

- Store **private keys** and **refresh tokens** in a **secret manager** or **restricted file permissions** on the VPS; not in chat, email, or tickets.
- **Rotate** certificates per Revolut’s process before expiry; keep **two keys** if Revolut supports overlap during rotation ([Update application certificates](https://developer.revolut.com/docs/guides/build-banking-apps/manage-your-applications/update-certificates)).
- Restrict **database** and **BI** access to columns that contain PII or full payloads.

## 5.9 Logging and debugging

- Log: request id, HTTP status, **Revolut error codes** if present, account id, page index.
- Never log: JWT assertions, `Authorization` headers, private keys, refresh tokens, full card numbers.

## 5.10 Verification checklist

- [ ] Sandbox **token** exchange succeeds
- [ ] **List accounts** returns expected wallets
- [ ] **List transactions** with small `from`/`to` window returns data
- [ ] Extract runs with **READ** scope only
- [ ] Private key **not** in repository; `.env` in `.gitignore`

## 5.11 References

- [Revolut Business API](https://developer.revolut.com/docs/business/business-api/)
- [Retrieve a list of transactions](https://developer.revolut.com/docs/business/get-transactions)
- [Make your first API request](https://developer.revolut.com/docs/guides/manage-accounts/get-started/make-your-first-api-request)
- [Work with JSON Web Tokens](https://developer.revolut.com/docs/guides/build-banking-apps/tutorials/work-with-json-web-tokens)
