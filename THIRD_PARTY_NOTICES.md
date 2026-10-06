# Third-party notices

The Cylinder Warp-LBM solver, scripts and validation records under
`src/conjecture_solver/vendor/cylinder_lbm` were contributed by
[Zifei Meng](https://github.com/ZifeiMengSPH) under Apache-2.0. Its LICENSE, NOTICE
and source provenance are preserved in that directory. Simjecture supplies the
installer and execution adapter. NVIDIA Warp is a separately installed dependency;
its package includes its own license and notices.

Simjecture depends on separately distributed open-source
packages, including HTTPX, NumPy, Pydantic, and SciPy. Their licenses are
reported by the installed Python distributions and are not replaced by this
repository's Apache-2.0 license.

WarpX is an optional external simulation capability. The repository contains
integration guidance and independently authored launch and diagnostic code; it
does not relicense WarpX, its binaries, or its dependencies. Consult the WarpX
distribution for its license and required notices.

FLASH is an optional, separately obtained simulation capability. FLASH is not
distributed by this repository. Its upstream terms restrict redistribution and
describe separate commercial-use requirements. Operators must obtain FLASH
from the [official code-request page](https://flash.rochester.edu/site/flashcode/coderequest.html),
review the current license, and keep acquired source, modified source, and built
binaries outside this source distribution. Simjecture's `flash-mhd` skill and
capability metadata do not relicense FLASH.

Optional equation-of-state and opacity packages (atoMEC, Singularity-EOS,
M-ANEOS, and Optab) are obtained under their upstream licenses. The
operator-triggered installer may clone and build pinned revisions into a
Git-ignored runtime; this repository still does not relicense those packages or
commit their source, binaries, or atomic databases. Consult each upstream
distribution for its license and required notices.

Model providers, literature services, and externally supplied guided
commissioning packages are services or inputs rather than sublicensed parts of
this source distribution. Run artifacts must retain the provenance and license
information supplied by their generators.

The optional ITER ecosystem pack downloads CHERAB, Raysect, CHERAB-IMAS,
CHERAB-ITER, IMAS-Python, IMAS-Validator and their dependencies under their
respective upstream licenses. Solver guides refer to separately distributed
JOREK, SOLPS-ITER/EIRENE and DINA-PS. Their component code, data, citation and
redistribution terms remain upstream terms; Simjecture does not relicense them
or imply ITER endorsement. The diagnostic demo is independently authored using
public APIs; its CHERAB bremsstrahlung API reference is credited in the script.

The shared Simjecture logo wordmark is outlined from Open Sans Semibold. Its
attribution and Apache 2.0 license are retained beside the distributed artwork in
[src/conjecture_solver/web/static/brand/OPEN-SANS-NOTICE.txt](src/conjecture_solver/web/static/brand/OPEN-SANS-NOTICE.txt)
and [APACHE-2.0.txt](src/conjecture_solver/web/static/brand/APACHE-2.0.txt).
No font binaries or external font dependencies are included.
