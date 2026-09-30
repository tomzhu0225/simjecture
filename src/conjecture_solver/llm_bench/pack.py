"""Prepare and independently grade finite diagnostic coding tasks."""

import hashlib
import importlib.util
import json
import secrets
import shutil
import tarfile
import tempfile
import time
from pathlib import Path

from . import PACK_VERSION, fixtures, reference

HERE = Path(__file__).parent
TASKS = {
    "csv-energy": {"title": "CSV energy accounting", "seconds": 180, "fields": False},
    "rz-diagnostics": {"title": "Recorded RZ diagnostics", "seconds": 900, "fields": True},
}


def catalogue():
    return {
        "pack": "Simjecture Bench",
        "version": PACK_VERSION,
        "experimental": True,
        "tasks": [{"id": name, **value} for name, value in TASKS.items()],
    }


def validate_task(task):
    if task not in TASKS:
        raise ValueError("Unknown benchmark task")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unpack(root, task):
    validate_task(task)
    provenance = json.loads((HERE / "data/provenance.json").read_text())
    archive = HERE / "data/rz-records.tar.xz"
    if digest(archive) != provenance["archive_sha256"]:
        raise ValueError("Benchmark archive checksum mismatch")
    with tarfile.open(archive) as bundle:
        for entry in bundle:
            parts = Path(entry.name).parts
            if (
                len(parts) != 2
                or parts[0] not in ("n64", "n128")
                or not entry.isfile()
                or ".." in parts
            ):
                raise ValueError("Unexpected benchmark archive member")
            if not TASKS[task]["fields"] and not entry.name.endswith(".csv"):
                continue
            path = root / entry.name
            path.parent.mkdir(parents=True, exist_ok=True)
            with bundle.extractfile(entry) as stream:
                path.write_bytes(stream.read())
            if digest(path) != provenance["files"][entry.name]["sha256"]:
                raise ValueError("Benchmark input checksum mismatch")
    return {name: root / name for name in ("n64", "n128")}


def instruction(task):
    validate_task(task)
    text = f"""# {TASKS[task]["title"]} — Simjecture Bench {PACK_VERSION}

This is a finite scientific coding benchmark using recorded aluminium RZ outputs,
not a fresh simulation or proof of the physical radiation mechanism. The suggested
agent budget is {TASKS[task]["seconds"]} seconds; the runner must enforce it.
Use the supplied raw/n64 and raw/n128 inputs without changing them.

Write a self-contained reduce.py exposing reduce_case(directory) -> JSON-serializable
dict. Use standard Python, NumPy, h5py and Matplotlib as needed. It will be reexecuted
on both supplied cases and three numerical holdouts with different energies, clocks,
group counts and (for RZ) covered blocks. Holdouts are not physical evidence.

CSV definitions: radiation_boundary.csv contains per-group per-step increments in
escaped_energy_erg. Sum these once and multiply erg by 1e-7 for joules. For cumulative
radiation, sum groups at each recorded time_s, cumulatively sum increments and prepend
(0,0); do not replace that clock with HDF5 times. In operator_budget.csv, pair the
radiation_before and radiation_after rows in their recorded order with equal time_s.
Sum BEFORE minus AFTER for kinetic_erg + magnetic_erg + internal_erg, once each;
ignore unrelated stage tags. No empty or unpaired stages may silently become zero.
Return E_rad_total_J, radiation_operator_loss_J, radiation_relative_difference
(abs(total-loss)/max(abs(total),1e-12)). Operator agreement is not whole-domain closure.

Write result.json as {{"cases":{{"n64":{{...}},"n128":{{...}}}}}} and nonempty FINDINGS.md
with definitions, units, input provenance and limitations. Findings existence is
checked; prose scientific accuracy is not automatically certified.
Keep PROGRESS.md before any handoff. Continue after a handoff only with the same task,
remaining deadline and generic reminder to read PROGRESS.md; no operator solution hints.
Do not inspect verifier/oracle code or use it as your submitted implementation.
"""
    if task == "rz-diagnostics":
        text += """
RZ definitions: visit only node type 1 leaves. Field shape is [block,dummy,axial,r];
dummy has size one. bounding box coordinates are in cm. Cell centres and volume
are r=rlo+(i+0.5)*dr and 2*pi*r*dr*dz. Density is g/cm^3 and velocity cm/s.
Integrate inward kinetic energy 0.5*rho*max(-velx,0)^2 over the full box.
Total kinetic uses all three velocity components and both signs. Magnetic energy
is 0.5*(magx^2+magy^2+magz^2) in this instrument's normalization; internal energy
is rho*eint, already including radiation. Integrated erg become J by 1e-7.
Tracer r50: sort cell-centre radii, linearly interpolate half of cumulative
rho*line*volume mass on these centres; cm become mm by x10.
HDF5 time is seconds. Reference time is the first maximum inward kinetic sample.
Compression bounds are first/last sample times with r50 <= 1.3*min(r50).
Interpolate cumulative radiation on its own clock to subtract window endpoints.
Stored-energy change is FINAL minus INITIAL over the FULL HDF5 span (total kinetic
+ magnetic + internal), not over the compression window.

Also return t_ref_ns, compression_bounds_ns, K_in_peak_J, E_rad_after_ref_J,
E_rad_compression_J, delta_stored_J, mass_relative_drift (final-initial)/initial,
broadband_ratio=E_rad_total_J/K_in_peak_J, compression_ratio=E_rad_compression_J/K_in_peak_J,
compression_exceeds_peak, whole_domain_closure_established=false, mechanism_proven=false.
The last two flags describe missing physical channels, not arithmetic success.
Add relative_grid_differences to result.json for K_in_peak_J, E_rad_total_J and
E_rad_compression_J, using abs(n128-n64)/max(abs(n128),1e-12).
Report compression sample counts and finite claim outcome in FINDINGS.md;
fewer than three samples would disqualify the physical window comparison.

Write plot-data.json as {"cases":{"n64":{...},"n128":{...}}}, containing arrays:
time_s, inward_kinetic_J, stored_energy_J, tracer_r50_mm on the HDF5 clock;
radiation_time_s, cumulative_radiation_J on the cumulative radiation clock.
These quantities are independently checked. The host renders canonical plots from
verified data after grading. Any additional agent PNG is unscored; image existence
does not prove a chart is correct. Two grids show sensitivity, not convergence.
"""
    return text


