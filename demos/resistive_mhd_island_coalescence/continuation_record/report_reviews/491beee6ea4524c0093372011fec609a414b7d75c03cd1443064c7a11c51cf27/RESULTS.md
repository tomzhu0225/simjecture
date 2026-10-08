# Island-coalescence continuation

No credible counterexample has been established. The original full-range, spatially resolved, pre-plasmoid single-branch hypothesis remains **unresolved**. No scientific disposition has been accepted. This continuation uses the same operator-supplied FLASH 4.8 executable and physical model; it does not substitute a solver or change the exponent band [-0.60,-0.40].

## Status and provenance

Fresh exact guided reproduction `exp_9569a8e06fda35f472250ff6` completed in 25.30 s and remains permanently non-evidentiary commissioning. The agent-owned source is `calculation.py`; the retained guided reader is `guided_reader.py`. Runtime identity is `1dbefbee9b1ae4784d75f242e60d9cb64e12f95a30c2017d0a5b8e5b04e36d80`. Each case retains executable, parameter, reader/runtime metadata and raw-field identities in `result.json`, plus `raw_fields.npz`, `case/flash.par` and the execution log.

Method `method_52376b86fd60e94689b8b2a0` required revision: an old CFL margin was imported and a three-point refinement description contradicted two planned refined samples. These were method errors, not physical counterexamples. Renewed method `method_462b34a5c15f82e6165b0cc4` permits fresh prospective collection only; it accepts no scientific claim.

Fresh full-window S=500 N256 CFL=.8/.4 commissioning runs `exp_27bae5c10115cc47b7ee511a` / `exp_f4615601bac4bd9ea59211c3` cost 55.87 / 109.75 s. Rates are 0.0654534793 / 0.0655177194, differing by 0.09805%. Recorded qualification `exp_5fa5b2433dfe1ea142b28d6f` derives the absolute log difference 0.000980980469 from hash-bound inputs. All four path/cadence variants cross both thresholds. This is fresh commissioning, not hypothesis evidence. Borrowing that sensitivity across other resistivities remains empirical.

## Observable and decision

The unchanged model is normalized two-dimensional compressible single-fluid MHD, uniform explicit eta, gamma=5/3, alpha=20, reflecting square boundaries. Four CPU MPI ranks use 2x2 decomposition, HLLD, adaptive CFL=.8, diffusion timestep control and cadence .025. The nominal inverse-resistivity control is S_eta=1/eta, not a dimensional Lundquist number.

The guided central By flux increment is independently crosschecked against a Bx path. First linearly interpolated crossings of flux .01 and .05 define R=.04/(t_high-t_low), with B0=vA0=L0=rho0=1. Failure to reach the window is censoring, not a counterexample. A retained last plot before requested tmax does not censor a reached window.

The frozen `protocol.json` specifies five distinct base controls 250,500,1000,2000,4000 at N256, and two fresh N384 matched controls at 250 and1000. Minimum evolving sheet FWHM is four/six cells; matched rate change must not exceed10%. Topology, divergence, boundary flux, conservation, sampled positivity and both path/cadence checks are required. Missing refinement remains null/unresolved.

Fit log R against log S by OLS. Empirical log-rate margins use twice the matched-grid change, path/cadence sensitivity and the fresh CFL sensitivity, with a minimum .01. Unrefined points explicitly borrow qualified margins. Propagate boxes to slope intervals; report Student-t regression intervals separately as descriptive fit diagnostics. An interval overlapping [-.60,-.40] does not reject that band. The common two-point fit measures endpoint-exponent persistence only; it cannot test refined curvature. Infeasible full-scan power laws without refined curvature confirmation remain unresolved. Finite samples do not prove continuous-domain universality.

## Fresh completed matched pairs

| S_eta | N | R | minimum FWHM cells | evidence-stage experiment |
|---:|---:|---:|---:|---|
| 250 | 256 | 0.08964507 | 14 | `exp_bfe4f90373621f5d11794fe6` |
| 250 | 384 | 0.08976683 | 22 | `exp_e1d0b9057facbbb61adf0d9c` |
| 1000 | 256 | 0.04953232 | 8 | `exp_bb0ee141588fbdda53787492` |
| 1000 | 384 | 0.04964290 | 10 | `exp_3cfeb359d713c480a5352496` |

