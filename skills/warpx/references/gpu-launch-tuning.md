# Local CUDA launch and tuning

Use this resource only to deploy and tune an already authored program. It must
not supply physical parameters, expected outcomes, acceptance thresholds, or a
benchmark problem.

## Prove the whole stack

The repository has a local, non-MPI, 2D CUDA WarpX 26.07 runtime with HDF5
openPMD diagnostics for the WSL host's NVIDIA RTX 4000 Ada Generation. Inside
the autonomous sandbox, invoke it through the
`warpx-cuda-openpmd-26.07` capability.

Do not infer GPU execution from `nvidia-smi` alone. Verify all three layers:

1. `nvidia-smi` reports a device and usable driver.
2. A real CUDA allocation and kernel complete.
3. The loaded AMReX binding reports `have_gpu=true` and `gpu_backend=CUDA`.

On this WSL host, `/usr/lib/wsl/lib` must be first in `LD_LIBRARY_PATH`.
Otherwise an incompatible `libcuda` can be selected even though `nvidia-smi`
works.

Set `warpx_amrex_the_arena_init_size` explicitly on every GPU
`picmi.Simulation`. A 256 MiB initial arena is a safe commissioning allocation
for this host; it is an allocator setting, not a scientific memory cap. Measure
peak use and retain headroom before increasing the workload.

The reusable host launcher repairs the source-built wheel's nested Python path:

```bash
skills/warpx/scripts/run_local_cuda.sh -c \
  "import amrex.space2d as a; print(a.Config.have_gpu, a.Config.gpu_backend)"
```

Expected output is `True CUDA`. See `local-cuda-deployment.md` to install or
repair the runtime and `examples/openpmd_field_smoke.py` to verify the producer
and reader path. These checks establish instrument availability only.

## Benchmark contract

GPU performance depends strongly on the exact program and decomposition. Build
a campaign-local JSON file whose cases contain complete candidate-program
argument lists. Change only the launch parameter being tuned; keep all
scientific inputs and diagnostics fixed.

```json
{
  "cases": [
    {"label": "case-a", "argv": ["--max-grid-size", "64"]},
    {"label": "case-b", "argv": ["--max-grid-size", "0"]}
  ]
}
```

The example values illustrate argument passthrough only; they are not defaults.
Include the complete real argv for each case in the campaign-local file.

Run a fresh sweep from the repository root:

```bash
skills/warpx/scripts/run_local_cuda.sh \
  skills/warpx/scripts/benchmark_gpu.py \
  --python .runtime/warpx-cuda-openpmd/bin/python \
  --program /absolute/path/to/candidate.py \
  --cases /absolute/path/to/campaign-cases.json \
  --output artifacts/warpx-gpu-scaling-YYYYMMDD \
  --repeats 2 \
  --required-path relative/program/completion.json
```

The harness refuses a non-CUDA AMReX build, runs every case in an isolated
directory, checks required nonempty artifacts, and records exact argv,
end-to-end wall time, optional WarpX evolve time, GPU identity, and summaries.
It does not decide whether a scientific result is valid.

Do not assume the GPU is faster than the CPU, and do not transfer a launch
choice between workloads. Rebenchmark after changing the program, arguments,
diagnostics, runtime, or device.
