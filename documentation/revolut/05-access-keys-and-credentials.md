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

Revolut Business API authentication typically uses a **JWT client assertion** signed with a **private key** whose **public certificate** is registered on the application.

**High-level steps** (confirm against current guides):

1. In the **Revolut Business** web application, open **Developer** or **API** settings (wording may vary).
2. **Create** a new API application (or use an existing one dedicated to this extract).
3. Generate an **RSA key pair** and **public certificate** for signing (Revolut commonly documents **PS256** and certificate upload steps).
4. **Upload** the **public** certificate to Revolut; **retain** the **private** key **only** in a secret store or secure file path on the server—**never** commit it to git.

Official guides to follow:

- [Make your first API request](https://developer.revolut.com/docs/guides/manage-accounts/get-started/make-your-first-api-request)
- [Update application certificates](https://developer.revolut.com/docs/guides/build-banking-apps/manage-your-applications/update-certificates) (rotation)
- [Work with JSON Web Tokens](https://developer.revolut.com/docs/guides/build-banking-apps/tutorials/work-with-json-web-tokens)

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

## 5.7 Environment variables (proposal for this project)

When implementation lands, align with [`.env.example`](../../.env.example) (copy to `.env`; never commit secrets). Proposed names:

| Variable | Purpose |
|----------|---------|
| `REVOLUT_USE_SANDBOX` | `true` / `false` — selects sandbox vs production hosts |
| `REVOLUT_CLIENT_ID` | OAuth / API client id from Revolut |
| `REVOLUT_ISSUER` | If distinct from client id for JWT `iss` (optional; omit if same) |
| `REVOLUT_PRIVATE_KEY_PATH` | Filesystem path to PEM private key (server only) |
| `REVOLUT_PRIVATE_KEY_PASSPHRASE` | If the key is encrypted (optional) |
| `REVOLUT_REFRESH_TOKEN` | Persisted refresh token if your flow stores it in env (prefer secret manager in production) |
| `REVOLUT_TRANSACTION_LOOKBACK_DAYS` | Bounded lookback for state drift (see [01-scope-and-requirements.md](01-scope-and-requirements.md)) |
| `REVOLUT_STORE_RAW_PAYLOAD` | `true` / `false` — store full JSON in DB (default `false` in high-sensitivity environments) |

If the token endpoint or JWT claims require additional ids (e.g. redirect URI for some flows), add variables **only** when the implementation confirms they are needed.

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
