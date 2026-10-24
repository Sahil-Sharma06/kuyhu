#!/usr/bin/env bash
# Core domain logic must stay at >= 90% line coverage (run after pytest --cov).
set -euo pipefail
python -m coverage report --include="app/services/selection.py,app/services/metrics.py" --fail-under=90
