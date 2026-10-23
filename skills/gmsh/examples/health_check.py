"""Headless OpenCASCADE Boolean, physical groups and tetrahedron Jacobians."""

import json
from pathlib import Path

import gmsh
import numpy as np

gmsh.initialize()
try:
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.NumThreads", 1)
    occ = gmsh.model.occ
    box = occ.addBox(0, 0, 0, 0.02, 0.01, 0.005)
    hole = occ.addCylinder(0.01, 0.005, 0, 0, 0, 0.005, 0.002)
    volumes, _ = occ.cut([(3, box)], [(3, hole)])
    occ.synchronize()
    gmsh.model.addPhysicalGroup(3, [tag for dim, tag in volumes], 100)
    boundaries = gmsh.model.getBoundary(volumes, combined=True, oriented=False)
    gmsh.model.addPhysicalGroup(2, [tag for dim, tag in boundaries], 200)
    gmsh.option.setNumber("Mesh.MeshSizeMax", 0.0015)
    gmsh.model.mesh.generate(3)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.write("part.msh")
    types, elements, _ = gmsh.model.mesh.getElements(3)
    count = sum(len(x) for x in elements)
    positive = True
    for element_type in types:
        points, _ = gmsh.model.mesh.getIntegrationPoints(int(element_type), "Gauss1")
        _, jacobians, _ = gmsh.model.mesh.getJacobians(int(element_type), points)
        positive = positive and bool(np.all(np.asarray(jacobians) > 0))
    checks = {
        "tetrahedra": count > 0,
        "positive_jacobians": positive,
        "physical_groups": set(gmsh.model.getPhysicalGroups()) == {(3, 100), (2, 200)},
    }
    Path("gmsh_health.json").write_text(
        json.dumps({"checks": checks, "elements": count, "version": gmsh.__version__}, indent=2)
        + "\n"
    )
    assert all(checks.values()), checks
finally:
    gmsh.finalize()
