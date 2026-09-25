# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: build the static site (Next.js "output: export" -> /app/out).
# ---------------------------------------------------------------------------
FROM node:25-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_OPTIONS=--max-old-space-size=1024
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Nginx serves the files and proxies /api. No Node.js at runtime.
# ---------------------------------------------------------------------------
FROM nginx:1.30-alpine
# apk upgrade: Alpine security patches on every build. openssl: the temporary self-signed
# certificate used only until certbot gets the real one (see nginx/40-extracta-site.sh).
RUN apk upgrade --no-cache \
    && apk add --no-cache openssl \
    && rm -f /etc/nginx/conf.d/default.conf /usr/share/nginx/html/*
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/snippets/ /etc/nginx/snippets/
COPY nginx/sites/ /etc/nginx/extracta/
# The script keeps its executable bit from git.
COPY nginx/40-extracta-site.sh /docker-entrypoint.d/
COPY --from=build /app/out /usr/share/nginx/html
EXPOSE 80 443
