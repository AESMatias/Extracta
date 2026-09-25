# Deploying Extracta to a server

This guide takes an empty Linux server (VPS) to a running site with HTTPS. It assumes Ubuntu
24.04, 2 GB of RAM, 1–2 vCPUs and at least 25 GB of disk. Every command runs on the server
unless it says otherwise.

```
Internet ──443/80──> Nginx (frontend container: website + HTTPS) ──/api──> Flask (web) ──> Redis <── Celery (worker)
                         ▲                                              └──> Supabase (PostgreSQL)   └──> Gemini
                         └── certificates ── certbot (Let's Encrypt, renews them by itself)
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
| An SMTP provider | Sends verification and password emails (step 7) |
| Optional: Google sign-in | OAuth client ID and secret (step 8) |
| Optional: PayPal payments | Live REST app Client ID, secret and webhook ID (step 9) |

## 1. Point the domain to the server

In your domain registrar's DNS panel, create an **A record**:

| Type | Name | Value |
|---|---|---|
| A | `extracta` (or `@` for the root domain) | the server's public IPv4 |

Wait until it resolves (usually minutes). From your own computer:

```bash
dig +short extracta.example.com
```

It must print the server's IP. Let's Encrypt cannot issue the certificate until it does.

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
ufw --force enable
```

**Swap (2 GB)**: required on a 2 GB server. Building the images (Next.js in particular) needs more
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
| `SITE_DOMAIN` | `extracta.example.com` (turns on HTTPS in Nginx) |
| `LETSENCRYPT_EMAIL` | your email: Let's Encrypt warns you there if a renewal ever fails |
| `COMPOSE_PROFILES` | `https` (also starts the certbot service) |
| `HTTP_PORT` / `HTTPS_PORT` | `80` / `443` |
| `SESSION_COOKIE_SECURE` | `true` |
| `REQUIRE_MANUAL_APPROVAL` | `true` if you want to approve every new account in /admin |
| `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `MAIL_FROM` | your email provider (step 7) |

Protect the file: `chmod 600 .env`. Never commit it.

## 5. Build and start

```bash
docker compose build          # first time: 5-10 minutes on a small server
docker compose up -d
./scripts/docker-cleanup.sh   # frees the disk space used by the build
```

On start, the `web` container applies the database migrations automatically (Alembic), then
starts the API.

**HTTPS, step by step** (automatic, about a minute):

1. Nginx starts with a temporary self-signed certificate (the browser would warn for that minute).
2. certbot asks Let's Encrypt for the real certificate; Let's Encrypt checks the domain by
   downloading a file that Nginx serves on port 80.
3. Nginx notices the new certificate within 60 seconds and reloads without dropping connections.
4. certbot checks twice a day and renews 30 days before expiry (certificates last 90 days).

By starting the certbot service you accept the Let's Encrypt Subscriber Agreement.
Follow it with `docker compose logs -f certbot frontend`: you should see
`Successfully received certificate` and then `new certificate installed, Nginx reloaded`.

## 6. Check that everything works

```bash
docker compose ps             # web, redis healthy; frontend and worker up
docker compose logs -f web    # "Database schema is up to date", then gunicorn
docker stats --no-stream      # memory stays well below the limits
curl -I https://extracta.example.com/api/health
```

Then open `https://extracta.example.com`, create an account and process a PDF. Open
`https://extracta.example.com/admin` and sign in with `ADMIN_PASSWORD`.

## 7. Email (required in production)

Extracta emails a link to confirm each new address, password-reset links and a notice when a
password changes. Without SMTP settings those emails only go to the logs, so nobody could
confirm their address.

