# Third-party notices

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