def prepare(task, output):
    validate_task(task)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    unpack(output / "raw", task)
    (output / "TASK.md").write_text(instruction(task))
    (output / "PROGRESS.md").write_text("# Progress\n\nNot started.\n")
    (output / "benchmark.json").write_text(
        json.dumps(
            {
                "pack": "Simjecture Bench",
                "version": PACK_VERSION,
                "task": task,
                "suggested_wall_seconds": TASKS[task]["seconds"],
                "continuation_policy": "same contract; remaining deadline; generic reminder only",
                "provenance": json.loads((HERE / "data/provenance.json").read_text())["scope"],
            },
            indent=2,
        )
        + "\n"
    )
    return {
        "task": task,
        "version": PACK_VERSION,
        "path": str(output.resolve()),
        "instruction": str((output / "TASK.md").resolve()),
    }


def _read_json(path):
    if path.is_symlink() or path.stat().st_size > 4_000_000:
        raise ValueError("Submission must be a bounded regular JSON file")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def _run_candidate(work, backend, timeout):
    from ..mvp_agent import BubblewrapSandbox, MVPAgentConfig

    sandbox = BubblewrapSandbox(
        work,
        MVPAgentConfig(
            execution_backend=backend,
            max_command_seconds=timeout,
            max_tool_output_chars=2000,
            max_memory_bytes=3 * 1024**3,
        ),
    )
    return sandbox.run_python(
        ("runner.py", "reduce.py", "cases.json", "actual.json"), timeout_seconds=timeout
    )


