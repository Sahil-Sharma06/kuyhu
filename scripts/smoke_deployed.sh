#!/usr/bin/env bash
# Smoke test a deployed instance: every /api route must return 200, security headers must be
# present, then the Playwright suite runs against the URL (fails on any console error).
#
# Usage: scripts/smoke_deployed.sh https://<project>.vercel.app
set -euo pipefail

BASE="${1:?usage: smoke_deployed.sh <base-url>}"
BASE="${BASE%/}"
ROUTES=(
  "/api/health"
  "/api/meta"
  "/api/forecast-vs-actual?date=2026-01-15&cutoff=09:30"
  "/api/metrics?start=2026-01-01&end=2026-01-31&cutoff=09:30"
  "/api/error-by-hour"
  "/api/error-by-horizon"
  "/"
)

fail=0
for r in "${ROUTES[@]}"; do
  code="$(curl -s -o /dev/null -w '%{http_code}' "$BASE$r")"
  printf '%-60s %s\n' "$r" "$code"
  [[ "$code" == "200" ]] || fail=1
done

headers="$(curl -sI "$BASE/")"
for h in content-security-policy x-content-type-options x-frame-options; do
  grep -qi "^$h:" <<<"$headers" || { echo "missing header: $h"; fail=1; }
done
[[ $fail == 0 ]] || { echo "FAILED"; exit 1; }

echo "==> Playwright suite against $BASE"
cd "$(dirname "$0")/../frontend"
E2E_BASE_URL="$BASE" npx playwright test --project=desktop-1440 --project=mobile-375
