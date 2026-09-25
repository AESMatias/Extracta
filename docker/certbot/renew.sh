#!/bin/sh
# certbot service (production only): gets the Let's Encrypt certificate for SITE_DOMAIN, then
# checks twice a day and renews it when it is 30 days from expiry. Nginx serves the validation
# files from the shared webroot and installs new certificates by itself within a minute.
set -u
trap 'exit 0' TERM INT

: "${SITE_DOMAIN:?Set SITE_DOMAIN in .env}"
: "${LETSENCRYPT_EMAIL:?Set LETSENCRYPT_EMAIL in .env (expiry warnings are sent there)}"

while :; do
    if certbot certonly --webroot --webroot-path /var/www/certbot \
        --domain "$SITE_DOMAIN" --email "$LETSENCRYPT_EMAIL" \
        --agree-tos --no-eff-email --non-interactive --keep-until-expiring; then
        pause=43200  # 12 hours
    else
        # Let's Encrypt allows 5 failed validations per hour: never retry faster than this.
        echo "certbot: could not get the certificate; retrying in 30 minutes."
        echo "certbot: check that the domain's DNS points to this server and that port 80 is open."
        pause=1800
    fi
    sleep "$pause" &
    wait $!
done
