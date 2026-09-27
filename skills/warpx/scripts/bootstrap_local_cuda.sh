#!/usr/bin/env bash
set -euo pipefail

# Reproduce the non-MPI 2D CUDA + openPMD WarpX runtime on a Linux/WSL host.
# The source tree is intentionally supplied by the caller: deployments must
# pin and audit the WarpX release rather than downloading an implicit branch.

usage() {
    echo "usage: $0 [--source WARPX_SOURCE] [--jobs N] [--arch N]" >&2
}

source_tree=""
jobs=8
cuda_arch=""
while (($#)); do
    case "$1" in
        --source) source_tree="$2"; shift 2 ;;
        --jobs) jobs="$2"; shift 2 ;;
        --arch) cuda_arch="$2"; shift 2 ;;
        *) usage; exit 2 ;;
    esac
done
if [[ -n "$source_tree" ]]; then
    source_tree="$(cd "$source_tree" && pwd)"
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
cuda_root="$repo_root/.runtime/cuda-toolkit-12.4"
io_root="$repo_root/.runtime/warpx-cuda-openpmd-deps"
python_root="$repo_root/.runtime/warpx-cuda-openpmd"

for command in python3 nvidia-smi; do
    command -v "$command" >/dev/null || {
        echo "missing deployment prerequisite: $command" >&2
        exit 2
    }
done
if [[ ! -e /dev/dxg && ! -e /dev/nvidia0 ]]; then
    echo "no WSL or native NVIDIA device node found" >&2
    exit 2
fi
if [[ -z "$cuda_arch" ]]; then
    cuda_arch="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d '.')"
fi

bootstrap_python="${SIMJECTURE_BOOTSTRAP_PYTHON:-python3}"
for spec in "cuda-toolkit:$cuda_root" "cuda-io:$io_root" "cuda-python:$python_root"; do
    "$bootstrap_python" "$repo_root/scripts/prepare_runtime.py" "${spec%%:*}" "${spec#*:}"
done

pinned_revision="312d507407a1bf6f01ae43fb41b5c3a3700d053c"
if [[ -z "$source_tree" ]]; then
    source_tree="$repo_root/.runtime/src-cache/warpx-26.07"
    git="$python_root/bin/git"
    "$git" init "$source_tree"
    "$git" -C "$source_tree" remote remove origin 2>/dev/null || true
    "$git" -C "$source_tree" remote add origin https://github.com/BLAST-WarpX/warpx.git
    for attempt in 1 2 3; do
        if "$git" -c http.version=HTTP/1.1 -C "$source_tree" fetch --depth 1 origin "$pinned_revision"; then
            break
        fi
        [[ "$attempt" -lt 3 ]] || exit 1
        sleep "$attempt"
    done
    "$git" -C "$source_tree" checkout --detach FETCH_HEAD
fi
observed="$("$python_root/bin/git" -C "$source_tree" rev-parse HEAD)"
[[ "$observed" == "$pinned_revision" ]] || {
    echo "WarpX source revision $observed does not match $pinned_revision" >&2
    exit 2
}

# Keep Windows toolchains out of discovery under WSL. HDF5_ROOT and the
# non-MPI build prefix prevent a Windows/MPI HDF5 config from being selected.
export PATH="$cuda_root/bin:$io_root/bin:$python_root/bin:/usr/local/bin:/usr/bin:/bin"
export CUDA_PATH="$cuda_root"
export HDF5_ROOT="$io_root"
export CMAKE_PREFIX_PATH="$io_root"
export PKG_CONFIG_PATH="$io_root/lib/pkgconfig"
driver_path=""
[[ -d /usr/lib/wsl/lib ]] && driver_path="/usr/lib/wsl/lib:"
export LD_LIBRARY_PATH="${driver_path}$cuda_root/lib:$cuda_root/lib64:$io_root/lib"
export CPATH="$python_root/include/python3.12"
export CC="$cuda_root/bin/x86_64-conda-linux-gnu-cc"
export CXX="$cuda_root/bin/x86_64-conda-linux-gnu-c++"
export CUDAHOSTCXX="$CXX"
export CUDACXX="$cuda_root/bin/nvcc"
export CMAKE_CUDA_ARCHITECTURES="$cuda_arch"
export WARPX_COMPUTE=CUDA WARPX_MPI=OFF WARPX_DIMS=2 WARPX_EB=OFF
export WARPX_OPENPMD=ON WARPX_OPENPMD_INTERNAL=ON
export WARPX_FFT=OFF WARPX_QED=OFF WARPX_QED_TABLE_GEN=OFF
export WARPX_PYTHON_IPO=OFF BUILD_PARALLEL="$jobs"

"$python_root/bin/python" -m pip install --no-build-isolation -v "$source_tree"
"$script_dir/run_local_cuda.sh" "$script_dir/probe_local_cuda.py" \
    --require-openpmd --workdir "$python_root/share/preflight"

"$python_root/bin/python" - "$source_tree" "$cuda_arch" > "$python_root/share/build-record.json" <<'PYRECORD'
import json, subprocess, sys
print(json.dumps({
    "package": "WarpX", "version": "26.07", "dimensions": "2", "compute": "CUDA",
    "revision": subprocess.check_output(["git", "-C", sys.argv[1], "rev-parse", "HEAD"], text=True).strip(),
    "cuda_architecture": sys.argv[2], "openpmd_probe_passed": True,
}, indent=2))
PYRECORD

"$bootstrap_python" "$repo_root/scripts/register_cuda_runtime.py" "$repo_root"
