# VPS deployment (KVM 2): Ubuntu, PostgreSQL, Keap extract

This guide targets a **Hostinger-style KVM VPS** used **only** for:

- **Ubuntu** (24.04 LTS recommended)
- **PostgreSQL** (data store for Keap extract + OAuth tokens)
- **Keap data extractor** (scheduled CLI runs)

**Power BI Desktop** runs on a **Windows PC**. The recommended way to reach PostgreSQL from that PC is an **SSH tunnel** (see [Connect Power BI to PostgreSQL](#connect-power-bi-to-postgresql)).

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
│  • Postgres: localhost:5432 only          │
│  • Extract: cron/systemd → python -m src │
└─────────────────┬───────────────────────┘
                  │ SSH (port 22)
                  │   optional: -L forwards DB (and OAuth once)
┌─────────────────▼───────────────────────┐
│ Windows PC                               │
│  • Power BI Desktop → 127.0.0.1:<port>  │
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

**Keep PostgreSQL on localhost only** (default on Ubuntu: `listen_addresses = 'localhost'` in `postgresql.conf`). Do not expose `5432` to the internet; access from Windows is via **SSH tunnel** below.

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

Production Keap apps expect an **HTTPS** redirect URI. On the VPS, typical approach:

1. Point a **DNS name** (e.g. `keap-oauth.example.com`) to the server IP.
2. Install **nginx** and **Certbot** (Let’s Encrypt); terminate TLS on nginx.
3. For **one-time authorization**, proxy `https://<your-host>/oauth/callback` to the local callback port used by `python -m src.auth.authorize` (see app docs; default dev URI in `.env.example` uses port `8000`).
4. Set `KEAP_REDIRECT_URI` in `.env` to match the **exact** URL registered in the Keap Developer Portal.

Run authorization once on the server:

```bash
cd /opt/keap-extract/app && source venv/bin/activate
python -m src.auth.authorize
```

Complete the browser flow; tokens are stored in PostgreSQL.

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
OnCalendar=*-*-* 02:30:00
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

### Recommended: SSH tunnel (easiest and most reliable)

**Why this option:** No VPN server to run, no public PostgreSQL port. Traffic is encrypted inside SSH. Same pattern works from home or office if SSH is reachable.

**On the Windows PC** (PowerShell or Command Prompt), with `ssh` available (Windows 10/11 OpenSSH client):

```text
ssh -N -L 15432:127.0.0.1:5432 YOUR_USER@YOUR_VPS_HOST
```

- Leave this window **open** while refreshing data in Power BI.
- Local port **15432** forwards to Postgres on the VPS (`127.0.0.1:5432`).

**In Power BI Desktop:**

1. **Get data** → **Database** → **PostgreSQL database**.
2. **Server:** `127.0.0.1`
3. **Port:** `15432`
4. **Database:** `keap_db` (or your `DB_NAME`).
5. **Data connectivity mode:** Import or DirectQuery as needed.
6. Sign in with database user / password (`keap_user` / password you set).

Optional: use **SSH key authentication** and `ssh-agent` so you are not prompted every time.

### Alternatives (when to use)

| Method | Use case |
|--------|----------|
| **VPN (e.g. WireGuard)** | Many internal services, multiple users, fixed office network. More moving parts on the VPS. |
| **Locked-down DB** (`pg_hba` + firewall allow **only** your static public IP) | Unattended scheduled refresh without a tunnel; requires static IP and careful hardening. |

For a single analyst and typical KVM 2 setup, **SSH tunnel + Import** (refresh when connected) is the simplest reliable path.

---

## Checklist

- [ ] UFW: SSH allowed; Postgres **not** exposed publicly.
- [ ] `.env` complete; `alembic upgrade head` applied.
- [ ] Keap OAuth completed; tokens in DB.
- [ ] Timer or cron for `--update` if needed.
- [ ] Power BI connects via `127.0.0.1:15432` with SSH tunnel active.

---

## Related documentation

- [08-deployment-guide.md](../08-deployment-guide.md) — general deployment
- [06-security-considerations.md](../06-security-considerations.md) — security context
- Repository [README.md](../../README.md) — usage and structure
