#!/usr/bin/env bash
# Clone the repo into a temp dir, follow the README's Docker steps and check the stack is healthy.
#
# Usage: scripts/verify_clean_clone.sh [repo-url-or-path] [ref]
#   defaults: this repository, current HEAD. Uses ports 18000/18080 to avoid clashing with dev servers.
set -euo pipefail

REPO="${1:-$(git rev-parse --show-toplevel)}"
REF="${2:-$(git rev-parse HEAD)}"
export BACKEND_PORT="${BACKEND_PORT:-18000}" FRONTEND_PORT="${FRONTEND_PORT:-18080}"
PROJECT="wfm-verify-$$"
WORK="$(mktemp -d)"

cleanup() {
  (cd "$WORK/repo" 2>/dev/null && docker compose -p "$PROJECT" down --volumes --rmi local >/dev/null 2>&1) || true
  rm -rf "$WORK"
}
trap cleanup EXIT

echo "==> cloning $REPO @ $REF into $WORK"
git clone --quiet "$REPO" "$WORK/repo"
git -C "$WORK/repo" checkout --quiet "$REF"
cd "$WORK/repo"

for f in README.md docker-compose.yml backend/Dockerfile frontend/Dockerfile backend/.dockerignore frontend/.dockerignore backend/data/actuals.csv backend/data/forecasts.csv; do
  [[ -f "$f" ]] || { echo "missing $f"; exit 1; }
done

echo "==> docker compose up --build (README step)"
docker compose -p "$PROJECT" up -d --build

wait_for() {
  for _ in $(seq 1 60); do curl -fsS "$1" >/dev/null 2>&1 && return 0; sleep 2; done
  echo "timed out waiting for $1"; docker compose -p "$PROJECT" logs --tail 50; return 1
}
wait_for "http://localhost:$BACKEND_PORT/api/health"
wait_for "http://localhost:$FRONTEND_PORT/api/health"

echo "==> checks"
curl -fsS "http://localhost:$FRONTEND_PORT/" | grep -q "<title>GB Wind Forecast Monitor</title>"
curl -fsS "http://localhost:$FRONTEND_PORT/api/metrics" | grep -q '"n":744'
for svc in backend frontend; do
  user="$(docker compose -p "$PROJECT" exec -T "$svc" id -u)"
  [[ "$user" != "0" ]] || { echo "$svc runs as root"; exit 1; }
  echo "$svc runs as uid $user"
done
echo "OK: clean clone builds, runs as non-root and is healthy"
