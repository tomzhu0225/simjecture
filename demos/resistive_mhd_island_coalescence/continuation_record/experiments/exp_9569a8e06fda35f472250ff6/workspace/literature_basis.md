# Literature boundary for the resistive-MHD campaign

The classical Sweet-Parker result is a single-fluid resistive-MHD scaling. For
a steady, long and thin current sheet with uniform magnetic diffusivity,
mass conservation and Ohmic flux transport give
`delta/L ~ S^(-1/2)` and `v_in/V_A ~ S^(-1/2)`. That makes resistive MHD the
appropriate first instrument for this claim, provided the sheet is resolved,
remains on a single-sheet branch, and is larger than the omitted kinetic
scales.

The island-coalescence literature also supplies the expected failure modes.
[Huang and Bhattacharjee (2010)](https://arxiv.org/abs/1003.5951) recovered the
Sweet-Parker dependence below a configuration-dependent transition and found a
plasmoid-mediated departure at larger Lundquist number. Their reported
critical value is a benchmark for that setup, not a universal constant.
[Cassak, Shay, and Drake (2005)](https://doi.org/10.1103/PhysRevLett.95.235002)
and their [onset analysis](https://arxiv.org/abs/physics/0604001) describe the
fluid-to-Hall boundary when the Sweet-Parker layer approaches the ion inertial
scale.

FLASH 4.8 can add Hall transport and its associated timestep constraints in
the Unsplit Staggered Mesh solver, as documented in the official
[FLASH Hall-MHD unit documentation](https://flash.rochester.edu/site/flashcode/user_support/flash_ug_devel/node107.html).
That is an extended-MHD closure, not a kinetic electron model or a full
two-fluid distribution-function calculation. Hall transport by itself also
does not supply every electron-scale flux-breaking term. Consequently this
campaign may identify a resistive-MHD scaling branch and its numerical,
plasmoid, or model boundary, but a kinetic claim must move to a separately
commissioned kinetic instrument.

Pulsed-power reconnection can approach the transition where the current-sheet
thickness is comparable with the ion skin depth; for example,
[Hare et al.](https://arxiv.org/abs/1711.06534) discuss collisional and kinetic
scales in a driven laboratory reconnection platform. That makes the present
normalized MHD campaign a useful commissioning rung toward a Z-pinch-related
regime, not by itself a dimensional Z-pinch prediction.

All literature statements are context for model selection. They are not
simulation evidence for the active hypothesis.
