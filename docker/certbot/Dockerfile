# syntax=docker/dockerfile:1
# certbot (production only): the official image plus the security patches it lags behind on,
# and the loop that obtains and renews the Let's Encrypt certificate (renew.sh).
FROM certbot/certbot:v5.8.0
# pip is removed at the end: certbot does not need it to run, and pip bundles its own old copies
# of msgpack and setuptools.
RUN apk upgrade --no-cache \
    && pip install --no-cache-dir --upgrade "msgpack>=1.2.1" "setuptools>=78.1.1" \
    && pip uninstall --yes pip
COPY renew.sh /renew.sh
ENTRYPOINT ["/bin/sh", "/renew.sh"]
