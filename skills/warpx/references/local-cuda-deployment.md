# Deploy the local CUDA instrument

Use this procedure to reproduce the WarpX 26.07 non-MPI, 2D CUDA instrument
with HDF5 openPMD diagnostics on a Linux or WSL machine.

## Preconditions

- The bootstrap obtains pinned WarpX 26.07 source at commit
  `312d507407a1bf6f01ae43fb41b5c3a3700d053c` automatically. An optional
  `--source` checkout must match that revision.
- Install an NVIDIA driver visible to Linux or WSL, `nvidia-smi`, and Simjecture itself. The bootstrap installs its own
  compiler, CUDA toolkit, Python headers and I/O dependencies using the verified
  Micromamba downloader; no system mamba, compiler or root access is required.
- On WSL, confirm `/dev/dxg` and `/usr/lib/wsl/lib/libcuda.so` exist.
- Budget roughly 15 GB of RAM, several GB of disk, network access for source
  dependencies, and tens of minutes for compilation. Shared or older CPUs can
  take longer; follow the live command log rather than assuming a fixed deadline.

For an agent-assisted install, launch the command below with `run_command`
and poll `simulation_status` until completion. Do not run `nohup` or `&` inside
`terminal`: its descendant processes are cleaned up when that terminal command
ends. Share public progress during downloads and compilation.

Run the bootstrap from the repository root:

```bash
skills/warpx/scripts/bootstrap_local_cuda.sh --jobs 8
```

The script detects the GPU compute capability unless `--arch` is supplied. It
creates project-local environments under `.runtime/`, builds only the 2D CUDA
Python binding, installs openPMD/HDF5 support, and runs a post-install probe.
The runtime includes CuPy for Python-side GPU field/particle callbacks. Launchers
and capability descriptors disable user-site Python packages so a host-only install
cannot hide missing runtime dependencies. The WSL NVIDIA utility directory remains
available after build-toolchain isolation. It does not change the source revision. Dependency environments resume after
interrupted downloads and share a package cache with other installers.

The bootstrap writes a host-specific descriptor in
`.runtime/warpx-cuda-openpmd/capabilities/`, selecting native NVIDIA device files
or the WSL GPU/driver mount as appropriate. Register that directory, then run
the catalogue readiness check. The versioned descriptor remains a template.
Do not stop after compilation or a host-only import test.

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
- The bootstrap uses its managed Python headers instead of relying on Ubuntu
  development packages. Keep the conda compiler sysroot separate from system headers.
- Compile for the actual device architecture. This host's RTX 4000 Ada is
  compute capability 8.9, expressed to CMake as `89`.

## Validate after deployment

Run the reusable launcher and require both CUDA and openPMD HDF5:

```bash
skills/warpx/scripts/run_local_cuda.sh \
  skills/warpx/scripts/probe_local_cuda.py --require-openpmd
```

The probe must report `cuda_warpx`, `cupy_device_kernel`, `openpmd_hdf5_reader`, and
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

## Complete the browser handoff

After registering the descriptor, call `research_tools(action="check", name=ID)`
with the returned catalogue ID, then `research_tools(action="list")` until that
check completes. Verify the actual selected descriptor under the configured
execution backend. A manual host-shell run or relocated copy is insufficient.
If readiness is failed, inspect the reported error, repair and rerun this check.
Do not call it a stale UI error or report success while the card is failed.
Generic CLI profiles can refer to a different pinned capability; check the
actual custom installation through its own registered catalogue ID.
