#!/usr/bin/env bash
set -euo pipefail
bootstrap_python="${SIMJECTURE_BOOTSTRAP_PYTHON:-python3}"
exec "$bootstrap_python" "$(dirname "$0")/bootstrap.py" "$@"
