# VPS deployment (KVM 2): Ubuntu, PostgreSQL, Keap extract

This guide targets a **Hostinger-style KVM VPS** used **only** for:

- **Ubuntu** (24.04 LTS recommended)
- **PostgreSQL** (data store for Keap extract + OAuth tokens)
- **Keap data extractor** (scheduled CLI runs)

**Power BI Desktop** runs on a **Windows PC**. The usual way to reach PostgreSQL from that PC is an **SSH tunnel** (see [Connect Power BI to PostgreSQL](#connect-power-bi-to-postgresql)).

**Power BI Service** (scheduled refresh, sharing in the cloud) **cannot** use your PC’s SSH tunnel—refresh runs in **Microsoft’s cloud**. Use either a **direct cloud connection** to a reachable PostgreSQL endpoint (see [Power BI Service (cloud refresh)](#power-bi-service-cloud-refresh)) or an **[on-premises data gateway](https://learn.microsoft.com/en-us/data-integration/gateway/service-gateway-onprem)** on a machine that can reach the database.

| Typical KVM 2 profile | Role in this guide |
|----------------------|-------------------|
| 2 vCPU, 8 GB RAM, 100 GB NVMe | Comfortable for Ubuntu + Postgres + extractor |

Do **not** run a Windows VM for Power BI on this same 8 GB node; use a separate Windows machine for reporting.

For generic install and commands, see [08-deployment-guide.md](../08-deployment-guide.md).

---

## Architecture

```text
┌─────────────────────────────────────────┐
│ VPS (Ubuntu + PostgreSQL + Keap extract) │
│  • Postgres: localhost (Desktop tunnel)   │
│    or TCP 5432 restricted (Service/gw)   │
│  • Extract: cron/systemd → python -m src │
└─────────────────┬───────────────────────┘
                  │ SSH :22 + optional -L (Desktop)
                  │   OR :5432 from Microsoft / gateway
┌─────────────────▼───────────────────────┐
│ Clients                                    │
│  • Power BI Desktop → 127.0.0.1:<port>    │
│  • Power BI Service → cloud or gateway    │
└──────────────────────────────────────────┘
```

---

## 1. Server baseline

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git ufw
sudo ufw allow OpenSSH
sudo ufw enable
```

Use SSH keys; disable password login when ready (`PasswordAuthentication no` in `sshd_config`).

---

## 2. PostgreSQL

```bash
sudo apt install -y postgresql postgresql-contrib
```

Create role and database. Use a **quoted heredoc** so passwords with `!`, `$`, or `"` are safe (double-quoted `-c "..."` breaks on `!` because bash enables **history expansion**).

```bash
sudo -u postgres psql <<'EOSQL'
CREATE USER keap_user WITH PASSWORD 'your_database_password_here';
CREATE DATABASE keap_db OWNER keap_user;
GRANT ALL PRIVILEGES ON DATABASE keap_db TO keap_user;
EOSQL
```

Edit only the string inside `PASSWORD '...'`. The `<<'EOSQL'` form passes the block to `psql` literally—no shell interpretation of `!` or `$`.

**`.env` and passwords with `@`:** Use the raw password in `DB_PASSWORD` (e.g. `$3cur3-P@ssw0rd`). The app URL-encodes credentials when building the PostgreSQL URL so `@` does not break Alembic or the app (unencoded `@` was previously parsed as part of the hostname).

**Default:** keep PostgreSQL on **localhost** only (`listen_addresses = 'localhost'` in `postgresql.conf`). Access from Windows is usually via **SSH tunnel** ([Connect Power BI to PostgreSQL](#connect-power-bi-to-postgresql)). If you need a **direct** TCP connection (e.g. unattended refresh from a **fixed** public IP), use [§2.1](#21-optional-expose-postgresql-tcp-5432-restricted)—never open `5432` to the entire internet without a compensating control (VPN, strict firewall, or PostgreSQL SSL).

### 2.1 Optional: expose PostgreSQL TCP 5432 (restricted)

**Risk:** A reachable `5432` is a high-value target. **Do not** `ufw allow 5432/tcp` with no source filter (that exposes the port globally). Without PostgreSQL TLS (`hostssl` + certificates), passwords and data can traverse the network in **cleartext**; an **SSH tunnel** or **VPN** is usually safer than a raw `host` rule.

Use a **single client IPv4** (or your office static range) everywhere below. Replace `203.0.113.50` with that address.

1. **Listen on all interfaces** (firewall still limits who can connect). Ubuntu keeps config under `/etc/postgresql/<version>/main/`:

   ```bash
   PGMAIN=$(ls -d /etc/postgresql/*/main 2>/dev/null | head -1)
   test -n "$PGMAIN" || { echo "PostgreSQL config dir not found"; exit 1; }
   sudo sed -i "s/^#*listen_addresses.*/listen_addresses = '*'/" "$PGMAIN/postgresql.conf"
   ```

   Or edit `$PGMAIN/postgresql.conf` manually: set `listen_addresses = '*'`.

2. **Allow only that client in `pg_hba.conf`** (append near the bottom, before any overly broad `host ... all ... 0.0.0.0/0` line if present). Reuse `PGMAIN` from step 1, or set it again: `PGMAIN=$(ls -d /etc/postgresql/*/main 2>/dev/null | head -1)`.

   ```bash
   echo "host    keap_db    keap_user    203.0.113.50/32    scram-sha-256" | sudo tee -a "$PGMAIN/pg_hba.conf"
   ```

   Use your real `DB_NAME` / `DB_USER` if they differ. **`listen_addresses` requires a full restart** (a reload is not enough for that setting):

   ```bash
   sudo systemctl restart postgresql
   ```

3. **UFW on the VPS:** allow **only** the client IP to reach `5432`:

   ```bash
   sudo ufw allow from 203.0.113.50 to any port 5432 proto tcp
   sudo ufw status verbose
   ```

4. **Hostinger (or other) cloud firewall:** add an inbound rule for **TCP 5432** **from** that same IP (or range). If this layer is missing, the port may still be unreachable or accidentally wide open depending on the provider defaults.

5. **Clients (e.g. Power BI Desktop over the public internet):** use the VPS **public hostname or IP**, **port `5432`**, database `keap_db`, and your DB user/password. Expect TLS/certificate prompts unless you disable DB encryption or trust the server cert (see [Troubleshooting](#troubleshooting-windows-certificate-error-when-connecting-power-bi)). For **TLS to Postgres**, configure server SSL and switch the `pg_hba` line to `hostssl` per [PostgreSQL SSL](https://www.postgresql.org/docs/current/ssl-tcp.html).

**Power BI Service** needs a path that does not rely on your PC; see [Power BI Service (cloud refresh)](#power-bi-service-cloud-refresh). If you use a **cloud connection** with a public hostname, treat **TLS + `hostssl`** as mandatory (not optional hardening).

The extractor on the VPS keeps **`DB_HOST=localhost`** in `.env`; it does not need to use the public interface.

---

## 3. Application

```bash
sudo mkdir -p /opt/keap-extract
sudo chown "$USER:$USER" /opt/keap-extract
cd /opt/keap-extract
git clone https://github.com/kumbirai/keap-data-extract-oauth.git app
cd app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

- `DB_HOST=localhost`, `DB_PORT=5432`, `DB_NAME=keap_db`, `DB_USER=keap_user`, `DB_PASSWORD=...`
- Keap OAuth fields and `TOKEN_ENCRYPTION_KEY` (see [.env.example](../../.env.example))

**Revolut (optional BI extract):** Register your **certificate** with Revolut per [Make your first API request — add your certificate](https://developer.revolut.com/docs/guides/manage-accounts/get-started/make-your-first-api-request). Full detail: [05-access-keys-and-credentials.md](../revolut/05-access-keys-and-credentials.md).

- **Recommended on a server:** `REVOLUT_CLIENT_ID`, `REVOLUT_PRIVATE_KEY_PATH`, `REVOLUT_JWT_KID`, and `REVOLUT_REFRESH_TOKEN` so the app mints a **client assertion JWT**, exchanges it for an **access token**, and refreshes automatically.
- **Short-lived bearer only:** set `REVOLUT_ACCESS_TOKEN` to the current access token (the value Revolut returns for API calls, e.g. `oa_prod_…`). Omit refresh token and authorization code. **Update `.env` when the token expires** (often on the order of ~40 minutes in production), or switch to the refresh-token flow above.

Example check against the live API (use a real token from your vault, not in shell history if possible):

```bash
curl https://b2b.revolut.com/api/1.0/accounts \
  -H "Authorization: Bearer <your_access_token>"
```

```bash
alembic upgrade head
```

### 3.1 Update the app later (`git pull`)

From the server, in the same directory you cloned into:

```bash
cd /opt/keap-extract/app
git pull origin main
```

Use `main` or whatever your default branch is (`git branch -r` to see).

Then refresh dependencies and migrations if the repo changed them:

```bash
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

- **`.env`** is local-only (not in git); `git pull` does not replace it.
- If you have local changes, `git pull` may fail; either **stash** (`git stash`, pull, `git stash pop`) or commit on a branch—avoid editing tracked files on the VPS long-term.

---

## 4. OAuth (Keap) on the VPS

Keap requires an **HTTPS** redirect URI. The authorize script starts a **small HTTP server** on the VPS; **nginx** serves HTTPS and **reverse-proxies** `/oauth/callback` to that server (default **port 8000**). Your browser must be able to open the HTTPS URL (same host as SSH or your PC’s browser is fine).

### 4.1 DNS and hostname

- **Custom domain:** Create an **A record** pointing to the VPS IP (e.g. `keap-oauth.example.com`).
- **Hostinger hostname:** Many plans provide a hostname such as `srv1498298.hstgr.cloud` that already resolves to the server—use that if you do not have a separate domain.

Pick **one** canonical URL, e.g. `https://srv1498298.hstgr.cloud/oauth/callback`.

### 4.2 Keap Developer Portal

1. Open your app at [Keap Developer Portal](https://developer.keap.com/).
2. Set the redirect / callback URL to the **exact** HTTPS URL (trailing path **`/oauth/callback`**, no typo).
3. Copy **Client ID** and **Client Secret** into `.env`.

### 4.3 nginx and Let’s Encrypt

**Before Certbot:** Let’s Encrypt must reach your VPS on **port 80** (HTTP-01 challenge). A **timeout** almost always means the Internet cannot open TCP 80 to this machine.

1. **UFW on the VPS** (if enabled):

   ```bash
   sudo ufw allow OpenSSH
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw status verbose
   ```

   If `80/tcp` is missing, add it and run `sudo ufw reload` if needed.

2. **Hostinger firewall (hPanel):** In **VPS → Firewall** (or **Security**), allow **inbound TCP 80** and **TCP 443** to this server. Hostinger often ships with a cloud firewall that blocks 80/443 even when UFW is open—both must allow traffic.

3. **Quick checks on the VPS:**

   ```bash
   sudo systemctl enable --now nginx
   curl -sI http://127.0.0.1/ | head -3
   ```

4. **From outside the VPS:** e.g. your PC’s browser opening `http://YOUR_VPS_IP/` or an online port checker on **TCP 80** for that IP. If it **times out**, Certbot will fail until inbound **80** (and later **443**) is allowed end-to-end.

Then:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo certbot --nginx -d srv1498298.hstgr.cloud
```

Replace `srv1498298.hstgr.cloud` with your **A record** or Hostinger hostname. Follow the prompts (email, agree to terms). Certbot will configure nginx for HTTPS.

#### Certbot still fails after opening 80/443

- Confirm DNS: `dig +short srv1498298.hstgr.cloud` should return your VPS IPv4.
- Read logs: `sudo tail -50 /var/log/letsencrypt/letsencrypt.log`
- **DNS challenge** (no port 80 needed): use a domain you control with a DNS API, or Hostinger DNS + `certbot certonly --manual --preferred-challenges dns -d your.domain` (add TXT record when prompted), then configure nginx to use the issued cert paths under `/etc/letsencrypt/live/`.

Add a **proxy** for the OAuth callback. Edit the server block Certbot created (often under `/etc/nginx/sites-available/`, e.g. your hostname’s config):

```nginx
location /oauth/callback {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Then:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

#### 404 on `https://your-host/oauth/callback` (nginx)

If the browser shows **404 Not Found** from nginx after Keap redirects (URL contains `?code=...`), the **`location /oauth/callback` block is missing**, is in the **wrong** `server` block, or nginx was not reloaded.

1. Put the block inside the **`server { ... }` that has `listen 443 ssl`** and `server_name srv1498298.hstgr.cloud` (your hostname). Certbot often creates a separate file, e.g.:

   ```bash
   ls /etc/nginx/sites-enabled/
   sudo grep -r "listen 443" /etc/nginx/sites-enabled/
   ```

   Edit **that** file—not only the port-80 block.

2. Example placement (inside the TLS server):

   ```nginx
   server {
       listen 443 ssl;
       server_name srv1498298.hstgr.cloud;
       # ... ssl_certificate lines from certbot ...

       location /oauth/callback {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       # other locations...
   }
   ```

3. `sudo nginx -t && sudo systemctl reload nginx`

4. **Run authorization again** from the app directory **while the callback server is listening**:

   ```bash
   cd /opt/keap-extract/app && source venv/bin/activate
   python -m src.auth.authorize
   ```

   Then complete the flow in the browser. The previous `code=` in the URL is **single-use**; after a 404 you must start a **new** authorize run.

5. **Order:** start `python -m src.auth.authorize` first (log shows *Starting callback server on port 8000*), **then** open the Keap URL. If nothing listens on `8000` when nginx proxies, you get **502 Bad Gateway** instead of 404.

### 4.4 `.env` on the VPS

```env
KEAP_REDIRECT_URI=https://srv1498298.hstgr.cloud/oauth/callback
OAUTH_CALLBACK_LISTEN_PORT=8000
```

Must match the Keap portal **character for character** (scheme, host, path). Change the hostname to yours. Port `8000` is where the Python callback server listens; nginx terminates TLS on **443** and forwards to `8000`.

### 4.5 Run authorization (one time)

```bash
cd /opt/keap-extract/app && source venv/bin/activate
python -m src.auth.authorize
```

On a headless server the browser may not open. Copy the **authorization URL** from the log, open it on **your PC** (or any machine), sign in to Keap, and approve. Keap will redirect your browser to `https://your-host/oauth/callback?code=...` → nginx → Python on port 8000 → tokens saved in PostgreSQL.

If the callback never completes, check nginx error log (`/var/log/nginx/error.log`) and that nothing else is using port **8000** during authorize.

---

## 5. Run extraction

```bash
source venv/bin/activate
python -m src              # full load
python -m src --update     # incremental
```

Logs: `logs/` under the app directory (see project README).

---

## 6. Schedule extraction (systemd)

Run as a dedicated user (example `keapextract`). Create a service that runs `--update` on a timer.

**`/etc/systemd/system/keap-extract.service`** (example):

```ini
[Unit]
Description=Keap data extract (incremental)
After=network.target postgresql.service

[Service]
Type=oneshot
User=keapextract
Group=keapextract
WorkingDirectory=/opt/keap-extract/app
EnvironmentFile=/opt/keap-extract/app/.env
ExecStart=/opt/keap-extract/app/venv/bin/python -m src --update
```

**`/etc/systemd/system/keap-extract.timer`** (example: daily 02:30 UTC):

```ini
[Unit]
Description=Daily Keap incremental extract

[Timer]
OnCalendar=*-*-* 00:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now keap-extract.timer
```

Adjust paths, user, and calendar to your policy.

---

## Connect Power BI to PostgreSQL

**Power BI Desktop** can use the **SSH tunnel** below. **Power BI Service** needs one of the options in [Power BI Service (cloud refresh)](#power-bi-service-cloud-refresh)—the service cannot see `127.0.0.1` on your laptop.

### Power BI Service (cloud refresh)

Scheduled refresh and shared datasets run in **Microsoft’s cloud**. The PostgreSQL connector supports **[cloud connections](https://learn.microsoft.com/en-us/power-bi/connect-data/service-connect-cloud-data-sources)** and connections through **[on-premises](https://learn.microsoft.com/en-us/data-integration/gateway/service-gateway-onprem)** or **[virtual network](https://learn.microsoft.com/en-us/data-integration/vnet/overview)** data gateways (see [Power Query PostgreSQL connector](https://learn.microsoft.com/en-us/power-query/connectors/postgresql)).

| Approach | When to use | Database exposure |
|----------|-------------|-------------------|
| **On-premises data gateway** | Default recommendation for a VPS database you do **not** want on the open internet | Install the gateway on **Windows** (always-on PC or small VM). Allow **TCP 5432** only from that machine’s public IP (same pattern as [§2.1](#21-optional-expose-postgresql-tcp-5432-restricted), using the gateway’s IP instead of an analyst PC), or use a **VPN** from the gateway host to the VPS. Postgres stays off `0.0.0.0/0`. |
| **Direct cloud connection** | You accept exposing PostgreSQL to Microsoft’s refresh infrastructure (and you can maintain firewall rules) | Postgres listens on a **public** hostname/IP with **`hostssl`** + `scram-sha-256`, strong password, and **least-privilege** role. Firewall allows **inbound 5432** from [Azure service tags / IP ranges](https://learn.microsoft.com/en-us/azure/virtual-network/service-tags-overview) relevant to **Power BI / Power Platform** (download the [weekly JSON](https://www.microsoft.com/en-us/download/details.aspx?id=56519); filter for tags such as **PowerBI**—verify current tag names for your cloud). This is **operationally heavier** than a gateway because ranges change. |

**Gateway workflow (summary):**

1. On the Windows host that can reach Postgres, install the [standard mode on-premises data gateway](https://learn.microsoft.com/en-us/data-integration/gateway/service-gateway-install).
2. In **Power BI service** → **Settings** → **Manage connections and gateways**, confirm the gateway is online.
3. Publish a report/dataset from Desktop that uses PostgreSQL, or configure the semantic model’s **Gateway and cloud connections** so the PostgreSQL source maps to **this gateway** (not “cloud” only). Enter server (VPS hostname or internal IP if VPN), port `5432`, database, and credentials. Gateway June 2025+ bundles **Npgsql**; older gateway builds may need the [Npgsql MSI](https://github.com/npgsql/npgsql/releases/tag/v4.0.17) per Microsoft’s connector prerequisites.

**Direct cloud workflow (summary):**

1. Complete [§2.1](#21-optional-expose-postgresql-tcp-5432-restricted) but replace the single static client IP with **allowlisted Microsoft / Azure ranges** (or your provider’s equivalent “IP group” updated from the JSON). **Do not** leave `5432` open to the world without `hostssl` and a deliberate risk decision.
2. Use a **TLS certificate** Postgres clients trust (commercial CA, or Let’s Encrypt on the DB if you terminate TLS on Postgres—follow [PostgreSQL SSL](https://www.postgresql.org/docs/current/ssl-tcp.html)). Name on the cert should match the **hostname** you enter in Power BI.
3. After publishing from Desktop, open the **semantic model** in the Power BI service → **Settings** → **Gateway and cloud connections** → under **Cloud connections**, map the PostgreSQL data source to a **cloud** connection using the same server name, **encrypted** connection, and DB credentials. If refresh fails with certificate errors, align hostname and trust chain with [Troubleshooting: Windows certificate error](#troubleshooting-windows-certificate-error-when-connecting-power-bi) (same class of issue in the cloud path).

**Security checklist (both paths):** dedicated DB user (not superuser), `scram-sha-256`, long random password, only required schemas/tables granted, and [§2.1](#21-optional-expose-postgresql-tcp-5432-restricted) discipline on UFW + provider firewall.

### Recommended: SSH tunnel (easiest and most reliable for Desktop)

**Why this option:** No VPN server to run, no public PostgreSQL port. Traffic is encrypted inside SSH. Same pattern works from home or office if SSH is reachable.

**On the Windows PC** (PowerShell or Command Prompt), with `ssh` available (Windows 10/11 OpenSSH client):

```text
ssh -N -L 15432:127.0.0.1:5432 YOUR_USER@YOUR_VPS_HOST
```

- Leave this window **open** while refreshing data in Power BI.
- Local port **15432** forwards to Postgres on the VPS (`127.0.0.1:5432`).

**Linux / `psql` example (same rule):** connect to the **local** tunnel port, not `5432`:

```bash
PGPASSWORD=your_password psql -h 127.0.0.1 -p 15432 -U keap_user -d keap_db
```

#### Troubleshooting: “Connection to 127.0.0.1:5432 refused”

That message names the **target** port. Two common cases:

1. **Client on your PC is using port `5432`.** The tunnel maps **local `15432` → VPS `127.0.0.1:5432`**. On your laptop, `127.0.0.1:5432` is almost always **not** the tunnel (unless you used `-L 5432:...`). Use **`-p 15432`** (Power BI, `psql`, DBeaver, etc.). If you intentionally forwarded local `5432`, then use `5432` locally—but the default in this doc is `15432`.

2. **You already use `15432` but still get refused.** Then SSH reached the VPS, but **nothing accepted TCP on the VPS at `127.0.0.1:5432`** (Postgres stopped, wrong install, or DB only in Docker without a host publish). On the VPS run:

   ```bash
   sudo systemctl status postgresql
   sudo ss -tlnp | grep 5432
   ```

   You should see Postgres listening on `127.0.0.1:5432` or `*:5432`. If Postgres runs **only inside Docker** and is not published on the host loopback, change the tunnel to match how the container is published (e.g. `-L 15432:127.0.0.1:5432` only works if the host actually listens on `127.0.0.1:5432`).

**In Power BI Desktop:**

1. **Get data** → **Database** → **PostgreSQL database**.
2. **Server:** `127.0.0.1`
3. **Port:** `15432`
4. **Database:** `keap_db` (or your `DB_NAME`).
5. **Data connectivity mode:** Import or DirectQuery as needed.
6. Sign in with database user / password (`keap_user` / password you set).

### Troubleshooting: Windows certificate error when connecting (Power BI)

**Symptom:** Power BI shows *Unable to connect* with details like *The remote certificate is invalid according to the validation procedure.*

**Cause:** The PostgreSQL connector uses **TLS to the database** when encryption is on. You reach Postgres as `127.0.0.1` through an **SSH tunnel**, but the server’s certificate is almost always for the **VPS hostname** (or is self-signed). Windows then rejects it (name mismatch or untrusted issuer).

**No TLS controls in the PostgreSQL dialog:** On **Power BI Desktop**, the **PostgreSQL database** dialog’s **Advanced options** only include command timeout, SQL statement, and navigation flags—**not** SSL or encryption. That matches [Microsoft’s PostgreSQL connector documentation](https://learn.microsoft.com/en-us/power-query/connectors/postgresql). Encryption is adjusted elsewhere (below).

**Fix (recommended when you use an SSH tunnel):** The tunnel already encrypts traffic end-to-end. Use one of these:

1. **Data source settings (most common)**  
   **File** → **Options and settings** → **Data source settings** → select your PostgreSQL source → **Edit** (or edit permissions / connection as your build labels it). Find **Encrypt connection** (or equivalent) and **clear** it, then save and reconnect.

2. **First-connection prompt**  
   If Power BI shows a dialog that the connection is **not encrypted** or asks about encryption support, **OK** / proceed with an **unencrypted** database connection is appropriate when SSH is carrying the ciphertext.

3. **ODBC fallback**  
   If you still cannot disable encryption for that connector, use **Get data** → **ODBC** (install the [PostgreSQL ODBC driver](https://www.postgresql.org/ftp/odbc/versions/) if needed) and put `sslmode=disable` in the connection string (along with host `127.0.0.1`, port `15432`, database, user, password). Traffic remains protected by the SSH tunnel.

**Also check:** The SSH tunnel is still running. If the dialog has **separate** Server and Port fields, use **Server** `127.0.0.1` and **Port** `15432`; if it only has one **Server** box, `127.0.0.1:15432` is valid for the Power Query `PostgreSQL.Database` function.

### SSH keys and ssh-agent (Windows, fewer prompts)

By default, `ssh` asks for your **VPS password** each time you start the tunnel. A **key pair** lets you authenticate without typing the password (or you type a **key passphrase** once per Windows session via the agent).

#### 1. Create a key on the PC (once)

PowerShell:

```powershell
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\id_ed25519_keap -C "powerbi-tunnel"
```

Press Enter for no passphrase (tunnel starts with no prompts), or set a passphrase (more secure; use step 3 so you only enter it once after login).

#### 2. Install the public key on the VPS (once)

Show the public key:

```powershell
Get-Content $env:USERPROFILE\.ssh\id_ed25519_keap.pub
```

On the VPS (as the Linux user you SSH as, not necessarily `root`):

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo 'PASTE_THE_ONE_LINE_.pub_CONTENT_HERE' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Or from the PC (if `ssh-copy-id` is available):

```powershell
type $env:USERPROFILE\.ssh\id_ed25519_keap.pub | ssh YOUR_USER@YOUR_VPS_HOST "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Ensure the VPS allows keys: in `/etc/ssh/sshd_config`, `PubkeyAuthentication yes` (default). Reload: `sudo systemctl reload ssh`.

#### 3. ssh-agent (optional; for passphrase-protected keys)

So you are not asked the **key** passphrase on every tunnel:

```powershell
Get-Service ssh-agent | Set-Service -StartupType Manual
Start-Service ssh-agent
ssh-add $env:USERPROFILE\.ssh\id_ed25519_keap
```

`ssh-add -l` lists loaded keys. After a reboot, run `Start-Service ssh-agent` and `ssh-add` again (or use a key with no passphrase and skip the agent).

#### 4. Tunnel using the key

```powershell
ssh -N -L 15432:127.0.0.1:5432 -i $env:USERPROFILE\.ssh\id_ed25519_keap YOUR_USER@YOUR_VPS_HOST
```

Optional **`~/.ssh/config`** on the PC (`C:\Users\You\.ssh\config`) to shorten the command:

```text
Host keap-vps
    HostName srv1498298.hstgr.cloud
    User your_linux_user
    IdentityFile ~/.ssh/id_ed25519_keap
```

Then:

```powershell
ssh -N -L 15432:127.0.0.1:5432 keap-vps
```

### Alternatives (when to use)

| Method | Use case |
|--------|----------|
| **VPN (e.g. WireGuard)** | Many internal services, multiple users, fixed office network. More moving parts on the VPS. |
| **Locked-down DB** (expose `5432` only to your IP: `pg_hba` + UFW + provider firewall; see [§2.1](#21-optional-expose-postgresql-tcp-5432-restricted)) | Unattended refresh from a **fixed** client IP (rare for Power BI Service—prefer **gateway** or Microsoft IP allowlists; see [Power BI Service (cloud refresh)](#power-bi-service-cloud-refresh)). |

For a single analyst and typical KVM 2 setup, **SSH tunnel + Import** (refresh when connected) is the simplest reliable path for **Desktop**. For **Power BI Service**, prefer a **gateway** or a **TLS-hardened** endpoint with a **restricted** inbound policy, not an open `5432`.

---

## Checklist

- [ ] UFW: SSH allowed; Postgres **not** on the public internet **or** (if using [§2.1](#21-optional-expose-postgresql-tcp-5432-restricted)) `5432` allowed **only** from known client IP(s) **or** from maintained Microsoft/Azure allowlists for [Power BI Service (cloud refresh)](#power-bi-service-cloud-refresh).
- [ ] `.env` complete; `alembic upgrade head` applied.
- [ ] Keap OAuth completed; tokens in DB.
- [ ] Timer or cron for `--update` if needed.
- [ ] **Power BI Desktop:** `127.0.0.1:15432` with SSH tunnel active (certificate issues: [Troubleshooting](#troubleshooting-windows-certificate-error-when-connecting-power-bi)).
- [ ] **Power BI Service:** semantic model mapped to an **on-premises gateway** (gateway host can reach Postgres) **or** a **cloud connection** to a **TLS** (`hostssl`) endpoint with firewall rules you can sustain; see [Power BI Service (cloud refresh)](#power-bi-service-cloud-refresh).

---

## Related documentation

- [connect-pgadmin-windows.md](connect-pgadmin-windows.md) — pgAdmin on Windows via SSH tunnel or direct TCP
- [08-deployment-guide.md](../08-deployment-guide.md) — general deployment
- [06-security-considerations.md](../06-security-considerations.md) — security context
- Repository [README.md](../../README.md) — usage and structure
