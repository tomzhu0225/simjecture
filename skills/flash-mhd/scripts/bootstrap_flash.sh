#!/usr/bin/env bash
set -euo pipefail

# Operator-side FLASH builder. Clones only a Git remote the operator supplied.
# This script never contains a default FLASH URL.

usage() {
    echo "usage: $0 --prefix DIR --project-root DIR [--source DIR] [--git-url URL] [--git-ref REF] [--jobs N] [--repair]" >&2
}

prefix=""
project_root=""
source_tree=""
git_url="${FLASH_GIT_URL:-}"
git_ref="${FLASH_GIT_REF:-}"
jobs=8
repair=0
while (($#)); do
    case "$1" in
        --prefix) prefix="$2"; shift 2 ;;
        --project-root) project_root="$2"; shift 2 ;;
        --source) source_tree="$2"; shift 2 ;;
        --git-url) git_url="$2"; shift 2 ;;
        --git-ref) git_ref="$2"; shift 2 ;;
        --jobs) jobs="$2"; shift 2 ;;
        --repair) repair=1; shift ;;
        *) usage; exit 2 ;;
    esac
done
[[ -n "$prefix" && -n "$project_root" ]] || { usage; exit 2; }
project_root="$(cd "$project_root" && pwd)"

: "${FLASH_SETUP_ARGS:?set FLASH_SETUP_ARGS to the arguments passed to ./setup}"
: "${FLASH_OBJDIR:?set FLASH_OBJDIR to the FLASH object directory name}"
FLASH_PREFLIGHT_PARFILE="${FLASH_PREFLIGHT_PARFILE:-}"

if [[ -z "$source_tree" ]]; then
    if [[ -z "$git_url" ]]; then
        echo "pass --source DIR, --git-url URL, or set FLASH_GIT_URL" >&2
        exit 2
    fi
    command -v git >/dev/null || {
        echo "missing git; required to clone the operator FLASH remote" >&2
        exit 2
    }
    cache="$project_root/.runtime/src-cache/flash"
    mkdir -p "$(dirname "$cache")"
    if [[ ! -d "$cache/.git" ]]; then
        git clone --filter=blob:none "$git_url" "$cache"
    else
        git -C "$cache" remote set-url origin "$git_url"
        git -C "$cache" fetch --tags origin
    fi
    if [[ -n "$git_ref" ]]; then
        git -C "$cache" checkout --detach "$git_ref"
    fi
    source_tree="$cache"
fi

source_tree="$(cd "$source_tree" && pwd)"
[[ -x "$source_tree/setup" || -f "$source_tree/setup" ]] || {
    echo "FLASH setup script is missing in $source_tree" >&2
    exit 2
}
if [[ -z "$FLASH_PREFLIGHT_PARFILE" ]]; then
    echo "set FLASH_PREFLIGHT_PARFILE to an operator-owned parameter file" >&2
    exit 2
fi
[[ -f "$FLASH_PREFLIGHT_PARFILE" ]] || {
    echo "preflight parameter file is missing: $FLASH_PREFLIGHT_PARFILE" >&2
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
    echo "missing python3.12 or python3" >&2
    exit 2
}

mkdir -p "$prefix/bin" "$prefix/share/preflight"
"$python" -m venv "$prefix"
"$prefix/bin/python" -m pip install --upgrade pip setuptools wheel
"$prefix/bin/python" -m pip install 'numpy>=1.26,<3' 'h5py>=3.10,<4'

(
    cd "$source_tree"
    # Word splitting of FLASH_SETUP_ARGS is intentional.
    # shellcheck disable=SC2086
    ./setup $FLASH_SETUP_ARGS
    make -C "$FLASH_OBJDIR" -j "$jobs"
)

flash4=""
for candidate in \
    "$source_tree/$FLASH_OBJDIR/flash4" \
    "$source_tree/object/flash4"
do
    if [[ -f "$candidate" ]]; then
        flash4="$candidate"
        break
    fi
done
[[ -n "$flash4" ]] || {
    echo "FLASH build did not produce flash4" >&2
    exit 2
}
cp "$flash4" "$prefix/bin/flash4"
chmod +x "$prefix/bin/flash4"
cp "$FLASH_PREFLIGHT_PARFILE" "$prefix/share/preflight/flash.par"

cat >"$prefix/bin/flash-python" <<'EOF'
#!/bin/sh
HERE="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
exec "$HERE/python" "$@"
EOF
chmod +x "$prefix/bin/flash-python"

"$prefix/bin/python" - "$source_tree" "$FLASH_OBJDIR" "$jobs" \
    >"$prefix/share/build-record.json" <<'PY'
import json, sys, sysconfig
print(json.dumps({
    "schema_version": "0.1.0",
    "package": "FLASH",
    "installer": "simjecture",
    "source": sys.argv[1],
    "object_directory": sys.argv[2],
    "jobs": int(sys.argv[3]),
    "python": sys.executable,
    "python_version": sysconfig.get_python_version(),
    "notes": [
        "Operator-supplied FLASH build; not redistributable with Simjecture."
    ],
}, indent=2, sort_keys=True))
PY
echo "FLASH runtime ready at $prefix"
