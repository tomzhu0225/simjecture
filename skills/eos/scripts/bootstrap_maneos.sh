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
for command in git gfortran make; do
    command -v "$command" >/dev/null || {
        echo "missing deployment prerequisite: $command" >&2
        exit 2
    }
done

mkdir -p "$prefix/bin" "$prefix/share/preflight" "$prefix/src"
"$python" - "$prefix" <<'PY'
import shutil, sys, venv
from pathlib import Path

prefix = Path(sys.argv[1])
base = Path(sys.base_prefix).resolve()
if base.parent.name == "python" and base.parent.parent.name == "uv":
    # uv's standalone distribution is relocatable. A venv symlink to the
    # user's uv directory would be broken inside the capability mount.
    shutil.copytree(base, prefix, dirs_exist_ok=True, symlinks=True)
    launcher = prefix / "bin" / "python"
    launcher.unlink(missing_ok=True)
    launcher.symlink_to(f"python{sys.version_info.major}.{sys.version_info.minor}")
else:
    # System Python's standard library is available through the /usr mount.
    # This query runtime needs only the standard library, not pip.
    venv.EnvBuilder(with_pip=False, symlinks=False).create(prefix)
PY

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

make -C "$src/src" -j "$jobs"
gfortran -O2 "$query_source" "$src/src/libaneos.a" -o "$prefix/bin/maneos-query"

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
