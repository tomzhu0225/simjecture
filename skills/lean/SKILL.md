---
name: lean
description: Formalize and check mathematical propositions and numerical-method properties with Lean 4 and Mathlib. Use for formal conservation, exact counterexamples, theorem refinement, or explicit complexity models; compilation alone does not validate a physical solver.
---

# Lean

Install `simjecture install lean`; check `simjecture doctor --profile lean`.
The capability `lean-4.24.0` pins Lean and Mathlib v4.24.0. Its Python entrypoint
supports ordinary standard-library scripts importing `lean_check`. The installer
fetches the finite-sum, real-arithmetic, `Ring`, and `NormNum` dependency closure;
use focused imports such as `Mathlib.Tactic.Ring`. Broad `Mathlib.Tactic` imports
can exceed the sandbox memory allowance and are not installed by this recipe.

Write a Lean source and a short Python driver:

```python
from lean_check import check
result = check("Scheme.lean", ["Scheme.conservation"], output="proof", timeout=60)
print(result["status"])
```

In a minimal study, use `lab.run("check_scheme.py", capability="lean-4.24.0",
inputs=["Scheme.lean"], outputs=["proof/result.json", "proof/compile.log"],
stage="exploration")`. Declare the audit log and frozen sources as outputs when
needed. The existing method and evidence contracts apply to decisive runs.
Classic agents use `run_capability` with the Python driver as `argv[0]`.
The capability runs without network in the existing bounded Simjecture sandbox.

For trusted local work, the same driver is available through
`python -m conjecture_solver.lean_check Scheme.lean --theorem Scheme.conservation
--output proof`. This direct invocation is cooperative host execution; use the
capability sandbox for untrusted authoring. It is not a general Lean code sandbox.

The checker freezes the input, checks it, then imports its compiled module into
an independently generated audit. Each requested name must be a theorem, with
transitive axioms limited to `propext`, `Classical.choice`, and `Quot.sound`.
Receipts retain source hashes, runtime identity, exact commands, diagnostics,
resource limits, and per-theorem axioms. Output directories must be new.
`proved` applies only to the named, inspected mathematical statements.
`undecided`, `timeout`, `unavailable`, and `rejected_source` do not falsify a claim.
Inspect theorem assumptions and definitions even when the audit passes.

Author ordinary mathematical declarations using installed `Mathlib`, `Std`, or
`Init` imports. The conservative source policy rejects placeholders, custom axioms,
metaprogram commands, and option changes (including occurrences in comments).
It is an authoring guard, not a security parser. Arbitrary local modules and runtime
dependency downloads are not supported. Split larger developments only after
extending the dependency/provenance contract explicitly.

Start with an exact one-step identity; then generalize to arbitrary grids. For
finite volumes, specify shared face fluxes, the periodic neighbor permutation,
uniform volumes, and the arithmetic domain. A conservation proof says nothing by
itself about positivity, entropy, PDE convergence, floating-point implementation,
or optimality. State an algorithm class and cost/accuracy model before claiming
optimality; a timing improvement needs a matched-accuracy benchmark.

For a failed conjecture, search separately for a witness and validate it with
exact arithmetic or a certified error bound. Retain initial admissibility, all
parameters, the violated inequality, the original claim, and its refinement.
Do not label a scripted sequence autonomous discovery.

The repository demo `demos/lean_euler` progresses from scalar decay to periodic
finite-volume conservation and a compressible Euler counterexample. The example
`examples/health_check.py` tests installation behavior, not scientific qualification.
