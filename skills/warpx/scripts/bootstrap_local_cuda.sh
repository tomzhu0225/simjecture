#!/usr/bin/env bash
set -euo pipefail

# Reproduce the non-MPI 2D CUDA + openPMD WarpX runtime on a Linux/WSL host.
# The source tree is intentionally supplied by the caller: deployments must
# pin and audit the WarpX release rather than downloading an implicit branch.

usage() {
    echo "usage: $0 --source WARPX_SOURCE [--jobs N] [--arch N]" >&2
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
[[ -n "$source_tree" ]] || { usage; exit 2; }
source_tree="$(cd "$source_tree" && pwd)"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
cuda_root="$repo_root/.runtime/cuda-toolkit-12.4"
io_root="$repo_root/.runtime/warpx-cuda-openpmd-deps"
python_root="$repo_root/.runtime/warpx-cuda-openpmd"

for command in mamba python3.12 nvidia-smi; do
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

mamba create -y -p "$cuda_root" -c conda-forge \
    cuda-nvcc=12.4 cuda-cudart-dev=12.4 libcublas-dev=12.4 \
    libcurand-dev=10.3.5.147 libcusparse-dev=12.3.1.170 \
    cuda-profiler-api=12.4 cuda-nvtx-dev=12.4 \
    gcc_linux-64=12.4 gxx_linux-64=12.4
mamba create -y -p "$io_root" -c conda-forge \
    'hdf5=1.14.6=nompi_*' cmake ninja pkg-config

python3.12 -m venv --system-site-packages "$python_root"
"$python_root/bin/python" -m pip install --upgrade \
    pip setuptools wheel packaging picmistandard==0.34.0 \
    periodictable openpmd-api matplotlib numpy

# Keep Windows toolchains out of discovery under WSL. HDF5_ROOT and the
# non-MPI build prefix prevent a Windows/MPI HDF5 config from being selected.
export PATH="$cuda_root/bin:/usr/local/bin:/usr/bin:/bin:$io_root/bin"
export CUDA_PATH="$cuda_root"
export HDF5_ROOT="$io_root"
export CMAKE_PREFIX_PATH="$io_root"
export PKG_CONFIG_PATH="$io_root/lib/pkgconfig"
driver_path=""
[[ -d /usr/lib/wsl/lib ]] && driver_path="/usr/lib/wsl/lib:"
export LD_LIBRARY_PATH="${driver_path}$cuda_root/lib:$cuda_root/lib64:$io_root/lib"
export CPATH=/usr/include
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
    --require-openpmd