1. Pick any provider with SMTP: Brevo, Resend, Mailgun or Amazon SES (free tiers are plenty to
   start), or Gmail with an [app password](https://myaccount.google.com/apppasswords) for low
   volume.
2. In the provider, verify your domain (it gives you DNS records: SPF, DKIM) so emails do not
   land in spam.
3. Fill `.env`:

   | Variable | Example |
   |---|---|
   | `SMTP_HOST` / `SMTP_PORT` | `smtp-relay.brevo.com` / `587` |
   | `SMTP_USERNAME` / `SMTP_PASSWORD` | the SMTP credentials the provider shows |
   | `SMTP_SECURITY` | `starttls` for port 587, `ssl` for port 465 |
   | `MAIL_FROM` | `Extracta <no-reply@extracta.example.com>` |

4. Apply: `docker compose up -d`, register a test account and check the email arrives. If it
   does not: `docker compose logs web | grep -i email`.

`REQUIRE_EMAIL_VERIFICATION=true` (the default) means users confirm their email before
uploading or paying. From `/admin` you can mark an address as verified by hand.

## 8. Optional: Sign in with Google

1. Open <https://console.cloud.google.com/apis/credentials> and create a project if needed.
2. **OAuth consent screen**: External, app name "Extracta", your support email, scopes
   `email`, `profile`, `openid`. Publish it when you are ready for any Google account to sign in.
3. **Create credentials → OAuth client ID → Web application**.
4. **Authorized redirect URI**: `https://extracta.example.com/api/auth/google/callback`
5. Copy the client ID and secret into `.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`).
6. Apply: `docker compose up -d` (it recreates the containers that read `.env`).

The Google button appears automatically on the sign-in and registration pages.

## 9. Optional: Payments with PayPal

1. Open <https://developer.paypal.com/dashboard/applications> with your PayPal **business**
   account.
2. **Test first**: in the **Sandbox** tab, create an app, copy its Client ID and Secret into
   `.env` with `PAYPAL_ENV=sandbox`, and buy a plan with a sandbox buyer account
   (Sandbox → Accounts). No real money moves.
3. **Go live**: in the **Live** tab create an app, then set `PAYPAL_ENV=live` and the live
   `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET`.
4. **Webhook** (needed for monthly renewals, cancellations made on PayPal's website and
   refunds): in the same app, **Webhooks → Add Webhook**:
   - URL: `https://extracta.example.com/api/billing/webhook`
   - Events: `Billing subscription activated`, `updated`, `re-activated`, `cancelled`,
     `suspended`, `expired`, `payment failed`; `Payment sale completed`, `refunded`, `reversed`;
     `Checkout order approved`; `Payment capture completed`, `refunded`, `reversed`.
   - Copy the **Webhook ID** it shows into `.env` as `PAYPAL_WEBHOOK_ID`.
5. Apply: `docker compose up -d`.

Users choose a **monthly subscription** (renews automatically, cancel anytime from their account;
they keep the plan until the paid period ends) or **page packs** (pay as you go, pages never expire). Plans and prices
are in `app/plans.py` (USD); the PayPal billing plans are created automatically the first time
someone subscribes. The server always decides the price and verifies every order and
subscription with PayPal; the browser only shows PayPal's buttons. Every webhook is verified
with PayPal and applied exactly once, and a task re-checks subscriptions every 6 hours in case
an event was lost. A refund made from PayPal's dashboard ends the plan time it paid for.

## 10. Updating to a new version

```bash
cd /opt/extracta
git pull
docker compose build
docker compose up -d
./scripts/docker-cleanup.sh
```

Migrations run automatically on start. Rebuilding also installs the latest Debian security
patches into the images.

## 11. Operations

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
| The site does not load over HTTPS | DNS does not point to the server yet, or ports 80/443 are closed. Check `dig`, `ufw status`, and `docker compose logs certbot frontend`. |
| The browser warns about the certificate for more than a few minutes | certbot has not obtained the real certificate yet: `docker compose logs certbot`. Check that `.env` has `COMPOSE_PROFILES=https` and `LETSENCRYPT_EMAIL`, that DNS points here and port 80 is open. It retries every 30 minutes. |
| `Cross-site request refused` (403) | `PUBLIC_BASE_URL` does not match the address in the browser (http vs https, www vs no www). |
| The build stops with `Killed` / exit 137 | Not enough memory: check that swap is on (`swapon --show`). |
| Verification emails do not arrive | `SMTP_HOST` is empty (they go to `docker compose logs web`), or the provider refused them: `docker compose logs web \| grep -i email`. Check the spam folder and the domain's SPF/DKIM records. |
| Renewals do not extend plans | `PAYPAL_WEBHOOK_ID` missing or the webhook URL is wrong; PayPal's dashboard shows each delivery and its response. The 6-hourly check still catches up. |
| Google says `redirect_uri_mismatch` | The redirect URI in Google Cloud must be exactly `PUBLIC_BASE_URL` + `/api/auth/google/callback`. |
| Uploads fail at once for everyone | `docker compose logs worker`; check `GEMINI_API_KEY` and the Gemini quota. |
| `web` is unhealthy | `docker compose logs web`: usually `DATABASE_URL` (use the Session pooler) or a missing variable. |
