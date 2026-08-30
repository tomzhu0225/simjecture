#!/usr/bin/env bash
set -euo pipefail

# Provision the pinned Singularity-EOS 1.12.1 query runtime. Operator-side only.

PINNED_REVISION="760ac3f8e106addc13dad8a47b9d4ad75e44ea48"
UPSTREAM="https://github.com/lanl/singularity-eos.git"

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
project_root="$(cd "$project_root" && pwd)"
query_source="$project_root/skills/eos/scripts/singularity_query.cpp"
[[ -f "$query_source" ]] || {
    echo "missing query driver $query_source" >&2
    exit 2
}

if [[ -e "$prefix" ]]; then
    if [[ "$repair" -ne 1 ]]; then
        echo "runtime already exists at $prefix; pass --repair to replace it" >&2
        exit 2
    fi
    rm -rf "$prefix"
fi

python=""
for candidate in python3.12 python3; do
    if command -v "$candidate" >/dev/null; then
        python="$(command -v "$candidate")"
        break
    fi
done
[[ -n "$python" ]] || {
    echo "missing deployment prerequisite: python3.12 or python3" >&2
    exit 2
}
command -v git >/dev/null || {
    echo "missing deployment prerequisite: git" >&2
    exit 2
}
command -v g++ >/dev/null || {
    echo "missing deployment prerequisite: g++" >&2
    exit 2
}

mkdir -p "$prefix/bin" "$prefix/share" "$prefix/src"
"$python" -m venv "$prefix"

if [[ -n "$source_tree" ]]; then
    source_tree="$(cd "$source_tree" && pwd)"
    observed="$(git -C "$source_tree" rev-parse HEAD)"
    if [[ "$observed" != "$PINNED_REVISION" ]]; then
        echo "Singularity-EOS source revision $observed does not match $PINNED_REVISION" >&2
        exit 2
    fi
    src="$source_tree"
else
    src="$prefix/src/singularity-eos"
    git clone --filter=blob:none "$UPSTREAM" "$src"
    git -C "$src" checkout --detach "$PINNED_REVISION"
fi

g++ -std=c++20 -O2 -pthread \
    -I "$src" \
    -I "$src/utils/ports-of-call" \
    -I "$src/singularity-utils" \
    "$query_source" \
    -o "$prefix/bin/eos-query"

"$prefix/bin/python" - "$PINNED_REVISION" "$jobs" >"$prefix/share/build-record.json" <<'PY'
import json, sys, sysconfig
print(json.dumps({
    "schema_version": "0.1.0",
    "package": "singularity-eos",
    "version": "1.12.1",
    "revision": sys.argv[1],
    "installer": "simjecture",
    "jobs": int(sys.argv[2]),
    "models": ["IdealGas", "IdealElectrons"],
    "python": sys.executable,
    "python_version": sysconfig.get_python_version(),
}, indent=2, sort_keys=True))
PY
echo "Singularity-EOS runtime ready at $prefix"
