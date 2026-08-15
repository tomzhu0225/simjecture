"""One-step WarpX theta-implicit EM interface smoke; never scientific evidence.

Uses a tiny 2D grid so the same program runs under both the multi-dimension
CPU capability and the 2D-only CUDA/openPMD capability.
"""

import json
from pathlib import Path

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
nonlinear_solver = picmi.PicardNonlinearSolver(
    require_convergence=True,
    max_iterations=20,
    relative_tolerance=1.0e-8,
    absolute_tolerance=0.0,
    diagnostic_file="picard_iterations.txt",
    diagnostic_interval="1",
)
evolve_scheme = picmi.ThetaImplicitEMEvolveScheme(
    nonlinear_solver=nonlinear_solver,
    theta=0.5,
)
simulation = picmi.Simulation(
    solver=solver,
    time_step_size=1.0e-12,
    max_steps=1,
    particle_shape=1,
    verbose=1,
    warpx_evolve_scheme=evolve_scheme,
    warpx_random_seed=1,
    warpx_serialize_initial_conditions=True,
    warpx_amrex_the_arena_init_size=256 * 1024 * 1024,
    warpx_used_inputs_file="implicit_used_inputs",
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
        layout=picmi.GriddedLayout(grid=grid, n_macroparticle_per_cell=[1, 1]),
    )

simulation.step()
used_inputs = Path("implicit_used_inputs").read_text()
checks = {
    "completed": True,
    "theta_implicit_native": 'algo.evolve_scheme = "theta_implicit_em"'
    in used_inputs,
    "picard_native": 'implicit_evolve.nonlinear_solver = "picard"' in used_inputs,
    "convergence_required_native": "picard.require_convergence = 1" in used_inputs,
    "scientific_evidence_eligible": False,
}
Path("implicit_capability_smoke.json").write_text(
    json.dumps({"checks": checks}) + "\n"
)
