# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: build the static site (Next.js "output: export" -> /app/out).
# ---------------------------------------------------------------------------
FROM node:22-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_OPTIONS=--max-old-space-size=1024
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: compile Caddy with the latest Go toolchain and patched Go libraries (what xcaddy does).
# The official binary lags behind Go security releases; this is the internet-facing process.
# ---------------------------------------------------------------------------
FROM golang:1.26-alpine AS caddy
ARG CADDY_VERSION=v2.11.4
WORKDIR /src
ENV CGO_ENABLED=0 GOFLAGS=-trimpath
RUN go mod init extracta/caddy \
    && printf 'package main\n\nimport (\n\tcaddycmd "github.com/caddyserver/caddy/v2/cmd"\n\t_ "github.com/caddyserver/caddy/v2/modules/standard"\n)\n\nfunc main() { caddycmd.Main() }\n' > main.go \
    && go get github.com/caddyserver/caddy/v2@${CADDY_VERSION} \
    && go get -u golang.org/x/crypto golang.org/x/net golang.org/x/text \
    && go get google.golang.org/grpc@v1.83.2 `# 1.84.0 is affected by CVE-2026-84445; 1.83.2 has the fix` \
    && go mod tidy \
    && go build -ldflags "-s -w" -o /usr/bin/caddy .

# ---------------------------------------------------------------------------
# Stage 3: Caddy serves the files and proxies /api. No Node.js at runtime.
# ---------------------------------------------------------------------------
FROM caddy:2.11-alpine
COPY --from=caddy /usr/bin/caddy /usr/bin/caddy
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/out /srv
