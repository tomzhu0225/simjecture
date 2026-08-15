#!/usr/bin/env bash
set -euo pipefail

# Launch the project-local WarpX CUDA runtime under WSL. The WSL driver stub
# must precede Ubuntu's libcuda, and the source-built wheel bundles pyAMReX in
# a nested site-packages directory.
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
cuda_root="$repo_root/.runtime/cuda-toolkit-12.4"
io_root="$repo_root/.runtime/warpx-cuda-openpmd-deps"
python_root="${WARPX_CUDA_RUNTIME:-$repo_root/.runtime/warpx-cuda-openpmd}"
if [[ ! -x "$python_root/bin/python" && -z "${WARPX_CUDA_RUNTIME:-}" ]]; then
    python_root="$repo_root/.runtime/warpx-cuda"
fi
if [[ ! -x "$python_root/bin/python" ]]; then
    echo "missing WarpX CUDA Python runtime: $python_root" >&2
    exit 2
fi
python_site="$($python_root/bin/python -c \
    "import sysconfig; print(sysconfig.get_paths()['purelib'])")"
bundled_site="$python_site/pywarpx/site-packages"
if [[ ! -x "$cuda_root/bin/nvcc" ]]; then
    echo "missing CUDA 12.4 toolkit: $cuda_root" >&2
    exit 2
fi

export CUDA_PATH="$cuda_root"
driver_path=""
[[ -d /usr/lib/wsl/lib ]] && driver_path="/usr/lib/wsl/lib:"
io_path=""
[[ -d "$io_root/lib" ]] && io_path="$io_root/lib:"
export LD_LIBRARY_PATH="${driver_path}$cuda_root/lib:$cuda_root/lib64:${io_path}$python_site/pywarpx${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONPATH="$bundled_site:$python_site${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

exec "$python_root/bin/python" "$@"
