# Numerical risks to challenge

The relevant risks depend on the proposed experiment. Consider at least those
that could change its discriminating observable:

- grid resolution relative to Debye, skin-depth, gyroradius, wavelength,
  gradient, sheath, or interface scales;
- timestep relative to plasma, cyclotron, collision, crossing, bounce, growth,
  and diagnostic timescales;
- finite-particle noise, loading correlations, random-seed sensitivity, and
  the noise floor of fitted rates;
- particle shape, deposition, field gathering, filtering, smoothing, and
  numerical heating;
- finite box size, periodic recurrences, boundary reflections, and unavailable
  wavelengths;
- velocity or momentum convention errors and incorrectly realized thermal or
  drift distributions;
- inconsistent dimensional normalization or species charge/mass;
- diagnostic aliasing, phase cancellation, post-selected fit windows, and an
  estimator that changes meaning between cases;
- a completed run whose conservation, charge balance, or solver residual is
  unacceptable;
- a nominal control parameter inferred only from input values when collisions,
  transport, temperature, density, or effective coefficients evolve;
- a claimed convergence comparison that changes physical parameters or the
  estimator together with resolution; and
- too little evolution in the relevant crossing, bounce, growth, collision, or
  transport time to establish the regime assumed by the claim.

Use a small number of targeted challenges tied to explicit auxiliary
subhypotheses. Do not scan every numerical knob without a reason, and do not
promote a failed numerical attempt as physical evidence.
