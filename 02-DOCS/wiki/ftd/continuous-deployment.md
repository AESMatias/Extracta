---
title: Continuous deployment from main to the server
status: done
updated: 2026-09-25
---

# Continuous deployment

## Intent

Every push to `main` that passes CI reaches production without logging in to the server, like
Vercel, and a broken release never stays online.

## Design

- `deploy/deploy.sh` (on the server): lock, fetch `main`, tag the running images `:previous`,
  fast-forward, build while the old version serves, `up -d`, wait for Docker health checks (web,
  frontend; worker running), roll back images and commit if unhealthy after 240 s, prune.
- CI job `deploy`: needs backend and frontend, runs on pushes to `main` when the `DEPLOY_HOST`
  variable exists, `production` environment, no cancellation mid-deploy. It only opens SSH.
- The SSH key is pinned in `authorized_keys` with `command=".../deploy.sh"` and no forwarding or
  pty, and the host key is checked (`DEPLOY_KNOWN_HOSTS`): a leaked key can only redeploy `main`.

## Checklist

| # | Task | Proof | Status |
|---|------|-------|--------|
| 1 | Deploy script | Simulated `docker` in a throwaway git setup: nothing new → exit 0; healthy → deployed; never healthy → rolled back to the previous commit and images, exit 1; build fails → no restart; retry → deployed; not on main → refused | ✅ |
| 2 | CI deploy job | YAML parses; needs backend and frontend; skipped without `DEPLOY_HOST` | ✅ |
| 3 | Docs | DEPLOY sections 10 and "Automatic deploys" | ✅ |
| 4 | First real run on the server | Owner sets the key, secrets and variables | ⏳ |
