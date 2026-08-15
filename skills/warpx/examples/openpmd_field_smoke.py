"""One-step 2D openPMD/HDF5 field-diagnostic smoke; never scientific evidence."""

import json
from pathlib import Path

import openpmd_api as io
from pywarpx import picmi

grid = picmi.Cartesian2DGrid(
    number_of_cells=[8, 8],
    lower_bound=[0.0, 0.0],
    upper_bound=[1.0e-3, 1.0e-3],
    lower_boundary_conditions=["periodic", "periodic"],
    upper_boundary_conditions=["periodic", "periodic"],
    lower_boundary_conditions_particles=["periodic", "periodic"],
    upper_boundary_conditions_particles=["periodic", "periodic"],
    warpx_max_grid_size=8,
)
solver = picmi.ElectromagneticSolver(grid=grid, method="Yee")
simulation = picmi.Simulation(
    solver=solver,
    time_step_size=1.0e-14,
    max_steps=1,
    particle_shape=1,
    verbose=1,
    warpx_random_seed=1,
    warpx_serialize_initial_conditions=True,
    warpx_amrex_the_arena_init_size=256 * 1024 * 1024,
    warpx_used_inputs_file="openpmd_used_inputs",
)
for particle_type, name in (("electron", "electrons"), ("proton", "ions")):
    species = picmi.Species(
        particle_type=particle_type,
        name=name,
        initial_distribution=picmi.UniformDistribution(
            density=1.0e15,
            rms_velocity=[1.0e3, 1.0e3, 1.0e3],
        ),
        warpx_do_not_push=True,
    )
    simulation.add_species(
        species,
        layout=picmi.GriddedLayout(
            grid=grid,
            n_macroparticle_per_cell=[1, 1],
        ),
    )

simulation.add_diagnostic(
    picmi.FieldDiagnostic(
        name="fields",
        grid=grid,
        period=1,
        data_list=["E", "B", "J", "rho"],
        write_dir="openpmd_diags",
        warpx_format="openpmd",
        warpx_openpmd_backend="h5",
        warpx_openpmd_encoding="f",
    )
)
simulation.step()

used_inputs = Path("openpmd_used_inputs").read_text()
h5_files = sorted(Path("openpmd_diags").rglob("*.h5"))
iteration_count = 0
mesh_record_count = 0
if h5_files:
    series = io.Series(str(h5_files[0]), io.Access.read_only)
    # Iteration objects have .time and .meshes, not .iteration.
    iteration_count = len(series.iterations)
    mesh_record_count = sum(
        len(series.iterations[index].meshes) for index in series.iterations
    )
    series.close()

checks = {
    "completed": True,
    "openpmd_format_native": 'fields.format = "openpmd"' in used_inputs,
    "h5_backend_native": 'fields.openpmd_backend = "h5"' in used_inputs,
    "h5_file_nonempty": bool(h5_files and h5_files[0].stat().st_size > 0),
    "iteration_readable": iteration_count > 0,
    "mesh_records_readable": mesh_record_count > 0,
    "scientific_evidence_eligible": False,
}
Path("openpmd_capability_smoke.json").write_text(
    json.dumps({"checks": checks}) + "\n"
)
