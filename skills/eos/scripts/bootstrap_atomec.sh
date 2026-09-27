#!/usr/bin/env bash
set -euo pipefail

# Provision the pinned atoMEC 1.4.0 runtime. Operator-side only.

PINNED_REVISION="4b05849a1bcf6a9d682673c360ec2ebfb4eceab3"
UPSTREAM="https://github.com/atomec-project/atoMEC.git"

usage() {
    echo "usage: $0 --prefix DIR --project-root DIR [--jobs N] [--source DIR] [--repair]" >&2
}

prefix=""
project_root=""
jobs=8
source_tree=""
repair=0
while (($#)); do
    case "$1" in
        --prefix) prefix="$2"; shift 2 ;;
        --project-root) project_root="$2"; shift 2 ;;
        --jobs) jobs="$2"; shift 2 ;;
        --source) source_tree="$2"; shift 2 ;;
        --repair) repair=1; shift ;;
        *) usage; exit 2 ;;
    esac
done
[[ -n "$prefix" && -n "$project_root" ]] || { usage; exit 2; }
prefix="$(mkdir -p "$(dirname "$prefix")" && cd "$(dirname "$prefix")" && pwd)/$(basename "$prefix")"

runtime_profile="atomec"
source "$project_root/scripts/runtime_environment.sh"
mkdir -p "$prefix/bin" "$prefix/share/preflight" "$prefix/src"

if [[ -n "$source_tree" ]]; then
    source_tree="$(cd "$source_tree" && pwd)"
    observed="$(git -C "$source_tree" rev-parse HEAD)"
    if [[ "$observed" != "$PINNED_REVISION" ]]; then
        echo "atoMEC source revision $observed does not match $PINNED_REVISION" >&2
        exit 2
    fi
    "$prefix/bin/python" -m pip install "mendeleev==0.9.0" "numpy<2" "scipy<1.12" "pandas<2" "$source_tree"
else
    "$prefix/bin/python" -m pip install "mendeleev==0.9.0" "numpy<2" "scipy<1.12" "pandas<2" \
        "git+${UPSTREAM}@${PINNED_REVISION}"
fi

mkdir -p "$prefix/share"
"$prefix/bin/python" - "$PINNED_REVISION" "$jobs" >"$prefix/share/build-record.json" <<'PY'
import json, sys, sysconfig
from pathlib import Path
print(json.dumps({
    "schema_version": "0.1.0",
    "package": "atoMEC",
    "version": "1.4.0",
    "revision": sys.argv[1],
    "installer": "simjecture",
    "jobs": int(sys.argv[2]),
    "python": sys.executable,
    "python_version": sysconfig.get_python_version(),
}, indent=2, sort_keys=True))
PY
echo "atoMEC runtime ready at $prefix"
