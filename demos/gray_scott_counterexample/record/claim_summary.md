# Claim summary

- status: `completed`
- iterations: 37
- open: (none)
- closed: claim_root, claim_finite_gs

## Finish notes

- all registered claims are closed
- closed_claim_count=2
- open_claim_count=0

## Claims

| id | kind | relation | status | contracts | evidence | statement |
| --- | --- | --- | --- | ---: | ---: | --- |
| claim_root | scientific | root | falsified | 1 | 2 | At fixed reaction parameters, whether a two-dimensional Gray-Scott reaction-diffusion system develops a persistent sp... |
| claim_finite_gs | scientific | refines | supported | 1 | 2 | On a fixed L=40 periodic 2D domain with reaction parameters F=0.072,k=0.062 and diffusion ratio Du/Dv=3 fixed, nonlin... |

## Details

### `claim_root`

Evidence contracts: 1 (latest v1)
- observable: Pattern measure P(t)=mean((u-mean(u))^2)/mean(u)^2 at t=1000 for two pseudospectral 2D Gray-Scott runs on identical L=40 periodic domain, F=0.072,k=0.062, fi...
- decision_rule: Root falsified iff P_s1/P_s10 > 1000 AND P_s1 > 1e-3. Root weakened/survives if margin is smaller; unresolved if near thresholds.

Evidence:
- `simulation_results.json` (iter 30, sufficient, run_python): Evidence for supported child claim_finite_gs, which directly contradicts the root. On L=40 periodic 2D domain, F=0.072,k=0.062, Du/Dv=3 fixed, P_s1=0.0858 an...
- `root_pattern_results.json` (iter 35, contract v1, sufficient, run_python): Under claim_root evidence contract v1: F=0.072,k=0.062, Du/Dv=3, L=40 periodic, N=128, t=1000, identical delta=1e-3 perturbation. P_s1=8.3745e-2 vs P_s10=4.3...

Closed reason: Root-level evidence contract v1 satisfied: P_s1/P_s10=1.93e16 > 1000 and P_s1=8.3745e-2 > 1e-3. Both dt=0.05 and dt=0.025 runs agree to five significant figures and are free of NaN/instability. At fixed reaction parameters and diffusion ratio, absolute diffusion scale alone changed the final outc...

### `claim_finite_gs`

Evidence contracts: 1 (latest v1)
- observable: Pattern measure P(t) = mean((u - mean(u))^2)/mean(u)^2 at final time t_end=1000 for two pseudospectral runs on L=40 periodic grid, F=0.072,k=0.062, fixed rat...
- decision_rule: Child claim supported iff P_s1_final/P_s10_final > 1000 AND P_s1_final > 1e-3. Child claim refuted iff P_s1_final/P_s10_final < 10 or P_s1_final < 1e-3. Inte...

Evidence:
- `simulation_results.json` (iter 27, contract v1, sufficient, run_python): Full decisive run: same F=0.072,k=0.062, Du/Dv=3, L=40 periodic, N=128, dt=0.05, t_end=1000, identical initial perturbation. P_s1=0.0858029786, P_s10=7.63960...
- `simulation_results_dt025.json` (iter 28, contract v1, sufficient, run_python): Convergence run with dt=0.025, N=128, t=1000: P_s1=0.0858032916 vs 0.0858029786 at dt=0.05; P_s10=7.64377e-10 vs 7.63961e-10. Relative changes <5e-6, so the ...

Closed reason: Evidence contract satisfied: P_s1_final/P_s10_final=1.12e8 > 1000 and P_s1_final=0.0858 > 1e-3. Temporal convergence at dt=0.025 reproduced both values, no NaN, and the s=10 field remained within 0.006% of the homogeneous steady state.

