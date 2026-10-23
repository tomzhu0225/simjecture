"""Small steady heat-conduction model through native ElmerGrid and ElmerSolver."""

import importlib.util
import json
import os
from pathlib import Path

import gmsh
import numpy as np
import pyvista as pv

spec = importlib.util.spec_from_file_location("elmer", os.environ["SIMJECTURE_ELMER_DRIVER"])
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
case = Path("heat-control").resolve()
case.mkdir()
gmsh.initialize()
try:
    gmsh.option.setNumber("General.Terminal", 0)
    surface = gmsh.model.occ.addRectangle(0, 0, 0, 1, 1)
    gmsh.model.occ.synchronize()
    gmsh.model.addPhysicalGroup(2, [surface], 100)
    other = []
    for dim, tag in gmsh.model.getBoundary([(2, surface)], False, False):
        x, _, _ = gmsh.model.occ.getCenterOfMass(dim, tag)
        if abs(x) < 1e-9:
            gmsh.model.addPhysicalGroup(1, [tag], 1)
        elif abs(x - 1) < 1e-9:
            gmsh.model.addPhysicalGroup(1, [tag], 2)
        else:
            other.append(tag)
    gmsh.model.addPhysicalGroup(1, other, 3)
    gmsh.option.setNumber("Mesh.MeshSizeMax", 0.1)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.model.mesh.generate(2)
    gmsh.write(str(case / "input.msh"))
finally:
    gmsh.finalize()
(case / "case.sif").write_text("""Header
  Mesh DB "." "mesh"
End
Simulation
  Coordinate System = Cartesian 2D
  Simulation Type = Steady
  Steady State Max Iterations = 1
  Output Intervals = 1
End
Body 1
  Target Bodies(1) = 100
  Equation = 1
  Material = 1
End
Equation 1
  Active Solvers(2) = 1 2
End
Material 1
  Heat Conductivity = 1
End
Solver 1
  Equation = Heat
  Procedure = "HeatSolve" "HeatSolver"
  Variable = Temperature
  Variable DOFs = 1
  Linear System Solver = Iterative
  Linear System Iterative Method = CG
  Linear System Preconditioning = ILU1
  Linear System Max Iterations = 1000
  Linear System Convergence Tolerance = 1e-12
  Linear System Abort Not Converged = True
  Nonlinear System Max Iterations = 1
End
Solver 2
  Exec Solver = After All
  Procedure = "ResultOutputSolve" "ResultOutputSolver"
  Output File Name = heat
  Vtu Format = True
  Binary Output = True
End
Boundary Condition 1
  Target Boundaries(1) = 1
  Temperature = 300
End
Boundary Condition 2
  Target Boundaries(1) = 2
  Temperature = 310
End
""")
grid = driver.run_native(
    "grid", case, ["14", "2", "input.msh", "-out", "mesh"], timeout=30, memory_gib=2
)
run = driver.run_native("solver", case, ["case.sif"], timeout=30, memory_gib=2)
assert grid["execution_pass"] and run["execution_pass"]
mesh = pv.read(next((case / "mesh").glob("heat*.vtu")))
field = next(name for name in mesh.point_data if name.lower() == "temperature")
error = float(np.max(abs(mesh[field] - (300 + 10 * mesh.points[:, 0]))))
report = {
    "checks": {"completed": True, "heat_solution": error < 1e-6},
    "max_temperature_error_K": error,
    "scope": "Native 2D heat-conduction control; other models use their own checks.",
}
Path("elmer_health.json").write_text(json.dumps(report, indent=2) + "\n")
assert report["checks"]["heat_solution"], report
