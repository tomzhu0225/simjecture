#!/usr/bin/env bash
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
prefix=""
project_root=""
while (($#)); do
    case "$1" in
        --prefix) prefix="$2"; shift 2 ;;
        --project-root) project_root="$2"; shift 2 ;;
        --jobs) shift 2 ;;
        --repair) shift ;;
        *) echo "Unsupported argument: $1" >&2; exit 2 ;;
    esac
done
[[ -n "$prefix" && -n "$project_root" ]] || exit 2
project_root="$(cd "$project_root" && pwd)"
bootstrap_python="${SIMJECTURE_BOOTSTRAP_PYTHON:-python3}"
if ! command -v "$bootstrap_python" >/dev/null 2>&1; then
    echo "Bootstrap Python is unavailable; run simjecture install quantum-espresso from its application environment, or set SIMJECTURE_BOOTSTRAP_PYTHON to a working Python executable." >&2
    exit 2
fi
"$bootstrap_python" "$project_root/skills/quantum-espresso/scripts/finalize_runtime.py" --check-disk "$prefix"
runtime_profile="quantum-espresso"
source "$project_root/scripts/runtime_environment.sh"
"$python" "$project_root/skills/quantum-espresso/scripts/finalize_runtime.py" "$prefix"
