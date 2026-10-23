# CAD handoff to meshing

The local simulation started with existing STEP parts. Its lessons concern
geometry exchange and solid topology, and transfer to CAD authored in FreeCAD.

Declare units at each boundary. FreeCAD geometry calls in the supplied example
use millimeters; the meshing/solver script may use meters. STEP carries units,
but verify the imported bounding box before applying any scale conversion.
Scaling twice silently changes lengths, volumes and inferred electrical values.

Preserve source CAD. Write cut/simplified variants separately, together with the
parameters that generated them. Save the `.FCStd` model if future edits need
parametric history; export STEP or BREP for a reproducible meshing input.

Check `shape.isValid()`, the solid count, volume and bounding box before and
after Boolean operations. Re-import the exported STEP for a handoff check.
A visually touching pair of solids does not necessarily give a conformal
interface in a finite-element mesh. Meshing needs shared interfaces, deliberate
contact definitions or another physically justified connection.

For a reduced simulation model, keep enough feed/return or support geometry to
apply meaningful boundary conditions. A convenient flat cut is a modeling
choice, not proof that omitted hardware has no influence. Document what was
removed and how its effects are represented in the downstream model.

Headless installation experience: FreeCAD looks up the user's home through a
system API, so setting ordinary `HOME` alone did not work in the isolated
namespace. The capability sets `FREECAD_USER_HOME=.` to use the writable case
directory. Keep this setting when embedding the installed module in another
isolated runner. The installed `.so` modules and Python ABI must match.