def grade(
    task, submission, *, backend="bubblewrap", timeout=120, metadata=None, _candidate_executor=None
):
    """Trusted referee stays outside submitted-code execution and owns comparisons."""
    validate_task(task)
    if TASKS[task]["fields"] and importlib.util.find_spec("h5py") is None:
        raise ValueError("RZ grading requires h5py; install simjecture[flash-demo] or [workspace]")
    if _candidate_executor is None:
        from ..execution import require_execution_backend

        require_execution_backend(backend)
    submission = Path(submission).resolve()
    checks, error = [], None
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="simjecture-bench-") as temporary:
        root = Path(temporary)
        expected_cases = unpack(root / "original", task)
        protected = {
            str(p.relative_to(root / "original")): digest(p)
            for p in (root / "original").rglob("*")
            if p.is_file()
        }
        intact = all(
            (submission / "raw" / name).is_file()
            and not (submission / "raw" / name).is_symlink()
            and digest(submission / "raw" / name) == checksum
            for name, checksum in protected.items()
        )
        holdouts = fixtures.create(root / "holdouts", task, secrets.randbits(64))
        function = reference.csv_result if task == "csv-energy" else reference.rz_result
        expected = {name: function(path) for name, path in (expected_cases | holdouts).items()}
        work = root / "candidate"
        work.mkdir()
        manifest = {}
        for name, path in (expected_cases | holdouts).items():
            shutil.copytree(path, work / "inputs" / name)
            manifest[name] = f"inputs/{name}"
        (work / "cases.json").write_text(json.dumps(manifest))
        shutil.copyfile(HERE / "candidate_runner.py", work / "runner.py")
        reducer = submission / "reduce.py"
        try:
            if reducer.is_symlink() or not reducer.is_file() or reducer.stat().st_size > 1_000_000:
                raise ValueError("Missing bounded, self-contained reduce.py")
            shutil.copyfile(reducer, work / "reduce.py")
            result = (_candidate_executor or _run_candidate)(work, backend, timeout)
            if result.returncode != 0 or result.timed_out or result.workspace_exceeded:
                raise ValueError(f"Reducer failed: {result.stderr[-1000:]}")
            actual = _read_json(work / "actual.json")
        except (ValueError, OSError, RuntimeError) as failure:
            actual, error = {}, str(failure)[:1500]
        for name, (target, _curves) in expected.items():
            checks += reference.comparisons(actual.get(name), target, f"{name}:")
        try:
            saved = _read_json(submission / "result.json")
        except (OSError, ValueError):
            saved = {}
        if not isinstance(saved.get("cases"), dict):
            saved["cases"] = {}
        for name in expected_cases:
            checks += reference.comparisons(
                saved.get("cases", {}).get(name), expected[name][0], f"saved:{name}:"
            )
        if task == "rz-diagnostics":
            diffs = {
                key: abs(expected["n128"][0][key] - expected["n64"][0][key])
                / max(abs(expected["n128"][0][key]), 1e-12)
                for key in ("K_in_peak_J", "E_rad_total_J", "E_rad_compression_J")
            }
            checks += reference.comparisons(saved.get("relative_grid_differences"), diffs, "grid:")
            try:
                plot = _read_json(submission / "plot-data.json")
            except (OSError, ValueError):
                plot = {}
            if not isinstance(plot.get("cases"), dict):
                plot["cases"] = {}
            for name in expected_cases:
                checks += reference.comparisons(
                    plot.get("cases", {}).get(name), expected[name][1], f"plot:{name}:"
                )
        findings = submission / "FINDINGS.md"
        delivered = (
            findings.is_file()
            and not findings.is_symlink()
            and 0 < findings.stat().st_size < 1_000_000
            and bool(findings.read_text().strip())
        )
        report = {
            "schema_version": "0.1.0",
            "pack_version": PACK_VERSION,
            "task": task,
            "passed": intact and delivered and all(c["passed"] for c in checks),
            "checks": checks,
            "intact_inputs": intact,
            "findings_present": delivered,
            "error": error,
            "grading_wall_seconds": time.monotonic() - start,
            "execution_backend": backend,
            "comparison_scope": "finite numerical contract",
            "scientific_claim_approved": False,
            "trial": {
                key: (metadata or {}).get(key)
                for key in (
                    "model",
                    "agent",
                    "settings",
                    "wall_seconds",
                    "input_tokens",
                    "output_tokens",
                    "cached_input_tokens",
                    "reasoning_output_tokens",
                    "requests_without_usage",
                )
            },
            "usage_note": "Null means unknown; manual metadata is not provider billing evidence.",
        }
        if task == "rz-diagnostics" and report["passed"]:
            report["verified_plot_data"] = {name: expected[name][1] for name in expected_cases}
    return report


def render_verified_plots(task, submission, report, output):
    if task != "rz-diagnostics" or not report["passed"]:
        return
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    curves = report["verified_plot_data"]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for name, data in curves.items():
        axes[0].plot([t * 1e9 for t in data["time_s"]], data["inward_kinetic_J"], label=name)
        axes[1].plot(
            [t * 1e9 for t in data["radiation_time_s"]], data["cumulative_radiation_J"], label=name
        )
    for axis, title in zip(
        axes, ("Inward kinetic energy", "Escaped broadband radiation"), strict=True
    ):
        axis.set(xlabel="Time (ns)", ylabel="Energy (J)", title=title)
        axis.legend()
    fig.tight_layout()
    fig.savefig(output / "verified-energies.png", dpi=150)
    plt.close(fig)


def configure_parser(parser):
    commands = parser.add_subparsers(dest="bench_command", required=True)
    commands.add_parser("list")
    for command in ("prepare", "grade", "export"):
        sub = commands.add_parser(command)
        sub.add_argument("task", choices=tuple(TASKS))
        sub.add_argument("--output", type=Path, required=True)
        if command == "grade":
            sub.add_argument("--submission", type=Path, required=True)
            sub.add_argument(
                "--execution-backend",
                choices=("bubblewrap", "proot-cooperative"),
                default="bubblewrap",
            )
            sub.add_argument("--model")
            sub.add_argument("--agent")
    parser.set_defaults(handler=cli)


def cli(args):
    try:
        if args.bench_command == "list":
            result = catalogue()
        elif args.bench_command == "prepare":
            result = prepare(args.task, args.output)
        elif args.bench_command == "export":
            from .exporter import export

            result = export(args.task, args.output)
        else:
            result = grade(
                args.task,
                args.submission,
                backend=args.execution_backend,
                metadata={"model": args.model, "agent": args.agent},
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n")
            render_verified_plots(
                args.task, args.submission, result, args.output.parent / "verified-plots"
            )
        print(json.dumps({k: v for k, v in result.items() if k != "verified_plot_data"}, indent=2))
        return int(args.bench_command == "grade" and not result["passed"])
    except (ValueError, OSError, RuntimeError) as error:
        print(str(error))
        return 2
