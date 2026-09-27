#!/usr/bin/env bash
set -euo pipefail

# Provision the pinned Optab 1.3.1 runtime. Operator-side only.

PINNED_REVISION="2d95b7c1a944e15d80605afee783c22eed441ae1"
UPSTREAM="https://github.com/nombac/optab.git"

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
preflight_writer="$project_root/skills/opacity/scripts/write_optab_preflight.py"
[[ -f "$preflight_writer" ]] || {
    echo "missing preflight writer $preflight_writer" >&2
    exit 2
}

runtime_profile="optab"
source "$project_root/scripts/runtime_environment.sh"
mkdir -p "$prefix/bin" "$prefix/share/preflight" "$prefix/src"
h5pfc="$prefix/bin/h5pfc"
launcher="$prefix/bin/mpirun"

if [[ -n "$source_tree" ]]; then
    source_tree="$(cd "$source_tree" && pwd)"
    observed="$(git -C "$source_tree" rev-parse HEAD)"
    if [[ "$observed" != "$PINNED_REVISION" ]]; then
        echo "Optab source revision $observed does not match $PINNED_REVISION" >&2
        exit 2
    fi
    src="$source_tree"
else
    src="$prefix/src/optab"
    git init "$src"
    git -C "$src" remote remove origin 2>/dev/null || true
    git -C "$src" remote add origin "$UPSTREAM"
    for attempt in 1 2 3; do
        if git -c http.version=HTTP/1.1 -C "$src" fetch --depth 1 origin "$PINNED_REVISION"; then
            break
        fi
        if [[ "$attempt" -eq 3 ]]; then
            echo "Could not fetch the pinned Optab source after three attempts" >&2
            exit 1
        fi
        echo "Source download interrupted; retrying…" >&2
        sleep "$attempt"
    done
    git -C "$src" checkout --detach FETCH_HEAD
fi

make -C "$src/src" -j "$jobs" H5PFC=true FC="$h5pfc" HDF5="$prefix" LDFLAGS=
if [[ -x "$src/src/a.out" ]]; then
    cp "$src/src/a.out" "$prefix/bin/optab"
elif [[ -x "$src/src/optab" ]]; then
    cp "$src/src/optab" "$prefix/bin/optab"
else
    echo "Optab build did not produce an executable" >&2
    exit 2
fi
chmod +x "$prefix/bin/optab"

cat >"$prefix/bin/mpi-launcher" <<'EOF'
#!/bin/sh
HERE="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
export OPAL_PREFIX="$HERE/.."
export LD_LIBRARY_PATH="$HERE/../lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$HERE/mpirun" "$@"
EOF
chmod +x "$prefix/bin/mpi-launcher"

gaunt_dir="$src/database/1016620_Supplementary_Data"
if [[ ! -s "$gaunt_dir/gauntff.dat" && -f "$gaunt_dir/get_gauntff.sh" ]]; then
    (cd "$gaunt_dir" && bash get_gauntff.sh)
fi
[[ -f "$gaunt_dir/gauntff.dat" ]] || {
    echo "failed to obtain van Hoof free-free Gaunt-factor data" >&2
    exit 2
}

nist_dir="$src/database/NIST"
mkdir -p "$src/database/h5"
make -C "$src/database/src" convert_nist_h5 FC="$h5pfc" HDF5="$prefix" LDFLAGS=
"$prefix/bin/python" "$project_root/skills/opacity/scripts/fetch_optab_data.py" "$src"

[[ -f "$src/database/h5/NIST.h5" ]] || {
    echo "failed to build input/h5/NIST.h5; install HDF5 Fortran tools and rerun" >&2
    exit 2
}

"$prefix/bin/python" "$preflight_writer" --output "$prefix/share/preflight"
cp "$gaunt_dir/gauntff.dat" \
    "$prefix/share/preflight/1016620_Supplementary_Data/gauntff.dat"
cp "$src/database/h5/NIST.h5" "$prefix/share/preflight/h5/NIST.h5"

species_id=""
for candidate in \
    "$src/sample/sample/input/species_id.dat" \
    "$src/sample/input/species_id.dat"
do
    if [[ -f "$candidate" ]]; then
        species_id="$candidate"
        break
    fi
done
[[ -n "$species_id" ]] || {
    echo "upstream Optab species_id.dat is missing" >&2
    exit 2
}
cp "$species_id" "$prefix/share/preflight/species_id.dat"

"$prefix/bin/python" - "$PINNED_REVISION" "$jobs" "$launcher" \
    >"$prefix/share/build-record.json" <<'PY'
import json, sys, sysconfig
print(json.dumps({
    "schema_version": "0.1.0",
    "package": "optab",
    "version": "1.3.1",
    "revision": sys.argv[1],
    "installer": "simjecture",
    "jobs": int(sys.argv[2]),
    "mpi_launcher": sys.argv[3],
    "python": sys.executable,
    "python_version": sysconfig.get_python_version(),
}, indent=2, sort_keys=True))
PY
echo "Optab runtime ready at $prefix"
