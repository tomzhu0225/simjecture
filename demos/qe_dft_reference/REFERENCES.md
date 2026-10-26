# Primary sources and comparison limits

- QE source/package: https://github.com/QEF/q-e (GPL-2.0); conda-forge qe 7.4
  hac89879_0. Runtime build record preserves exact dependencies and artifact hashes.
- GBRV author site https://www.physics.rutgers.edu/gbrv/ states GNU public license
  and links https://www.physics.rutgers.edu/gbrv/gpl-3.0.txt . The Si file is
  https://www.physics.rutgers.edu/gbrv/si_pbe_v1.uspp.F.UPF ; actual downloaded
  SHA256: 2c4b1bce6f4e3fa41dd4381f20760fe142399a42784b697712339d0b6b31c316.
  No PP is relabeled as Apache-2.0; fetch it separately before offline replay.
- Garrity et al., Computational Materials Science 81 (2014) 446–452,
  https://doi.org/10.1016/j.commatsci.2013.08.053 ; author manuscript
  https://www.physics.rutgers.edu/gbrv/psp9 recommends 40/200 Ry for the library.
- Csonka et al., PRB 80, 035107 (2009), https://arxiv.org/abs/0903.4037 ,
  Table II: diamond Si PBE/BAND lattice constant 5.466 Angstrom; PBEsol 5.431,
  zero-temperature/zero-point-corrected experimental reference 5.416. This is a
  different all-electron implementation, so compare physical scale, not exact
  same-PP numerical agreement.
- GPAW official Si tutorial
  https://gpaw.readthedocs.io/tutorialsexercises/electronic/pbe0/pbe0.html :
  a=5.43 Angstrom, PBE/PAW, PW200eV, Gamma-centered8³ gives ΓΓ=2.559 eV and
  ΓX=0.707 eV. ΓX is an endpoint transition, not the true internal Γ-X CBM gap.
  Different lattice and PP preclude a tight tolerance against this QE run.

All reported measured values must come from the new run summaries. No absolute
energy cross-comparison, quasiparticle-gap claim or autonomous discovery is made.
