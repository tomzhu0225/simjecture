# PyVista in the standard Python environment

PyVista/VTK are installed with Simjecture's normal Python dependencies. Use
ordinary Python execution; no separate visualization capability is needed.
Matplotlib remains available for line plots, comparison figures and exports.

```python
import pyvista as pv

mesh = pv.read('fields.vtu')
print(mesh.point_data.keys(), mesh.cell_data.keys())
plotter = pv.Plotter(off_screen=True)
plotter.add_mesh(mesh, scalars='temperature')
plotter.show(screenshot='temperature.png')
```

For our local EM work, the most useful operations were volume integration,
probe sampling, slices, surface extraction, and field/current-density maps.
Keep these choices tied to the data:

- Solver elemental fields and recovered nodal fields are different. Integrate
  elemental quantities with element volumes where appropriate; record which
  representation was used. Interpolating an elemental discontinuity can hide it.
- `.sample(...)` can return invalid points. Check `vtkValidPointMask`; do not
  present a zero-filled outside-mesh sample as a physical zero.
- Cell IDs and material tags can change during conversion or extraction. Inspect
  the arrays and use the recorded body map rather than assuming CAD tags match.
- Compare vectors as well as magnitudes when direction matters. Label time,
  units, slice plane, source case and color saturation. Use common color scales
  for comparisons or explicitly label different scales.
- Coincident CAD faces caused z-fighting in an early geometry figure. Extract
  the intended surface or cut view instead of layering coplanar solids. Do not
  displace the numerical model merely to repair a picture.
- Preserve numerical arrays and provenance alongside figures. Failed cases can
  be plotted for diagnosis; label their status rather than treating appearance
  as validation. Our successful-looking early field plot had failed current
  conservation.

`off_screen=True` avoids an interactive window but still needs a usable VTK
rendering backend. The standard isolated Python runner selects EGL and limits Mesa worker
threads; it mounts system font configuration read-only for text rendering.
The Debian/Ubuntu setup route includes EGL/Mesa and fonts when system-package
installation is enabled. Users can override VTK settings in their scripts. If rendering is unavailable, VTK sampling/analysis can still
work; create a Matplotlib slice from sampled arrays or configure a supported
headless renderer. Do not start a display server merely for data processing.

## Comparing coupled simulation results

For mixed CAD/FEM/particle results, retain the distinction between display and
measurement. A slab average, a central profile and an integral over a plane are
different observables. Label their physical footprint and coordinate basis.
When comparing grids, use the same physical area, including fractional edge-cell
weights where needed, rather than accepting whichever cells fall in a loose index
slice. Changing the estimator after seeing a failed control changes the test.

Mask or flag quantities that are undefined or dominated by the numerical density
floor. In a hybrid-plasma viewer, a small positive bulk-flux number is not a
qualified shielding efficiency, and the integral of positive cell-mean velocity
is not a velocity-distribution-resolved one-way flux. Derive the relevant
diagnostic from the scientific question and preserve its formula.

CAD overlays and density isosurfaces provide spatial context. They do not prove
that absorbing solid boundaries were simulated, and a chosen density contour
does not identify a shock. If solid/near-solid cell overlap is displayed, state
the cell-classification rule and distinguish instantaneous cell moments from
particle trajectories, wall impacts and deposited heat.

For a standalone interactive artifact, embed the derived arrays and source
identities, preserve the physical aspect ratio, use consistent colour scales,
label clipped values, and link the numerical checks beside the visual result.
Check actual playback/layer selection and a narrow viewport. Preserve `.vtm`
companion files and test scene readback after packaging, not only before export.
