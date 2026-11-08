# Checked 1D Poisson baseline

This completed baseline is retained for replay while research proceeds to 3D
Euler. No 1D PDF report is planned.

`Optimality.lean` solves `2*u_i-u_(i-1)-u_(i+1)=f_i` with zero Dirichlet boundaries
for every finite rational right-hand side. Six audited theorems establish exact
correctness, uniqueness, trace/output correspondence, `11*N+6` modeled work, an
`N` output-write lower bound for every correct completed trace, and a factor-17
comparison for `N>0`.

The model charges unit-cost scalar arithmetic/casts, input reads, branch
inspection, and explicit output writes. Its event trace is ghost instrumentation;
constructing that trace is not executed work. The lower bound is due to output
size. It also applies to an oracle already given the answers. This is an
asymptotic baseline, not a new fastest solver, a bit-complexity result, or a
hardware-time theorem. Python correspondence is tested, not formally refined.

```bash
.venv/bin/simjecture install lean
.venv/bin/python demos/lean_poisson/run_local.py --output artifacts/lean-poisson/replay-001
```

Choose a new artifact directory. The two actual exploratory Simjecture lab jobs
check the proof and run exact/float experiments. `record/` retains checked source
hashes, proof/audit logs, experiment metadata, and measurements. The 39 rational
cases agree exactly with an independent Thomas elimination implementation.

The float experiments are separate evidence: the largest smooth case, N=65536,
misses the prespecified normalized backward-error target of 5e-15. That failure
is retained rather than relaxing the threshold. The analytical discrete sine
reference is evaluated in binary64; it is not a certified floating-point error
bound. No independent scientific review has been performed.

For the standard tridiagonal elimination reference, see
[W. T. Lee, Thomas Algorithm](https://sites.nd.edu/gfu/files/2019/10/ms6021_thomas.pdf).
