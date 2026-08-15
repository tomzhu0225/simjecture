# Recorded demo: collisionless GEM reconnection

This completed 177-minute campaign is the primary version 0.1 plasma
demonstration. It used a two-dimensional, three-velocity, fully kinetic
collisionless Harris sheet following the geometry and normalization of the GEM
magnetic reconnection challenge. The operator supplied a validated
CUDA/openPMD starting instrument; the agent chose and froze a fresh held-out
ensemble design before producing claim-bearing outcomes.

The starting instrument cites the
[GEM challenge](https://doi.org/10.1029/1999JA900449) and the
[0.1-rate review](https://doi.org/10.1017/S0022377817000666) as contextual
references. The run's literature search was preserved but was not eligible as
scientific evidence for the active claim.

```text
In two-dimensional, non-relativistic, fully kinetic, collisionless electron-ion
GEM-type Harris-sheet reconnection at reduced mass ratio 25 and the fixed
physical geometry and normalization of the supplied guided regime, the
seed-ensemble mean late-window normalized flux-slope reconnection rate at
Ti/Te = 1 is at least 25 percent larger than at Ti/Te = 20
(mu_1 / mu_20 >= 1.25), and this endpoint contrast persists under a
numerical-fidelity control.
```

The supplied anchor, its output, and three prior campaign audits were marked
non-evidentiary. Seed `20260814`, which motivated the endpoint claim, was
excluded. The agent selected fresh paired seeds `20260902`, `20260903`, and
`20260904`, ran both temperature endpoints at 16 and 8 particles per cell per
population, and commissioned separate simulator and analyzer claims.

```{figure} ../_static/demos/gem-ensemble-result.png
:alt: Recorded GEM flux histories, paired seed reconnection rates, and bootstrap ratio intervals at two particle counts.
:width: 100%

The 12 fresh CUDA simulations. The red dashed line marks the claimed ratio
threshold of 1.25; the dotted line marks equal endpoint means.
```

## Simulation and evidence contract

| Property | Recorded value |
| --- | --- |
| Representation | 2D3V; four fully kinetic electron/ion populations |
| Algorithms | explicit Yee fields; Esirkepov current deposition |
| Domain | `256 × 128`; `25.6 d_i × 12.8 d_i`; Harris half-width `0.5 d_i` |
| Plasma | `m_i/m_e=25`; `n_sheet=10^24 m^-3`; background fraction `0.2` |
| Normalization | `B0=65.4209 T`; `V_A,ref/c=0.04`; zero guide field |
| Resolution | `dx=dz=0.5 d_e`; 8 or 16 PPC per population |
| Integration | 4,623 steps; `dt ω_pe=0.3182`; CFL fraction `0.9` |
| Duration | `t Ω_ci=12.0013`; 26 openPMD field states per run |
| Boundaries | periodic in `x`; conducting fields and reflecting particles in `z` |
| Decisive window | OLS flux slope for `t Ω_ci ∈ [6,12]` |
| Energy gate | absolute combined field-plus-particle drift `≤2 × 10^-3` |
| Uncertainty | paired, 100,000-resample seed bootstrap |

Each of the 12 simulator summaries passed 26 five-aspect checks. Every run
passed its energy gate; the maximum absolute combined drift was
`4.8429 × 10^-4`. At 16 PPC each run represented 2,097,152 nominal
macroparticles. The scientific simulations reported 6,378.7 seconds of
aggregate CUDA execution, within 10,619.9 seconds for the complete 75-turn
campaign.

## Result and guarded interpretation

| Fidelity | mean rate, `Ti/Te=1` | mean rate, `Ti/Te=20` | ratio | bootstrap 95% interval |
| --- | ---: | ---: | ---: | ---: |
| 16 PPC | `0.075411 ± 0.000812` | `0.074500 ± 0.010967` | `1.0122` | `[0.8232, 1.4374]` |
| 8 PPC | `0.053390 ± 0.027564` | `0.049172 ± 0.025574` | `1.0858` | `[0.0150, 14.8310]` |

The frozen finite-sample rule falsified the operational child because the
valid 16-PPC group had `R16 < 1.25`; the 8-PPC point estimate also fell below
the threshold. The population statement remains unresolved because only three
seeds were sampled and the 16-PPC bootstrap interval includes 1.25. The 8-PPC
results are extremely seed-sensitive.

```text
○ claim_root                              open
└─ × claim_confirm_seed_ensemble          falsified
   ├─ ✓ claim_instr_simulator             supported
   └─ ✓ claim_instr_analyzer              supported
```

```{figure} ../_static/demos/gem-reconnection-fields.png
:alt: Final out-of-plane magnetic field and current density for the paired Ti/Te endpoints at 16 particles per cell and one held-out seed.
:width: 100%

Exact archived final states for the `20260902` pair at 16 PPC and
`t Ω_ci=12`. These representative fields are visual context; the contracted
claim used the complete seed ensemble and flux histories.
```

## Audit the preserved campaign

The repository contains the full top-level audit record plus 60 hash-verified
workspace artifacts, including every scientific summary and two representative
final-field arrays:

```bash
uv run simjecture status demos/collisionless_gem_reconnection/record
uv run python demos/collisionless_gem_reconnection/verify_record.py
uv sync --extra tui
uv run simjecture tui demos/collisionless_gem_reconnection/record
```

The original 893,147,359-byte workspace contained 482 artifacts. Bulk raw
openPMD histories are excluded from Git, but the committed provenance map
retains their names, sizes, hashes, commands, and claim relationships. See the
[complete demo guide](https://github.com/tomzhu0225/simjecture/tree/main/demos/collisionless_gem_reconnection)
for the exact autonomous launch input and guided commissioning package.

## Limits of the result

- The run used guided autonomy and a known-runnable simulator, not instrument
  invention from the hypothesis alone.
- Its scope is one 2D, reduced-mass-ratio, fixed-geometry regime through
  `t Ω_ci≈12`.
- Three seeds and two particle counts do not establish a population contrast or
  numerical convergence.
- The terminal prose overgeneralized the operational falsification; the durable
  ledger correctly leaves the immutable root open.
- Full raw-data reproduction still needs an external archive with a permanent
  identifier.