Native preliminary postprocessing of these recorded fields gives endpoint p=-0.427927 at N256 with empirical interval [-0.442354,-0.413500], and p=-0.427298 at N384 with interval [-0.441724,-0.412871]. The change in endpoint exponent is0.000630. Matched rate changes are0.1358% at S250 and0.2233% at S1000. Both band-power-law feasibility checks succeed. There are only two common points, so no regression residual interval or refined curvature test is available. Frozen final postprocessing and independent claim review are still pending.

The following preliminary figures are drawn from fresh evidence-stage outputs, not from the guided anchor or inherited figures. They show prospective claim evidence before claim review. Full-resolution raw arrays remain in the case workspaces; the displayed field image is spatially sampled.

![Fresh rates and empirical uncertainty](scaling.svg)

![Fresh S1000 N384 magnetic-field magnitude and current density](field_current.svg)

The field/current figure uses `exp_3cfeb359d713c480a5352496` near the midpoint of its flux-crossing times; the actual snapshot time is in the figure and `plot_fields.npz`. Axes span x,y=[-.5,.5]. Current is Jz=∂By/∂x−∂Bx/∂y on the cell-centred grid. Positive and negative current use red and blue. The SVG separately normalizes panel colors; it is a structure diagnostic, not a quantitative cross-panel amplitude comparison.

## Historical context

Parent `/home/tomzhu0225/src/simjecture/artifacts/docs-refresh-20261008/island-sol-medium-study` contains five N256 evidence-stage trajectories and N384 refinements, but no accepted claim review. Their original status is retained. The parent high-S N384 experiment `exp_0994411061cacfc10dc58ebb` timed out after the measurement window; its exploratory recovery `exp_9034b82e23f918ebd5c8af3a` is not fresh validation or a successful solver completion.

Inherited rates at N256 were .0896451,.0654535,.0495323,.0380820,.0285929. Parent analysis excluded S500 because stride2 missed its upper crossing; that exclusion is preserved. The fresh tmax=.85 commissioning fixes this diagnostic gap. Parent common-three-point fits near p=-.412 had numerical slope intervals inside the allowed band, while a1% error-box single-law feasibility test showed slight curvature. That tiny curvature does not establish a current independently accepted falsification, especially without stronger numerical error qualification.

## Limitations and next test

Sampled floors and reconstructed conservation do not measure integrated floor/source corrections. Central-sheet extrema veto cannot exclude off-axis, subthreshold or between-output islands. FWHM counts and grid changes are empirical resolution checks, not certified continuum error bounds. Neither borrowed high-S errors nor one S500 CFL comparison certify the whole domain. No kinetic, Hall, dimensional tokamak or universal Sweet–Parker conclusion follows from this bounded model.

The next discriminating test after the planned fresh cases is a third common refined resistivity and a denser spatial/cadence control wherever curvature decides the result. A full-range universal support claim would additionally need justified unsampled-domain coverage. No hypothesis repair is committed without an accepted falsification.


## Finalization receipts

All five fresh N256 cases and both declared N384 refinements completed. S500 `exp_06f4378ece55c0f9fd6f2672` completed65.56s; S2000 `exp_67bf2fd4c24cf7a2e06afc43` completed158.87s; S4000 `exp_d2b9107fc5d67722a51735d1` completed206.64s. The S500 launch initially hit a storage reservation limit and was subsequently run fresh; the commissioning output was never promoted.

The final evidence-stage postprocessing request was rejected with `Method source/runtime changed; submit the revised method` after the additional measurement data inputs changed its binding. No rejected request is represented as successful evidence. Exploratory frozen analysis `exp_21784f8eee3e103d1fe1c9ea` was then cancelled at the compute cutoff. Bounded drafting analysis `exp_cff9836110ed71a44c1d6620` is currently pending and will supply explicitly exploratory final summary/figures. Numerical evolution has ended. These interface/operational failures do not falsify the physical claim.
