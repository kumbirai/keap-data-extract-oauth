# Connect pgAdmin on Windows to the VPS PostgreSQL database

This guide assumes PostgreSQL on the VPS is set up as in [README.md](README.md) (typically **`keap_db`** / **`keap_user`**, Postgres listening on **`127.0.0.1:5432`** on the server).

Two ways to connect from Windows:

1. **SSH tunnel (recommended)** — no public database port; same idea as [Connect Power BI to PostgreSQL](README.md#connect-power-bi-to-postgresql) in the main README.
2. **Direct TCP** — only if you intentionally exposed port **5432** to your IP per [§2.1 Optional: expose PostgreSQL TCP 5432](README.md#21-optional-expose-postgresql-tcp-5432-restricted).

---

## Prerequisites

- [pgAdmin 4](https://www.pgadmin.org/download/pgadmin-4-windows/) installed on Windows.
- SSH access to the VPS (OpenSSH client is built into Windows 10/11: `ssh` in PowerShell or Command Prompt).
- Database name, user, and password from your VPS setup (often `keap_db`, `keap_user`, and the password you set in `CREATE USER`).

---

## Option A: SSH tunnel (recommended)

### 1. Start the tunnel

Open **PowerShell** or **Command Prompt** and run (adjust user and host):

```text
ssh -N -L 15432:127.0.0.1:5432 YOUR_LINUX_USER@YOUR_VPS_HOST
```

Examples for `YOUR_VPS_HOST`: the VPS public IP, or a hostname such as `srv1498298.hstgr.cloud`.

- Leave this window **open** while you use pgAdmin.
- **Local port `15432`** forwards to **Postgres on the VPS** at `127.0.0.1:5432`.

If you prefer a different local port, change the first number (e.g. `-L 5432:127.0.0.1:5432` and use port **5432** in pgAdmin—but **15432** avoids clashing with a local PostgreSQL install on your PC).

**Key-based login:** See [SSH keys and ssh-agent (Windows, fewer prompts)](README.md#ssh-keys-and-ssh-agent-windows-fewer-prompts) in the main README.

### 2. Register the server in pgAdmin

1. Open **pgAdmin 4**.
2. Right-click **Servers** → **Register** → **Server…**
3. **General** tab: **Name** — any label (e.g. `Keap VPS (tunnel)`).
4. **Connection** tab:
   - **Host name/address:** `127.0.0.1`
   - **Port:** `15432` (must match the **first** number in `-L 15432:...`)
   - **Maintenance database:** `keap_db` (or your `DB_NAME`)
   - **Username:** `keap_user` (or your `DB_USER`)
   - **Password:** your database password (check **Save password** only if acceptable on that machine)

5. **SSL** tab (important when using a tunnel):
   - Set **SSL mode** to **Disable**.

   The tunnel already encrypts traffic. If you leave SSL **Prefer** or **Require**, the client may try TLS to `127.0.0.1` and fail with certificate or hostname errors (same class of issue as [Troubleshooting: Windows certificate error](README.md#troubleshooting-windows-certificate-error-when-connecting-power-bi) for Power BI).

6. Click **Save**.

### 3. Verify

Expand **Servers** → your server → **Databases** → **keap_db**. You should see schemas and objects. If the connection fails, confirm the SSH window is still connected and that on the VPS Postgres is running (`sudo systemctl status postgresql`).

---

## Option B: Direct connection (restricted public 5432)

Use this only if you completed **listen_addresses**, **`pg_hba.conf`**, **UFW**, and provider firewall for **your** IP as in [§2.1](README.md#21-optional-expose-postgresql-tcp-5432-restricted).

In **Register → Server → Connection**:

- **Host name/address:** VPS **public hostname or IP** (not `127.0.0.1`).
- **Port:** `5432`
- **Maintenance database**, **Username**, **Password:** same as on the server.

**SSL** tab:

- Prefer **`hostssl`** on the server and a proper certificate, then use **SSL mode** **Require** (or **Verify-Full** if you install the CA in Windows) — see [PostgreSQL SSL](https://www.postgresql.org/docs/current/ssl-tcp.html) and the security notes in the main README.
- If the server is not configured for TLS yet, you may need **Prefer** or **Disable** temporarily; **cleartext over the public internet is risky** — treat that as a short-term diagnostic only.

---

## Troubleshooting

| Symptom | What to check |
|--------|----------------|
| **Unable to connect** / timeout | SSH tunnel window closed or wrong local port; or firewall blocking SSH (22) from your network. |
| **Connection refused** on `127.0.0.1:15432` | Tunnel not running, or local port mismatch (pgAdmin must use the **-L** local port). |
| **Connection refused** after tunnel is up | On the VPS, Postgres not listening on `127.0.0.1:5432` (service down, or DB only inside Docker without host publish). See [Troubleshooting: “Connection to 127.0.0.1:5432 refused”](README.md#troubleshooting-connection-to-1270015432-refused) in the README. |
| **Certificate** / **SSL** errors | On the tunnel path, set pgAdmin **SSL mode** to **Disable**. |

---

## Related

- [README.md](README.md) — full VPS deployment, PostgreSQL hardening, and Power BI tunnel notes.
