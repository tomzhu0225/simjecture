# Current qualification correction (2026-10-26)

The historical full-workflow pass in README.md, summary.json and
fe_reference_comparison.json is WITHDRAWN. Original Fe02 optimization XML has
exit_status=3 and opt_conv=false. Its SHA256 is
810b7840beab6e29afc847d65d80247c47add5c791682caed1e7eed784a216a2.
Original source: validation/fe_reference_02/workspace/result/relax/out/sample.save/data-file-schema.xml
under the local task root. This compact archive omitted that XML.

No historical file has been changed. The earlier README's current-source AST
claim is also historical and no longer true after the integrity fixes.
SCF/spectral observations and fixed-geometry controls remain historical data;
they do not establish successful optimization or an equilibrium lattice.
Current default analysis marks missing proof unqualified; supplying the original
failed XML yields failed, both with nonzero exit and workflow_passed=false.
Use a new reassessment output. A new converged run is needed to restore full
qualification; no new DFT was performed in this correction.
