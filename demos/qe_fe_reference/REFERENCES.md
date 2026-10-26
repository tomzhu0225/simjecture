# Fe primary sources and comparison limits

- [GBRV Fe PBE v1.5 UPF](https://www.physics.rutgers.edu/gbrv/fe_pbe_v1.5.uspp.F.UPF):
  generated 2015-06-15, scalar-relativistic USPP/NLCC, 16 valence electrons.
  SHA256: 6c132e6e7ac1c42df5cb6a13d0c99bb7af5bf3d6e2349f5658f0c22abfe3911a. PBE header is SLA PW PBX PBC PBE.
- [Author site](https://www.physics.rutgers.edu/gbrv/) links the
  [GPL-3.0 license](https://www.physics.rutgers.edu/gbrv/gpl-3.0.txt).
  PP and license are downloaded locally; no PP payload is redistributed here.
- [Author v1.5 update](https://www.physics.rutgers.edu/gbrv/delta_update_v15.pdf)
  specifically corrects early spin-polarized Fe/Cr/Mn tests and uses 40/200 Ry.
  That is a starting point, not a new-case convergence certificate.
- [Rahman et al., PRB 81, 184423 (2010)](https://arxiv.org/pdf/1005.0297):
  PBE FLAPW/all-electron, scalar-relativistic valence, no-SOC baseline, optimized
  volume/EoS; 0 K bcc a=2.83 Angstrom and computed mean moment 2.22 muB/atom.
  Table-II 2.237 muB is a local muffin-tin quantity; M=2.235 uses Tesla.
  Neither substitutes for the integrated QE total/absolute moment per cell.
