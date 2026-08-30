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

h5pfc=""
for candidate in h5pfc h5pfc.openmpi; do
    if command -v "$candidate" >/dev/null; then
        h5pfc="$(command -v "$candidate")"
        break
    fi
done
[[ -n "$h5pfc" ]] || {
    echo "missing deployment prerequisite: h5pfc (MPI Fortran HDF5 wrapper)" >&2
    exit 2
}

launcher=""
for candidate in mpirun orterun mpiexec; do
    if command -v "$candidate" >/dev/null; then
        launcher="$(command -v "$candidate")"
        break
    fi
done
[[ -n "$launcher" ]] || {
    echo "missing deployment prerequisite: mpirun, orterun, or mpiexec" >&2
    exit 2
}

mkdir -p "$prefix/bin" "$prefix/share/preflight" "$prefix/src"
"$python" -m venv "$prefix"
"$prefix/bin/python" -m pip install --upgrade pip setuptools wheel
"$prefix/bin/python" -m pip install 'numpy>=1.26,<3' 'h5py>=3.10,<4'

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
    git clone --filter=blob:none "$UPSTREAM" "$src"
    git -C "$src" checkout --detach "$PINNED_REVISION"
fi

make -C "$src/src" -j "$jobs" H5PFC=true FC="$h5pfc" HDF5=/usr LDFLAGS=
if [[ -x "$src/src/a.out" ]]; then
    cp "$src/src/a.out" "$prefix/bin/optab"
elif [[ -x "$src/src/optab" ]]; then
    cp "$src/src/optab" "$prefix/bin/optab"
else
    echo "Optab build did not produce an executable" >&2
    exit 2
fi
chmod +x "$prefix/bin/optab"

cat >"$prefix/bin/mpi-launcher" <<EOF
#!/bin/sh
exec $launcher "\$@"
EOF
chmod +x "$prefix/bin/mpi-launcher"

gaunt_dir="$src/database/1016620_Supplementary_Data"
if [[ -f "$gaunt_dir/get_gauntff.sh" ]]; then
    (cd "$gaunt_dir" && bash get_gauntff.sh)
fi
[[ -f "$gaunt_dir/gauntff.dat" ]] || {
    echo "failed to obtain van Hoof free-free Gaunt-factor data" >&2
    exit 2
}

nist_dir="$src/database/NIST"
if [[ -f "$nist_dir/get_nist_parallel.py" ]]; then
    (cd "$nist_dir" && "$prefix/bin/python" get_nist_parallel.py)
fi
if [[ ! -d "$src/database/h5" ]]; then
    mkdir -p "$src/database/h5"
fi
if [[ -f "$src/database/src/Makefile" ]]; then
    make -C "$src/database/src" convert_nist_h5 FC="$h5pfc" LDFLAGS= || true
fi
if [[ ! -f "$src/database/h5/NIST.h5" ]]; then
    if [[ -x "$src/database/src/convert_nist_h5" ]]; then
        (cd "$src/database/src" && ./convert_nist_h5)
    elif [[ -x "$src/database/src/a.out" ]]; then
        (cd "$src/database/src" && ./a.out)
    fi
fi
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
