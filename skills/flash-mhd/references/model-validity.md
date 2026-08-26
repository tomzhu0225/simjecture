# Model validity

Read this reference before selecting a FLASH model and again before promoting a
run from workbench to evidence.

## Select the closure from the claim

- **Ideal MHD** is appropriate only when non-ideal flux transport is outside the
  claimed observable and unresolved dissipation cannot determine the result.
- **Resistive MHD** represents collisional magnetic diffusion through the
  selected resistivity model. Confirm that the intended coefficient is
  compiled, active, dimensionally consistent, and distinguishable from
  numerical diffusion.
- **Hall/extended MHD** can represent ion-electron drift in magnetic transport
  and selected Braginskii terms when compiled into the Unsplit Staggered Mesh
  solver. It remains a fluid closure.
- **Kinetic or hybrid evidence** is required when distribution functions,
  particle trapping or acceleration, finite-orbit effects, pressure-tensor
  physics, or electron-scale dissipation decide the claim.

FLASH Hall physics adds Hall transport to magnetic and total-energy fluxes and
accounts for Hall-induced wave speeds in timestep selection. It does not evolve
a kinetic electron distribution or a full electron pressure tensor, and it is
not a replacement for a two-species kinetic calculation. A Hall calculation
still needs an applicable mechanism for magnetic-flux breaking.

Do not enable Hall terms in an arbitrarily normalized fluid problem. The FLASH
implementation derives electron density and transport coefficients from the
physical state, composition, equation of state, and physical constants. Establish
a consistent physical-unit mapping and verify the realized characteristic scales
before interpreting Hall behavior.

## Commission the representation

Choose checks appropriate to the active claim. A scientific FLASH contract will
usually need evidence from all of these aspects:

- **representation:** geometry, dimensionality, components, coordinates, units,
  initial state, and equation of state;
- **physics controls:** required resistive, Hall, transport, source, cooling, or
  forcing terms are active and have a measured effect against an applicable
  control;
- **boundaries:** implemented parity or flux conditions match the mathematical
  model and do not dominate the diagnostic region;
- **diagnostics:** stored variables, centering, normalization, sign conventions,
  measurement windows, and estimators are verified from realized output;
- **numerical regime:** relevant structures and timescales are resolved, the
  timestep is adequate, conservation and positivity are controlled, and the
  result is stable under applicable refinement.

Monitor the divergence constraint for the magnetic field and report its norm in
a scale-aware form. Check mass, momentum, and energy budgets when their source
and boundary fluxes are available. Compare explicit physical diffusion with
numerical diffusion through controls or convergence rather than assuming that a
configured coefficient dominates.

## Escalate honestly

If refinement moves the decisive structure toward an omitted scale, or if a
required closure is absent, do not tune the fluid model until it reproduces an
expected answer. Record the model wall. A later Hall, hybrid, or fully kinetic
calculation is a new instrument path with its own prospective commissioning and
evidence.
