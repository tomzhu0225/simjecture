"""One-step WarpX/PICMI interface smoke; permanently non-evidentiary."""

import json
from pathlib import Path

from pywarpx import picmi

grid = picmi.Cartesian1DGrid(
    number_of_cells=[8],
    lower_bound=[0.0],
    upper_bound=[1.0e-3],
    lower_boundary_conditions=["periodic"],
    upper_boundary_conditions=["periodic"],
    lower_boundary_conditions_particles=["periodic"],
    upper_boundary_conditions_particles=["periodic"],
    warpx_max_grid_size=8,
)
solver = picmi.ElectrostaticSolver(grid=grid)
simulation = picmi.Simulation(
    solver=solver,
    time_step_size=1.0e-14,
    max_steps=1,
    particle_shape=1,
    verbose=1,
    warpx_random_seed=1,
    warpx_serialize_initial_conditions=True,
    warpx_used_inputs_file="warpx_used_inputs",
)
for particle_type, name, frozen in (
    ("electron", "electrons", False),
    ("proton", "ions", True),
):
    species = picmi.Species(
        particle_type=particle_type,
        name=name,
        initial_distribution=picmi.UniformDistribution(density=1.0e15),
        warpx_do_not_push=frozen,
    )
    simulation.add_species(
        species,
        layout=picmi.GriddedLayout(grid=grid, n_macroparticle_per_cell=[1]),
    )
simulation.step()
Path("capability_smoke.json").write_text(
    json.dumps(
        {
            "checks": {
                "completed": True,
                "scientific_evidence_eligible": False,
            }
        }
    )
    + "\n"
)
