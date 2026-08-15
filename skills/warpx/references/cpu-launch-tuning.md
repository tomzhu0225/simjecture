# Local CPU launch tuning

Use this resource only to tune execution of an already authored program. It
must not supply physical parameters, expected outcomes, acceptance thresholds,
or a benchmark problem. Benchmark the exact frozen program and argument list
selected within the active campaign.

## Guard MPI first

Query the loaded AMReX library:

```bash
python -c "import amrex.space2d as a; print(a.Config.have_mpi, a.Config.have_omp)"
```

Use `mpiexec` only when `have_mpi` is true. The presence of an MPI launcher or
MPI environment variables is insufficient. With a non-MPI AMReX wheel,
`mpiexec -n N python run.py` starts independent simulations that can waste
resources and overwrite the same files.

## Benchmark contract

- Pass the candidate program's complete argument list after `--`. The harness
  forwards it unchanged and varies only the OpenMP environment.
- Require at least one nonempty, program-produced completion or validation
  artifact with `--required-path`. Choose that artifact in the active campaign;
  the tuning harness does not define scientific success.
- Use enough work to make initialization a small fraction of elapsed time.
- Hold program source, arguments, random-seed policy, output cadence, and input
  data fixed across thread cases.
- Set math-library threads to one to prevent nested oversubscription.
- Treat a zero exit status as necessary but not sufficient; inspect the
  required validation artifacts before adopting a launch configuration.

Run from the repository root with a fresh output directory:

```bash
.runtime/warpx-cpu/bin/python skills/warpx/scripts/benchmark_cpu_threads.py \
  --python .runtime/warpx-cpu/bin/python \
  --program /absolute/path/to/candidate.py \
  --output artifacts/warpx-cpu-scaling-YYYYMMDD \
  --threads 1,4,8 --repeats 2 --affinity close --places cores \
  --required-path relative/program/completion.json \
  -- <exact candidate-program arguments>
```

Everything after `--` belongs to the candidate program. The harness writes
per-run logs, `runs.csv`, and `summary.json`, including the exact argv and
required-path checks.

There is no portable default thread count, affinity, or AMReX block size.
Rebenchmark after changing the executable, program, arguments, grid,
distributions, interactions, diagnostics, host, or runtime build. Prefer the
fastest case that preserves the candidate program's own validation results.
