# Adaptive FLASH stepping and useful full trajectories

Use the installed solver's adaptive timestep as the normal starting policy for
an evolution calculation. Inspect the compiled timestep implementation and
problem parameters rather than carrying a commissioning cap into production.
FLASH takes the minimum of the active unit restrictions and the operator's
upper bound. An implicit diffusion or radiation operator does not remove the
hydrodynamic CFL limit or its own accuracy requirements.

`dtinit` controls startup, `dtmax` is an upper bound, and `cfl` scales the
hydrodynamic stability restriction. An upper bound of 1 ns does not force a
1 ns update. The accepted step can shrink near stagnation. Check the installed
version's growth-factor parameter, native step log and radiation convergence
messages. Keep adaptive CFL stepping enabled unless a fixed-step comparison or
other explicit numerical purpose requires a cap. Never set a large constant
step merely to reach the campaign deadline.

A startup smoke does not qualify time accuracy through a radiation peak.
Compare adaptive settings at the same mesh, physical inputs, boundaries,
radiation groups and analysis definitions over the relevant window. Retain
step history, solver convergence, finite/positive states, energy observables,
peak timing and applicable conservation/divergence checks. State tolerances
prospectively. Global energy agreement alone does not bound a small causal
reconnection contribution or establish spatial convergence.

First obtain an affordable complete exploratory trajectory through the required
observable. A coarse complete 3D case can reveal feasibility and where refinement
matters; it cannot by itself establish a quantitative reconnection conclusion.
Separate radiation/operator setup cost from evolution cost, and measure rank
scaling rather than assuming more MPI ranks help. Record the observed physical
coverage and wall cost. A linear startup extrapolation is provisional.

Expose live timing on recorded experiments when useful:

```python
lab.run(
    'case_runner.py', outputs=['result.json', 'diagnostics.tar'],
    stage='exploration', purpose='validation',
    monitor={'path': 'case/execution.log', 'format': 'flash',
             'unit': 'ns', 'target': 40.0},
    resources={'cpus': 8, 'memory_mb': 16384, 'gpus': 0},
)
```

Choose the target from the study, not from this example. Mutable log telemetry
supports execution decisions only; freeze and analyze artifacts for evidence.
If the full trajectory is unaffordable, consider qualified adaptive settings,
mesh/cadence/rank changes, restarts, or a scientifically justified patch. Record
physical scope changes explicitly. Do not substitute an easier physical model
and claim the original hypothesis was tested.
