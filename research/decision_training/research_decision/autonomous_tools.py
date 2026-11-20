"""Fixed tool contract and non-inventive translation of student experiment JSON."""

import math

TOOL_CONTRACT = {
    "tool": "MHD1D",
    "implementation": "full conservative ideal MHD, 1D space/3 vector components; MUSCL/LLF/SSPRK2",
    "worker": "independent-cpu",
    "input_location": "experiments entries; solver must be MHD1D",
    "parameters": {
        "beta": "number in [0.05,10]",
        "angle_deg": "number in [0,60]",
        "amplitude": "deltaB/B0 in [0.0001,0.3]",
        "periods": "positive simulated Alfven crossing periods; choose within the remaining wall budget",
        "cfl": "positive CFL <=0.6; unstable choices fail rather than receive corrections",
    },
    "scale": {
        "mesh": "object with nx: integer or list of integers, each >=16; the model chooses refinement or scans",
        "parallel_resources": "cpus: integer 1..16, memory_mb: integer 128..24576; solver is serial NumPy",
    },
    "initial_conditions": "periodic domain L=1, rho0=|B0|=mu0=1, gamma=5/3, p0=beta/2, transverse sinusoid; seed fixed by physical configuration",
    "observables": "measured wave speed, phase residual, amplitude, conserved quantities, positivity, raw fields",
    "workflow": "propose_experiments in the full advice schema; adapt using actual observations; closeout when sufficient. No code generator or GPT host is available. Non-supported solver requests are rejected without fabricated results.",
    "defaults": "missing beta/angle/amplitude inherit the task; missing CFL=0.25, periods=0.7, CPUs=1 and memory_mb=2048; defaults are recorded as adapter modifications",
}


def _number(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(label + " must be a finite number")
    if not low <= value <= high:
        raise ValueError(label + " outside the declared physical/tool range")
    return value


def translate(experiment, task):
    solver = experiment["solver"].lower().replace(" ", "")
    if solver not in {"mhd1d", "mhd1d/llf", "mhd1d-llf"}:
        raise ValueError("Only the declared MHD1D tool is executable in this autonomous branch")
    params, scale = experiment["parameters"], experiment["scale"]
    base = task["initial_parameter_configuration"]
    defaults = {}

    def parameter(name, default, *aliases):
        for key in (name, *aliases):
            if key in params:
                return params[key]
        defaults[name] = default
        return default

    result = dict(
        beta=_number(parameter("beta", base["beta"]), "beta", .05, 10),
        angle_deg=_number(parameter("angle_deg", base["angle_deg"], "angle"), "angle", 0, 60),
        amplitude=_number(parameter("amplitude", base["deltaB_over_B0"], "deltaB_over_B0"), "amplitude", 1e-4, .3),
        cfl=_number(parameter("cfl", .25, "CFL"), "CFL", 1e-8, .6),
        periods=_number(parameter("periods", .7), "periods", 1e-8, 1e12),
    )
    mesh = scale["mesh"]
    nx = mesh.get("nx", mesh.get("N", mesh.get("cells", params.get("nx"))))
    if nx is None:
        raise ValueError("Choose an explicit mesh.nx integer or refinement list")
    nx = nx if isinstance(nx, list) else [nx]
    if not nx or any(isinstance(n, bool) or not isinstance(n, int) or n < 16 for n in nx):
        raise ValueError("Each mesh must be an integer >=16")
    resources = scale["parallel_resources"]
    cpus = resources.get("cpus", resources.get("cpu_cores", 1))
    memory = resources.get("memory_mb", 2048)
    if "cpus" not in resources and "cpu_cores" not in resources:
        defaults["cpus"] = cpus
    if "memory_mb" not in resources:
        defaults["memory_mb"] = memory
    if isinstance(cpus, bool) or not isinstance(cpus, int) or not 1 <= cpus <= 16:
        raise ValueError("CPU reservation outside independent-cpu capacity")
    if isinstance(memory, bool) or not isinstance(memory, int) or not 128 <= memory <= 24576:
        raise ValueError("Memory reservation outside independent-cpu capacity")
    # Bound from the requested memory, including generous scratch/array space;
    # this is a capacity check, never a forced experimental resolution.
    if max(nx) * 2048 > memory * 1024 * 1024:
        raise ValueError("The requested mesh exceeds the reserved memory capacity")
    result["nx"] = nx
    result["resources"] = dict(cpus=cpus, memory_mb=memory, gpus=0)
    return result, defaults
