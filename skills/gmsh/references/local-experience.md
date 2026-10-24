# Lessons from local CAD and meshing work

- Inspect imported bounding boxes and units before meshing. A meter/millimeter
  mistake propagates into resistance, field strengths, volume integrals and
  circuit parameters. For the tested SI route, set
  `gmsh.option.setString("Geometry.OCCTargetUnit", "M")` before STEP import,
  then verify the resulting bounds. Store the conversion in the script.
- With OpenCASCADE, synchronize after edits. Boolean cuts/fragments can replace
  entity tags. Use returned entity mappings, geometric locations or other
  explicit selection criteria to rebuild physical groups after the operation.
- Fragment touching volumes when a conformal material interface is needed. For
  a continuous conductor, check face connectivity after meshing; sharing only a
  vertex or edge is insufficient. Other models may intentionally have separate
  components, so one connected component is not a universal mesh requirement.
- Retain all material volumes, air regions and named boundary groups needed by
  the solver. Check the exported mesh rather than assuming the in-memory CAD
  physical groups survived format conversion. Physical and elementary entity
  tags are different; Elmer body numbering can differ again.
- In the local load model, a broad fine-size box refined much more air than the
  physics needed. Separate refinement regions near the coil and shell, with a
  shorter transition, greatly reduced element count. Count elements by body and
  inspect the air mesh before concluding that hardware RAM is the limitation.
- Cutting lower hardware helped, but the driven and return faces still had to
  form meaningful ports. Save cut location, retained parts and face selections.
  Check cut-location and outer-domain sensitivity independently of local mesh
  refinement; a smaller mesh can still represent the wrong boundary problem.
- Save a geometry BREP, generated mesh, script parameters, source CAD hashes,
  physical-group map and basic quality statistics. Mesh-size targets are not
  exact edge-length guarantees; evaluate the actual mesh and relevant outputs.

For the tested ElmerGrid route, use `Mesh.MshFileVersion = 2.2` and
`ElmerGrid 14 2 load.msh -out mesh`. This is a known interoperability path,
not a restriction on Gmsh. Check your solver's supported format and element
orders when choosing another route. Native Gmsh choices remain available.

OpenCASCADE is Gmsh's CAD kernel; it is not a separate Simjecture tool entry.
On a headless Linux host, a missing `libGLU.so.1` can prevent even importing
Gmsh. The managed installer supplies it without changing system packages.

For a changed current path, validate intended contact and unintended interference
separately. In the Qin-1 extension, blindly reflecting a feed intersected other
hardware; the accepted version required a new clearance hole and mount. Record
fixture changes alongside winding parameters. Rebuild tags after those Boolean
operations, then check the resulting conductor connectivity and port surfaces.
A geometrically valid part can still violate an electrical design criterion.

Bind each generated mesh to the actual CAD hashes and geometry parameters used.
When exporting material labels to a Cartesian downstream model, state how a cell
is classified: a cell with one solid corner is not the same as an exact solid
volume fraction or a particle-surface intersection. Keep that distinction in
later overlap and boundary diagnostics.
