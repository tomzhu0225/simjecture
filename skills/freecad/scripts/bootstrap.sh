#!/usr/bin/env bash
set -euo pipefail
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
runtime_profile="freecad"
source "$project_root/scripts/runtime_environment.sh"
"$python" "$project_root/scripts/finalize_geometry_runtime.py" "$runtime_profile" "$prefix"
