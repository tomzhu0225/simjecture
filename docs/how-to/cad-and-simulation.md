# CAD, meshing, simulation and visualization

Simjecture provides three independent engineering tools. **FreeCAD** creates
and edits CAD, **Gmsh** prepares geometry and generates meshes, and **Elmer** runs
finite-element models. **PyVista/VTK and Matplotlib are included in ordinary
Python**, so visualization needs no separate tool installation. The standard
Linux sandbox supports headless EGL rendering and system fonts; the
Debian/Ubuntu installer supplies those host dependencies when enabled.

These tool integrations were added in source after v0.6.3
([PR #43](https://github.com/tomzhu0225/simjecture/pull/43)), growing out of the
initial headless magnetic-field screening workflow proposed by
[`@motismoore-ctrl`](https://github.com/motismoore-ctrl) in
[PR #37](https://github.com/tomzhu0225/simjecture/pull/37). Use a build containing
that change. The [Qin-1 worked example](../demos/qin1-hardware-plasma.md) follows
geometry and feed redesign through Elmer/circuit calculations into a separately
supplied native WarpX build, with the numerical limits retained.

```bash
simjecture install freecad
simjecture install gmsh
simjecture install elmer --source /path/to/elmer-install
```

FreeCAD and Gmsh install in managed environments without system-package changes.
The Elmer installer adopts a prebuilt Linux installation and preserves its
solver modules. Use `simjecture doctor --profile freecad`, `gmsh` or `elmer` to
run the corresponding control. Elmer setup is agent-assisted because it needs
the installation directory. FreeCAD and Gmsh appear as separate installable
entries in the tool library.

The tools accept user-authored Python, Gmsh geometry and Elmer SIF inputs. The
skills explain their native interfaces and the geometry/mesh/result handoffs.
The local coil study supplies practical lessons and an optional conductor/RLC
example; it does not constrain which CAD models or Elmer physics users choose.
A heat-conduction control exercises the general Elmer interface. Geometry
controls check Boolean operations, STEP exchange and mesh validity.

The typical handoff is **CAD → mesh → simulation → visualization**. Users can
start from an existing STEP file, import an existing mesh or visualize results
from another solver. Software availability and model accuracy remain separate:
apply physical and numerical checks appropriate to the problem.
