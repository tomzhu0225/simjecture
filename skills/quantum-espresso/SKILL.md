---
name: quantum-espresso
description: Deploy Quantum ESPRESSO and run material-configured scalar and collinear plane-wave DFT with independent DOS and band branches, readable diagnostics and source-bound checks.
---

# Quantum ESPRESSO

Use `simjecture install quantum-espresso`, then `simjecture doctor --profile
quantum-espresso`. Users and agents use the same operator entry. The first
qualified environment is Linux/WSL2 x86_64, QE 7.4 conda-forge build hac89879_0.
Packages stay in the project's managed runtime; base Conda is unchanged.
See [deployment](references/deployment.md) for Windows invocation and disk limits.

The capability is `quantum-espresso-7.4`. It launches Python and exposes sibling
PW/PP executables through `QE_BIN`. Project Python need not contain QE.
The runtime smoke checks availability/version only; calculation validity requires
a separately commissioned numerical instrument.

Before any scientific execution, follow [research plan confirmation](references/research-plan.md):
preview the full effective plan with the user, disclose defaults and acceptance,
then record their explicit approval of the displayed hash. Deployment is not
calculation consent. The driver and launcher both require the unchanged plan,
protocol and confirmation. Reuse existing approval only for identical contents;
changes require a new preview/confirmation. Never self-approve a real research
plan just because installation or tests succeeded.

The reusable [driver](examples/dft_workflow.py) reads structures, species, PP
hashes, cutoffs, meshes, paths, empty bands and acceptance rules from JSON.
Configure nspin=1 or collinear nspin=2, fixed/smeared/tetrahedron occupations,
smearing widths and species starting magnetizations. Metals need no band gap.
See [workflow](references/workflow.md) for stage-specific settings and concrete
remaining gaps. Implementation coverage and real material validation are separate;
read each example's validation record rather than inferring coverage from a tool name.

Fetch pseudopotentials outside the offline sandbox. Verify source, license and
hash; never silently select a functional or PP. Execute only the confirmed
supported mode. Full mode comprises relaxation, final SCF, independent uniform
NSCF/DOS/optional PDOS and path bands/projections in a fresh output.
Keep raw inputs/outputs, XML-derived arrays, energy units, occupied-band counts,
source/runtime identities and command receipts. Binary checkpoints remain local.

Commission the actual configured program through the selected launcher.
Follow source-bound methods review and prospective contracts for evidence.
Guided readiness and copied reference outputs are exploratory context.
Run new materials through the same entry with a new case and its own checks.
Report numerical validation separately from implemented configuration modes.
