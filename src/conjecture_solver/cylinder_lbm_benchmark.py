"""A fresh-simulation task, kept separate from the published diagnostic leaderboard."""


def task():
    return {
        "id": "cylinder-inlet-v1",
        "version": "1.0",
        "title": "Cylinder flow · inlet-distance benchmark",
        "suggested_wall_seconds": 1800,
        "capability": "warp-lbm-cylinder-1.0",
        "prompt": (
            "Prepare an autonomous research benchmark using Cylinder flow / Warp-LBM. "
            "Hypothesis: at Re=100, changing the upstream distance from 8D to 40D "
            "changes mean drag and shedding frequency by no more than 1%. "
            "Use fresh recorded simulations. Hold downstream distance at 40D, full "
            "domain height at 40D, 32 cells across D, lattice speed 0.06, far lateral "
            "boundaries, side sponge 8D, outlet equilibrium sponge 6D, and end time "
            "tU/D=300. Total length must therefore be upstream distance plus 40D. "
            "Compare upstream distances 8D, 20D and 40D. Use the final ten complete "
            "lift cycles and report amplitude/period stability. Test the result's "
            "sensitivity to grid resolution and lattice speed before claiming a "
            "physical difference. Retain configurations, source/runtime hashes, "
            "force histories, field plots and a comparison table. Evaluate percentage "
            "changes relative to the 40D result. If the hypothesis fails, propose "
            "the smallest supported refinement and test it with fresh evidence. "
            "Read the warp-lbm guide and inspect the contributor source when useful. "
            "Earlier validation records are background, not substitute evidence. "
            "Suggested campaign allowance is 30 minutes; measure pilot throughput "
            "and adjust the proposal to this machine's resources. Prepare the editable "
            "brief for review and launch. The benchmark evaluates numerical evidence "
            "and independent review, not the appearance of plots."
        ),
        "scoring": [
            "Fresh successful executions with retained input, source and runtime identities",
            "Matched downstream distance, boundaries, Reynolds number and statistical definitions",
            "Correct hypothesis decision supported by measured force and frequency differences",
            "Grid/Mach-number controls and a freshly tested refinement when needed",
            "Independent review, elapsed time, token usage and inference cost",
        ],
        "ranked_results_available": False,
    }
