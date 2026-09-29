#!/usr/bin/env bash
set -euo pipefail
# Operator-side entry point; scientific workers use the installed capability.
bootstrap_python="${SIMJECTURE_BOOTSTRAP_PYTHON:-/usr/bin/python3}"
exec "$bootstrap_python" "$(dirname "$0")/bootstrap.py" "$@"
