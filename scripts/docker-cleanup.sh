#!/bin/sh
# Free disk space after building images: drops unused images and build caches, keeps running
# containers and every volume (database of Redis, certificates, uploads).
# On macOS with Colima it also returns the freed space to the Mac (the VM disk only grows otherwise).
set -eu
docker image prune --all --force
docker builder prune --all --force
if command -v colima >/dev/null 2>&1 && colima status >/dev/null 2>&1; then
  colima ssh -- sudo fstrim -v /mnt/lima-colima
fi
docker system df
