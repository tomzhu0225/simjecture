#!/usr/bin/env bash
set -euo pipefail

PINNED_REVISION="6196889ac611f909dd99366fe447486411e27950"
UPSTREAM="https://github.com/flexible-atomic-code/fac.git"
prefix=""
project_root=""
source_tree=""
jobs=8
while (($#)); do
    case "$1" in
        --prefix) prefix="$2"; shift 2 ;;
        --project-root) project_root="$2"; shift 2 ;;
        --source) source_tree="$2"; shift 2 ;;
        --jobs) jobs="$2"; shift 2 ;;
        --repair) shift ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done
[[ -n "$prefix" && -n "$project_root" && "$jobs" =~ ^[1-9][0-9]*$ ]] || {
    echo "usage: $0 --prefix DIR --project-root DIR [--source DIR] [--jobs N] [--repair]" >&2
    exit 2
}
project_root="$(cd "$project_root" && pwd)"
if [[ -n "$source_tree" ]]; then
    source_tree="$(cd "$source_tree" && pwd)"
    [[ "$(git -C "$source_tree" rev-parse HEAD)" == "$PINNED_REVISION" ]] || {
        echo "FAC source does not match pinned revision" >&2; exit 2
    }
fi

runtime_profile="fac"
source "$project_root/scripts/runtime_environment.sh"
mkdir -p "$prefix/src" "$prefix/share"
src="$prefix/src/fac"
git init "$src"
git -C "$src" remote remove origin 2>/dev/null || true
git -C "$src" remote add origin "${source_tree:-$UPSTREAM}"
for attempt in 1 2 3; do
    if git -c http.version=HTTP/1.1 -C "$src" fetch --depth 1 origin "$PINNED_REVISION"; then
        break
    fi
    [[ "$attempt" -lt 3 ]] || exit 1
    sleep "$attempt"
done
git -C "$src" checkout --detach FETCH_HEAD
# Build in the managed copy, leaving a supplied source/audit tree untouched.
if [[ -f "$src/Makefile" ]]; then
    make -C "$src" clean
fi
(
    cd "$src"
    ./configure --prefix="$prefix" --with-mpi=omp \
        CC="${CC:-gcc}" F77="${FC:-gfortran}" PYTHON="$prefix/bin/python"
    make -j "$jobs"
    make install
)
for program in sfac scrm spol; do
    [[ -x "$prefix/bin/$program" ]] || { echo "missing FAC program $program" >&2; exit 1; }
done
cp "$project_root/skills/atomic-physics/scripts/fac_lte.py" "$prefix/share/fac_lte.py"
"$prefix/bin/python" - "$prefix" "$PINNED_REVISION" "$jobs" <<'PY'
import hashlib
import json
import pathlib
import platform
import sys

root = pathlib.Path(sys.argv[1])
record = {
    "schema_version": "0.1.0", "package": "FAC", "version": "1.1.5",
    "revision": sys.argv[2], "installer": "simjecture", "jobs": int(sys.argv[3]),
    "interfaces": ["sfac", "scrm", "spol"], "python_version": platform.python_version(),
    "executables": {name: hashlib.sha256((root / "bin" / name).read_bytes()).hexdigest()
                    for name in ("sfac", "scrm", "spol")},
    "lte_helper_sha256": hashlib.sha256((root / "share/fac_lte.py").read_bytes()).hexdigest(),
}
(root / "share/build-record.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
PY
echo "FAC command-line runtime ready at $prefix"
