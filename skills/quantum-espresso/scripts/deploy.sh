#!/usr/bin/env bash
set -euo pipefail
project_root=""
runtime_base=""
uv="uv"
bubblewrap_dir=""
while (($#)); do
    case "$1" in
        --project-root) project_root="$2"; shift 2 ;;
        --runtime-base) runtime_base="$2"; shift 2 ;;
        --uv) uv="$2"; shift 2 ;;
        --bubblewrap-dir) bubblewrap_dir="$2"; shift 2 ;;
        *) echo "Unsupported argument: $1" >&2; exit 2 ;;
    esac
done
[[ -n "$project_root" ]] || exit 2
project_root="$(cd "$project_root" && pwd)"
if ! command -v "$uv" >/dev/null 2>&1; then
    echo "uv is unavailable: install uv for Linux, or pass --uv /absolute/path/to/uv, then run uv sync --frozen in the checkout." >&2
    exit 2
fi
if [[ -n "$bubblewrap_dir" ]]; then
    [[ -x "$bubblewrap_dir/bwrap" ]] || { echo "Configured Bubblewrap is not executable" >&2; exit 2; }
    export PATH="$bubblewrap_dir:$PATH"
fi
local_prefix="$project_root/.runtime/quantum-espresso-7.4"
if [[ -e "$local_prefix" || -L "$local_prefix" ]]; then
    if [[ -n "$runtime_base" && "$(readlink -m "$local_prefix")" != "$(readlink -m "$runtime_base/quantum-espresso-7.4")" ]]; then
        echo "Existing QE runtime left unchanged; choose its current runtime base." >&2
        exit 2
    fi
else
    runtime_base="${runtime_base:-$HOME/.local/share/simjecture/$(basename "$project_root")/runtime}"
    [[ "$runtime_base" = /* ]] || { echo "Runtime base must be an absolute Linux path" >&2; exit 2; }
    mkdir -p "$runtime_base" "$project_root/.runtime"
    fs="$(findmnt -n -o FSTYPE -T "$runtime_base")"
    [[ "$fs" != "9p" && "$fs" != "drvfs" ]] || { echo "Use a Linux-native runtime base" >&2; exit 2; }
    ln -s "$runtime_base/quantum-espresso-7.4" "$local_prefix"
fi
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$project_root"
"$uv" run --frozen simjecture install quantum-espresso --project-root "$project_root" --jobs 1
"$uv" run --frozen simjecture doctor --profile quantum-espresso --project-root "$project_root"
