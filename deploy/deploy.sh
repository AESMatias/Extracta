#!/usr/bin/env bash
# Deploy the latest main on this server: pull, build, restart, wait until healthy, and roll back
# to the previous version if the new one does not come up.
#
#   deploy/deploy.sh            deploy if origin/main has new commits
#   deploy/deploy.sh --force    rebuild and restart even when nothing changed
#
# GitHub Actions runs it over SSH after CI passes on main (see docs/DEPLOY.md, "Automatic
# deploys"); it can also be run by hand. Only one deploy runs at a time. Database migrations run
# when the web container starts and are not undone by a rollback, so keep them backward
# compatible (add columns and tables; drop them in a later release).
set -euo pipefail

BRANCH=main
IMAGES=(pdf-process-pipeline extracta-frontend)
HEALTH_TIMEOUT=${DEPLOY_HEALTH_TIMEOUT:-240} # seconds; Docker health checks run every 30 s
HEALTH_POLL=${DEPLOY_HEALTH_POLL:-5}

cd "$(dirname "$0")/.."

log() { printf '%s  %s\n' "$(date -u +%H:%M:%S)" "$*"; }
fail() {
	log "ERROR: $*"
	exit 1
}

# One deploy at a time: a second push waits for the first deploy, then deploys what is newest.
if command -v flock >/dev/null 2>&1; then
	exec 9>/tmp/extracta-deploy.lock
	flock -w 1800 9 || fail "another deploy has been running for 30 minutes"
fi

[[ -f .env ]] || fail ".env is missing: copy .env.sample and fill it in first"
[[ "$(git rev-parse --abbrev-ref HEAD)" == "$BRANCH" ]] || fail "this checkout is not on $BRANCH"

git fetch --quiet origin "$BRANCH"
old=$(git rev-parse HEAD)
new=$(git rev-parse "origin/$BRANCH")
if [[ "$old" == "$new" && "${1:-}" != "--force" ]]; then
	log "already at ${new:0:7}: nothing to deploy"
	exit 0
fi

log "deploying ${old:0:7} -> ${new:0:7}"
git log --oneline "$old..$new" | sed 's/^/    /'

# Keep the running images as :previous so a failed deploy can go back to them in seconds.
for image in "${IMAGES[@]}"; do
	if docker image inspect "$image:latest" >/dev/null 2>&1; then
		docker image tag "$image:latest" "$image:previous"
	fi
done

git merge --ff-only --quiet "origin/$BRANCH" || fail "cannot fast-forward to origin/$BRANCH (local changes on the server?)"

log "building images (the site keeps running the old version meanwhile)"
if ! docker compose build; then
	git reset --hard --quiet "$old"
	fail "build failed: nothing was restarted, the server still runs ${old:0:7}"
fi

log "starting the new containers"
docker compose up -d --remove-orphans

healthy() {
	local service id status
	for service in web frontend; do
		id=$(docker compose ps -q "$service")
		[[ -n "$id" ]] || return 1
		status=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id")
		[[ "$status" == "healthy" ]] || return 1
	done
	id=$(docker compose ps -q worker) # no health check: it must at least be running
	[[ -n "$id" && "$(docker inspect -f '{{.State.Running}}' "$id")" == "true" ]]
}

log "waiting for web, frontend and worker to be healthy (up to ${HEALTH_TIMEOUT}s)"
waited=0
until healthy; do
	if ((waited >= HEALTH_TIMEOUT)); then
		log "the new version did not become healthy; last web logs:"
		docker compose logs --tail 30 web | sed 's/^/    /' || true
		log "rolling back to ${old:0:7}"
		git reset --hard --quiet "$old"
		for image in "${IMAGES[@]}"; do
			if docker image inspect "$image:previous" >/dev/null 2>&1; then
				docker image tag "$image:previous" "$image:latest"
			fi
		done
		docker compose up -d --remove-orphans
		fail "deploy of ${new:0:7} failed and was rolled back to ${old:0:7}"
	fi
	sleep "$HEALTH_POLL"
	waited=$((waited + HEALTH_POLL))
done

# Free disk: untagged images from older builds and week-old build cache. The :previous images stay
# for the next rollback.
docker image prune --force >/dev/null
docker builder prune --force --filter until=168h >/dev/null
log "deployed ${new:0:7} in production"
