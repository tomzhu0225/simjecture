# Recorded demo: Gray–Scott counterexample

This completed 23.8-minute campaign is the primary version 0.1 autonomous
demonstration. The agent received one natural-language hypothesis and no
campaign instruction. It selected its own mathematics, solver, parameters,
diagnostics, daughter hypothesis, prospective evidence contracts, and stopping
condition.

```text
At fixed reaction parameters, whether a two-dimensional Gray-Scott
reaction-diffusion system develops a persistent spatial pattern is determined
solely by the diffusion ratio D_u/D_v, independent of the absolute diffusion
scale.
```

The agent rejected the installed WarpX capability as inappropriate, authored a
NumPy pseudospectral reaction-diffusion solver, and found a finite-domain
counterexample. With `F=0.072`, `k=0.062`, `L=40`, and `D_u/D_v=3` fixed, the
`s=1` case retained a pattern while the `s=10` case decayed to homogeneity.

```{figure} ../_static/demos/gray-scott-result.png
:alt: Final Gray-Scott fields at two absolute diffusion scales and the recorded pattern measure over time.
:width: 100%

The contract evidence changes only the common diffusion scale. Both timestep
resolutions lead to the same disposition.
```

## Hypothesis graph and guarded closure

The campaign created one scientific daughter. The child was supported and the
root was falsified. When the agent first tried to use child-contract evidence
to close the root, the harness refused because the root lacked its own
prospective evidence contract. The agent then registered the missing contract,
ran a fresh four-case experiment with different perturbation phases, and
closed the root with qualifying evidence.

```text
× claim_root                         falsified
└─ ✓ claim_finite_gs (refines)       supported
```

```{figure} ../_static/demos/gray-scott-completed-tui.svg
:alt: Terminal interface attached to the completed Gray-Scott run, showing the falsified root and supported daughter hypothesis.
:width: 100%

The present interface attached read-only to the preserved run. Durable JSON and
JSONL files, rather than the interface, remain authoritative.
```

## Audit or replay

The repository includes the complete transcript, portable claim ledger, final
report, provenance map, all 22 generated workspace artifacts, final fields,
and the exact decisive program under
[`demos/gray_scott_counterexample/`](https://github.com/tomzhu0225/simjecture/tree/main/demos/gray_scott_counterexample).

```bash
uv run simjecture status demos/gray_scott_counterexample/record
uv run python demos/gray_scott_counterexample/verify_record.py
uv run simjecture web demos/gray_scott_counterexample/record --read-only
uv sync --extra tui
uv run simjecture tui demos/gray_scott_counterexample/record
```

This is evidence for autonomous, evidence-governed computation within a
specific numerical model. It is not evidence that arbitrary hypotheses can be
solved reliably, and it is not plasma validation.
