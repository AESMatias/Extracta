---
type: feature
title: Nginx instead of Caddy at the edge
tags: [ftd, nginx, https, certbot, deploy]
branch: feat/project-skeleton
---

# Nginx instead of Caddy at the edge

## Intent

The owner prefers Nginx, the industry-standard web server, over Caddy. Nginx must do everything
Caddy did: serve the static Next.js site, proxy `/api` to Flask with the same forwarded headers,
send the same security headers, and serve HTTPS in production with certificates that renew by
themselves. Constitution amended to v4.0.0 (principles 33-35).

## Scope

- In: Nginx configuration and image, a certbot service for Let's Encrypt (production-only
  Compose profile), `.env` variables, deployment guide, README, CI scan of the new images.
- Not now: HTTP/3 (QUIC) — Caddy served it; Nginx needs a separate QUIC listener and extra UDP
  setup that a single small server does not need.

## Design

- `frontend/nginx/nginx.conf`: main settings (no version in headers, gzip, Docker DNS resolver
  re-checked every 10 s, HSTS only over HTTPS).
- `frontend/nginx/snippets/site.conf`: the site, shared by both modes: `/api/` proxy with
  `X-Forwarded-For/-Proto/-Host` (Flask trusts one hop), streamed uploads
  (`proxy_request_buffering off`), 1-year cache for hashed `/_next/static/` files, `no-cache` for
  pages, `try_files` for `/login` → `login.html`, the site's own 404 page.
- `frontend/nginx/40-extracta-site.sh` runs at container start: `SITE_DOMAIN` empty → plain HTTP;
  set → HTTPS server with a 7-day self-signed placeholder until certbot delivers the real
  certificate, then a watcher installs new or renewed certificates and reloads Nginx within 60 s.
- `docker/certbot/`: the official certbot image plus the security patches it lags behind on;
  `renew.sh` requests the certificate over the HTTP-01 webroot, re-checks every 12 hours, and
  retries failures every 30 minutes (below Let's Encrypt's 5 failures per hour).
- Unknown host names on 443 get their TLS handshake refused (`ssl_reject_handshake`).

## Checklist

| # | Task | Proof | Status |
|---|------|-------|--------|
| 1 | Nginx image and config | `nginx -t` passes in both modes; image builds; Nginx 1.30.5 | ✅ |
| 2 | Same behaviour as Caddy | Pages 200, unknown page 404 with the site's page, security headers and CSP present, hashed assets cached 1 year and gzipped, `/api` answers with Flask's own headers | ✅ |
| 3 | Full flow through Nginx | Accounts end-to-end script: registration, Free-plan limits, 2 PDFs processed in 5.6 s, ownership isolation, admin, upgrade, save to DB, cross-site POST 403 | ✅ |
| 4 | Certificate hand-over | Simulated certbot writing a certificate into the shared volume: Nginx installed it and reloaded by itself within 60 s | ✅ |
| 5 | Images scanned | Trivy, fixable HIGH/CRITICAL: frontend 0; official certbot 8 → 0 after `apk upgrade`, patched `msgpack`/`setuptools` and removing pip | ✅ |
| 6 | Docs | `.env.sample`, `docs/DEPLOY.md` (HTTPS step by step, troubleshooting), README, constitution v4.0.0, decisions log | ✅ |
| 7 | Real certificate | Needs the owner's domain and server | ⏳ |

## Evidence

- Memory: Nginx 4 MiB (Caddy used 12 MiB). Limits: frontend 64 MB, certbot 128 MB (production
  only): 1344 MB locally, 1472 MB in production.
- The old `caddy_data` and `caddy_config` volumes are no longer used; remove them with
  `docker volume rm pdf_process_pipeline_caddy_data pdf_process_pipeline_caddy_config`.

## Next

Owner: on the server, set `SITE_DOMAIN`, `LETSENCRYPT_EMAIL` and `COMPOSE_PROFILES=https`, then
follow `docs/DEPLOY.md`.
