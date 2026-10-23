# Plasma validation lessons

When a plasma initialization is justified, it can avoid modeling the initial
solid. Record the initialization and its consequences: an imposed plasma
profile does not predict wire heating or ablated mass. A plasma-stage model
still needs EOS, transport, charge evolution, emission, and absorption with
compatible energy conventions.

Validate the smallest applicable literature case before extending the state
space. Exact configuration/transition counts check construction; agreement
with a published charge balance checks the retained population model. Neither
checks all omitted atomic configurations or establishes experimental accuracy.

For high-Z ions, relativistic splitting and configuration interaction can
change important spectral features. Statistical arrays can match main peaks
while missing wings. Inspect spectral convergence before trusting averages,
especially inverse-opacity weighting in a Rosseland mean.

A normalized population distribution is not a completeness test. Report the
populations at both charge-window edges and expand the window. Then expand
the configurations within each ion: small edge populations do not demonstrate
that higher shells, autoionizing states, or dense-plasma effects are negligible.

An average-atom mean ionization is not a resolved charge-state distribution.
Agreement between mean charges from two models does not establish agreement
in line populations or spectral opacity. When comparing at fixed mass density
and temperature, recompute each model's electron density consistently.

Preserve distinction between LTE and non-LTE. Compare kinetic relaxation,
hydrodynamic, and cooling times, and assess radiation trapping. An optically
thin rate model and an LTE table are different closures. A narrow opacity
comparison does not establish either closure throughout an implosion.

Keep electronic/ionic energy and bound-state energy conventions explicit.
Adding a separate ionization source to an equilibrium EOS can count binding
energy twice. An electron-only EOS plus kinetic ions also needs the appropriate
nonideal ionic contributions wherever they matter.

Primary method reference: M. Poirier (2018),
<https://doi.org/10.1002/ctpp.201700070>.
