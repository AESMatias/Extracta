#!/bin/sh
# Runs at container start (the official image executes /docker-entrypoint.d/*.sh before Nginx).
# SITE_DOMAIN empty -> plain HTTP (local). SITE_DOMAIN set -> HTTPS with the Let's Encrypt
# certificate that the certbot service keeps in the shared /etc/letsencrypt volume.
set -eu

conf=/etc/nginx/conf.d/extracta.conf

# Behind another proxy on this host (e.g. the server's own Nginx, publishing this container on
# 127.0.0.1): take the visitor's address from the X-Forwarded-For header that proxy sets, but only
# when the request comes from one of the REAL_IP_FROM networks. Otherwise every visitor would share
# the proxy's address, and so its rate limits.
realip=/etc/nginx/conf.d/00-real-ip.conf
: > "$realip"
if [ -n "${REAL_IP_FROM:-}" ]; then
    for network in $(echo "$REAL_IP_FROM" | tr ',' ' '); do
        echo "set_real_ip_from $network;" >> "$realip"
    done
    echo "real_ip_header X-Forwarded-For;" >> "$realip"
    echo "extracta: visitor addresses from X-Forwarded-For sent by $REAL_IP_FROM"
fi

if [ -z "${SITE_DOMAIN:-}" ]; then
    cp /etc/nginx/extracta/http.conf "$conf"
    echo "extracta: serving plain HTTP (SITE_DOMAIN is empty)"
    exit 0
fi

envsubst '${SITE_DOMAIN}' < /etc/nginx/extracta/https.conf.template > "$conf"

live="/etc/letsencrypt/live/$SITE_DOMAIN"
certs=/etc/nginx/certs
mkdir -p "$certs"

install_certificate() {
    # cp -L: the files in live/ are symlinks into archive/.
    cp -L "$live/fullchain.pem" "$certs/fullchain.pem"
    cp -L "$live/privkey.pem" "$certs/privkey.pem"
    chmod 600 "$certs/privkey.pem"
}

if [ -f "$live/fullchain.pem" ]; then
    install_certificate
    echo "extracta: HTTPS for $SITE_DOMAIN with the Let's Encrypt certificate"
else
    # Nginx cannot start HTTPS without a certificate, and certbot needs Nginx running to prove it
    # owns the domain. A short-lived self-signed certificate breaks that loop.
    openssl req -x509 -nodes -newkey rsa:2048 -days 7 -subj "/CN=$SITE_DOMAIN" \
        -keyout "$certs/privkey.pem" -out "$certs/fullchain.pem" 2>/dev/null
    chmod 600 "$certs/privkey.pem"
    echo "extracta: no certificate for $SITE_DOMAIN yet; temporary self-signed one until certbot gets it"
fi

# Watch for the first certificate and for renewals; install them and reload Nginx without downtime.
(
    while sleep 60; do
        if [ -f "$live/fullchain.pem" ] && ! cmp -s "$live/fullchain.pem" "$certs/fullchain.pem"; then
            install_certificate && nginx -s reload && echo "extracta: new certificate installed, Nginx reloaded"
        fi
    done
) &
