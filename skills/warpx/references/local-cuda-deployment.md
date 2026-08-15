# Deploy the local CUDA instrument

Use this procedure to reproduce the WarpX 26.07 non-MPI, 2D CUDA instrument
with HDF5 openPMD diagnostics on a Linux or WSL machine.

## Preconditions

- Pin an audited WarpX source checkout. The tested release is 26.07 at commit
  `312d507407a1bf6f01ae43fb41b5c3a3700d053c`.
- Install an NVIDIA driver visible to Linux or WSL, `nvidia-smi`, Miniforge or
  Mambaforge, `mamba`, Python 3.12 development headers, Git, and build tools.
- On WSL, confirm `/dev/dxg` and `/usr/lib/wsl/lib/libcuda.so` exist.
- Budget roughly 15 GB of RAM, several GB of disk, network access for source
  dependencies, and 10--30 minutes for compilation.

Run the bootstrap from the repository root:

```bash
skills/warpx/scripts/bootstrap_local_cuda.sh \
  --source /absolute/path/to/pinned/warpx-26.07 --jobs 8
```

The script detects the GPU compute capability unless `--arch` is supplied. It
creates project-local environments under `.runtime/`, builds only the 2D CUDA
Python binding, installs openPMD/HDF5 support, and runs a post-install probe.
It does not mutate the supplied WarpX source.

## Why the bootstrap is strict

- WarpX 26.07 rejects CUDA 12.0; use CUDA 12.2 or newer. The pinned toolkit is
  CUDA 12.4.
- A minimal `cuda-nvcc` package is insufficient. AMReX/WarpX also requires the
  development packages for CUDA runtime, cuBLAS, cuRAND, cuSPARSE, profiler
  API, and NVTX.
- On WSL, put `/usr/lib/wsl/lib` before Ubuntu CUDA stubs in
  `LD_LIBRARY_PATH`; otherwise a CUDA allocation can report no device even
  when `nvidia-smi` succeeds.
- Restrict the build `PATH` and set `HDF5_ROOT`/`CMAKE_PREFIX_PATH` to the
  project-local non-MPI Linux HDF5 prefix. A Windows Miniconda
  `hdf5-config.cmake` can otherwise be discovered through WSL and incorrectly
  require MPI.
- Set `CPATH=/usr/include` during compilation. With the conda host compiler,
  `nvcc` otherwise fails to resolve Ubuntu's multiarch Python `pyconfig.h`.
- Compile for the actual device architecture. This host's RTX 4000 Ada is
  compute capability 8.9, expressed to CMake as `89`.

## Validate after deployment

Run the reusable launcher and require both CUDA and openPMD HDF5:

```bash
skills/warpx/scripts/run_local_cuda.sh \
  skills/warpx/scripts/probe_local_cuda.py --require-openpmd
```

The probe must report `cuda_warpx`, `openpmd_hdf5_reader`, and
`openpmd_hdf5_roundtrip` as true. This proves GPU-aware AMReX was loaded and
that openPMD can create and read an HDF5 series. It does not replace the WarpX
field-diagnostic smoke test, which proves the producer path.

Then execute `examples/openpmd_field_smoke.py` in a fresh directory and verify
every boolean in `openpmd_capability_smoke.json`. Finally run a representative
scientific program and inspect both its realized input and openPMD records.

Set `WARPX_CUDA_RUNTIME` to select an alternate installed runtime while keeping
the same launcher:

```bash
WARPX_CUDA_RUNTIME=/absolute/path/to/runtime \
  skills/warpx/scripts/run_local_cuda.sh program.py
```

## Failure signatures

| Failure | Meaning and remedy |
|---|---|
| WarpX/AMReX requires CUDA 12.2+ | System `nvcc` is too old; use the pinned project-local toolkit. |
| `cudaErrorNoDevice` while `nvidia-smi` works | Wrong `libcuda` was loaded; put the WSL driver directory first. |
| Missing `CUDA::curand` or `CUDA::cusparse` | Install their development packages, not runtime libraries alone. |
| Missing `cuda_profiler_api.h` | Install `cuda-profiler-api`. |
| Missing `nvToolsExt.h` | Install `cuda-nvtx-dev`. |
| HDF5 config under `/mnt/c/...` requests MPI | Windows CMake contamination; restrict `PATH` and point HDF5 discovery to the Linux non-MPI prefix. |
| Missing `x86_64-linux-gnu/python*/pyconfig.h` | Add `/usr/include` to `CPATH`; do not add only the multiarch leaf because that mixes libc sysroots. |
| C++20 filesystem test fails after adding the multiarch leaf | Remove that leaf from `CPATH` and use `/usr/include`. |

Preserve the build log and package lists with deployment artifacts. Re-run the
probe after driver, CUDA, Python, WarpX, HDF5, or openPMD changes.
