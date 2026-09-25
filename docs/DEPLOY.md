# Deploying Extracta to a server

This guide takes an empty Linux server (VPS) to a running site with HTTPS. It assumes Ubuntu
24.04, 2 GB of RAM, 1–2 vCPUs and at least 25 GB of disk. Every command runs on the server
unless it says otherwise.

```
Internet ──443/80──> Caddy (frontend container: website + HTTPS) ──/api──> Flask (web) ──> Redis <── Celery (worker)
                                                                         └──> Supabase (PostgreSQL)   └──> Gemini
```

Only ports 80 and 443 are open to the world. Flask, Redis and the worker are reachable only
inside Docker's private network.

---

## 0. What you need before starting

| Item | Where |
|---|---|
| A server with a public IP | Any VPS provider (Hetzner, DigitalOcean, Vultr, Linode…) |
| A domain name | e.g. `extracta.example.com`, from any registrar |
| Supabase project | Its **Session pooler** connection string (see `.env.sample`) |
| Gemini API key | <https://aistudio.google.com/apikey> |
| Optional: Google sign-in | OAuth client ID and secret (step 7) |
| Optional: PayPal payments | Live REST app Client ID and secret (step 8) |

## 1. Point the domain to the server

In your domain registrar's DNS panel, create an **A record**:

| Type | Name | Value |
|---|---|---|
| A | `extracta` (or `@` for the root domain) | the server's public IPv4 |

Wait until it resolves (usually minutes). From your own computer:

```bash
dig +short extracta.example.com
```

It must print the server's IP. Caddy cannot get a certificate until it does.

## 2. Prepare the server

Connect and update the system:

```bash
ssh root@YOUR_SERVER_IP
apt update && apt upgrade -y
```

**Firewall**: allow SSH, HTTP and HTTPS only.

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable
```

**Swap (2 GB)**: required on a 2 GB server. Building the images (Next.js and Caddy) needs more
memory than the running app, and swap prevents the build from being killed.

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
sysctl vm.swappiness=10 && echo 'vm.swappiness=10' >> /etc/sysctl.conf
```

**Docker** (official installer, includes Compose):

```bash
curl -fsSL https://get.docker.com | sh
docker compose version
```

## 3. Get the code

```bash
cd /opt
git clone https://github.com/AESMatias/Extracta.git extracta
cd extracta
```

## 4. Configure `.env`

```bash
cp .env.sample .env
nano .env
```

Every variable is explained inside the file. For production, change at least these:

| Variable | Production value |
|---|---|
| `GEMINI_API_KEY` | your key |
| `DATABASE_URL` | Supabase **Session pooler** string |
| `SECRET_KEY` | a new random value: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ADMIN_PASSWORD` | a long password only you know (at least 12 characters) |
| `PUBLIC_BASE_URL` | `https://extracta.example.com` |
| `SITE_ADDRESS` | `extracta.example.com` |
| `HTTP_PORT` / `HTTPS_PORT` | `80` / `443` |
| `SESSION_COOKIE_SECURE` | `true` |
| `REQUIRE_MANUAL_APPROVAL` | `true` if you want to approve every new account in /admin |

Protect the file: `chmod 600 .env`. Never commit it.

## 5. Build and start

```bash
docker compose build          # first time: 5-10 minutes on a small server
docker compose up -d
./scripts/docker-cleanup.sh   # frees the disk space used by the build
```

On start, the `web` container applies the database migrations automatically (Alembic), then
starts the API. Caddy requests the HTTPS certificate on the first visit to the domain.

## 6. Check that everything works

```bash
docker compose ps             # web, redis healthy; frontend and worker up
docker compose logs -f web    # "Database schema is up to date", then gunicorn
docker stats --no-stream      # memory stays well below the limits
curl -I https://extracta.example.com/api/health
```

Then open `https://extracta.example.com`, create an account and process a PDF. Open
`https://extracta.example.com/admin` and sign in with `ADMIN_PASSWORD`.

## 7. Optional: Sign in with Google

1. Open <https://console.cloud.google.com/apis/credentials> and create a project if needed.
2. **OAuth consent screen**: External, app name "Extracta", your support email, scopes
   `email`, `profile`, `openid`. Publish it when you are ready for any Google account to sign in.
3. **Create credentials → OAuth client ID → Web application**.
4. **Authorized redirect URI**: `https://extracta.example.com/api/auth/google/callback`
5. Copy the client ID and secret into `.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`).
6. Apply: `docker compose up -d` (it recreates the containers that read `.env`).

The Google button appears automatically on the sign-in and registration pages.

## 8. Optional: Payments with PayPal

1. Open <https://developer.paypal.com/dashboard/applications> with your PayPal **business**
   account.
2. **Test first**: in the **Sandbox** tab, create an app, copy its Client ID and Secret into
   `.env` with `PAYPAL_ENV=sandbox`, and buy a plan with a sandbox buyer account
   (Sandbox → Accounts). No real money moves.
3. **Go live**: in the **Live** tab create an app, then set `PAYPAL_ENV=live` and the live
   `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET`.
4. Apply: `docker compose up -d`.

Plans and prices are in `app/plans.py` (USD, 30-day passes). The server always decides the
price and verifies every order before capturing it; the browser only shows PayPal's buttons.

## 9. Updating to a new version

```bash
cd /opt/extracta
git pull
docker compose build
docker compose up -d
./scripts/docker-cleanup.sh
```

Migrations run automatically on start. Rebuilding also installs the latest Debian security
patches into the images.

## 10. Operations

| Task | Command |
|---|---|
| Follow logs | `docker compose logs -f web worker frontend` |
| Restart everything | `docker compose restart` |
| Stop | `docker compose down` (volumes and certificates are kept) |
| Memory usage | `docker stats --no-stream` |
| Disk usage | `docker system df` and `df -h /` |
| Security scan | `docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image --ignore-unfixed --severity HIGH,CRITICAL pdf-process-pipeline:latest` |

**Backups**: the data lives in Supabase (see your Supabase plan's backup policy). Keep a copy of
`.env` somewhere safe and offline: without `SECRET_KEY` every session is invalidated, and
without the other values the app cannot start.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| The site does not load over HTTPS | DNS does not point to the server yet, or ports 80/443 are closed. Check `dig`, `ufw status`, and `docker compose logs frontend`. |
| `Cross-site request refused` (403) | `PUBLIC_BASE_URL` does not match the address in the browser (http vs https, www vs no www). |
| The build stops with `Killed` / exit 137 | Not enough memory: check that swap is on (`swapon --show`). |
| Google says `redirect_uri_mismatch` | The redirect URI in Google Cloud must be exactly `PUBLIC_BASE_URL` + `/api/auth/google/callback`. |
| Uploads fail at once for everyone | `docker compose logs worker`; check `GEMINI_API_KEY` and the Gemini quota. |
| `web` is unhealthy | `docker compose logs web`: usually `DATABASE_URL` (use the Session pooler) or a missing variable. |
