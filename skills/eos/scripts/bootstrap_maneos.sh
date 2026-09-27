#!/usr/bin/env bash
set -euo pipefail

# Provision the pinned M-ANEOS 1.0 query runtime. Operator-side only.

PINNED_REVISION="58d75bc499a371c98de28d5bd7f772b43f97037f"
UPSTREAM="https://github.com/isale-code/M-ANEOS.git"

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
query_source="$project_root/skills/eos/scripts/maneos_query.f90"
[[ -f "$query_source" ]] || {
    echo "missing query driver $query_source" >&2
    exit 2
}

runtime_profile="m-aneos"
source "$project_root/scripts/runtime_environment.sh"
mkdir -p "$prefix/bin" "$prefix/share/preflight" "$prefix/src"

if [[ -n "$source_tree" ]]; then
    source_tree="$(cd "$source_tree" && pwd)"
    observed="$(git -C "$source_tree" rev-parse HEAD)"
    if [[ "$observed" != "$PINNED_REVISION" ]]; then
        echo "M-ANEOS source revision $observed does not match $PINNED_REVISION" >&2
        exit 2
    fi
    src="$source_tree"
else
    src="$prefix/src/m-aneos"
    git init "$src"
    git -C "$src" remote remove origin 2>/dev/null || true
    git -C "$src" remote add origin "$UPSTREAM"
    for attempt in 1 2 3; do
        if git -c http.version=HTTP/1.1 -C "$src" fetch --depth 1 origin "$PINNED_REVISION"; then
            break
        fi
        if [[ "$attempt" -eq 3 ]]; then
            echo "Could not fetch the pinned M-ANEOS source after three attempts" >&2
            exit 1
        fi
        echo "Source download interrupted; retrying…" >&2
        sleep "$attempt"
    done
    git -C "$src" checkout --detach FETCH_HEAD
fi

make -C "$src/src" -j "$jobs" FC="${FC:-gfortran}"
"${FC:-gfortran}" -O2 "$query_source" "$src/src/libaneos.a" -o "$prefix/bin/maneos-query"

if [[ -f "$src/example/ANEOS.INPUT" ]]; then
    cp "$src/example/ANEOS.INPUT" "$prefix/share/preflight/ANEOS.INPUT"
elif [[ -f "$src/input/quartz_.input" ]]; then
    cp "$src/input/quartz_.input" "$prefix/share/preflight/ANEOS.INPUT"
else
    echo "upstream M-ANEOS example input is missing" >&2
    exit 2
fi

"$prefix/bin/python" - "$PINNED_REVISION" "$jobs" >"$prefix/share/build-record.json" <<'PY'
import json, sys, sysconfig
print(json.dumps({
    "schema_version": "0.1.0",
    "package": "M-ANEOS",
    "version": "1.0",
    "revision": sys.argv[1],
    "installer": "simjecture",
    "jobs": int(sys.argv[2]),
    "preflight_input": "share/preflight/ANEOS.INPUT",
    "python": sys.executable,
    "python_version": sysconfig.get_python_version(),
    "python_layout": "self-contained" if sys.prefix == sys.base_prefix else "system-venv",
}, indent=2, sort_keys=True))
PY
echo "M-ANEOS runtime ready at $prefix"
