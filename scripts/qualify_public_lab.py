"""Real commissioning through the same general tools used by the hosted agent."""

import argparse
import json
from pathlib import Path

from conjecture_solver.public.lab import HostedLab
from conjecture_solver.public.store import Store
from conjecture_solver.research_service import ResearchService

ROOT = Path("/srv/simjecture-public/general-qualification-20261006")
FLASH = Path("/opt/simjecture/reconnection-20261002/FLASH4.8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-gpu", action="store_true")
    args = parser.parse_args()
    ROOT.mkdir(exist_ok=True)
    (ROOT / "settings.json").write_text(
        json.dumps(
            {
                "executor_socket": "/run/simjecture-executor/lab.sock",
                "executor_qualified": True,
                "tools_registry": "/opt/simjecture-public/tools/registry.json",
            }
        )
    )
    store = Store(ROOT)
    _, visitor = store.create_visitor("operator-general-qualification", max_per_day=100)
    project = store.create_project(visitor["id"], "General execution commissioning")
    job = store.enqueue(
        visitor["id"],
        "interactive",
        "General executor qualification",
        project=project["id"],
        privileged=True,
        wall_seconds=900,
        limits={"interactive": None, "research": None},
    )
    store.claim()
    service = ResearchService.create(
        ROOT / "jobs" / job["id"] / "study",
        "General executor commissioning",
        wall_seconds=900,
        execution_backend="process-cooperative",
        completion_policy="answer",
    )
    lab = HostedLab(store, store.job(job["id"]), service)
    reports = []

    def run(label, command, outputs, inputs=None, timeout=120):
        print("RUN", label, flush=True)
        result = lab.run(command, outputs, inputs, timeout, label)
        reports.append({"label": label, "result": result})
        (ROOT / "report.json").write_text(json.dumps(reports, indent=2) + "\n")
        print(result["status"], label, result.get("metrics", {}).get("seconds"), flush=True)
        if result["status"] != "succeeded":
            raise RuntimeError(result)
        return result

    lab.write(
        "probe.py",
        """import os,json
from pathlib import Path
result={"uid":os.getuid()}
for name in ("/srv/simjecture-public/data/provider.json","/root/.ssh/authorized_keys"):
    try: Path(name).read_bytes();result[name]="ALLOWED"
    except PermissionError:result[name]="DENIED"
assert result["uid"]>=60000 and all(v=="DENIED" for k,v in result.items() if k!="uid")
Path("probe.json").write_text(json.dumps(result))
""",
    )
    run("Private-file isolation", "python probe.py", ["probe.json"], ["probe.py"])
    lab.write("tiny.c", '#include <stdio.h>\nint main(){puts("{\\"compiled\\":true}");return 0;}\n')
    run("Compile custom code", "gcc tiny.c -o tiny", ["tiny"], ["tiny.c"])
    run("Reuse compiled executable", "./tiny > compiled.json", ["compiled.json"], ["tiny"])
    entries = json.loads(Path("/opt/simjecture-public/tools/registry.json").read_text())["tools"]
    gpu = next(e for e in entries if e["id"] == "warpx-2d-cuda")
    text = (
        Path(gpu["template"])
        .read_text()
        .replace("{{cells}}", "64")
        .replace("{{steps}}", "40")
        .replace("{{amplitude}}", "0.02")
    )
    lab.write("inputs", text)
    if not args.skip_gpu:
        run(
            "Custom WarpX CUDA inputs",
            "warpx-2d inputs > warpx.log 2>&1",
            ["warpx.log", "reduced/*"],
            ["inputs"],
        )
        assert "CUDA initialized" in (lab.files / "warpx.log").read_text()
    flash = next(e for e in entries if e["id"] == "flash-2d")
    text = (
        Path(flash["template"])
        .read_text()
        .replace("{{cells}}", "64")
        .replace("{{end_time}}", "0.07")
    )
    lab.write("flash.par", text)
    run(
        "Custom FLASH inputs",
        "flash-2d > flash.log 2>&1",
        ["flash.log", "native_hdf5_plt_cnt_*"],
        ["flash.par"],
    )
    command = f"""set -e
simjecture_case_dir=$PWD
mkdir flash-source
for folder in bin source sites lib; do cp -RL {FLASH}/$folder flash-source/; done
chmod -R u+rwX flash-source
cd flash-source
SETUP_SHORTCUTS=$PWD/bin/setup_shortcuts.txt /usr/bin/python3 bin/setup.py \\
magnetoHD/IslandCoalescence -auto -opt -2d +cartesian +ug -nofbs +usm \\
+hdf5typeio -site=UU-DESKTOP-NVML34D -objdir="$simjecture_case_dir/build" \\
> "$simjecture_case_dir/build.log" 2>&1
cd "$simjecture_case_dir/build"
PATH=/opt/simjecture-public/tools/build-bin:$PATH make -j4 >> ../build.log 2>&1
cp flash4 ../reconnection-solver
cp --dereference Simulation_initBlock.F90 ../reconnection-init.F90
"""
    run(
        "Compile FLASH reconnection application",
        command,
        ["build.log", "reconnection-solver", "reconnection-init.F90", "build/setup_call"],
        [],
        timeout=180,
    )
    text = (
        FLASH / "source/Simulation/SimulationMain/magnetoHD/IslandCoalescence/flash.par"
    ).read_text()
    text = (
        text.replace("iProcs = 2", "iProcs = 1")
        .replace("jProcs = 2", "jProcs = 1")
        .replace("iGridSize = 128", "iGridSize = 64")
        .replace("jGridSize = 128", "jGridSize = 64")
        .replace("nend = 100", "nend = 100000")
    )
    lab.write("flash.par", text)
    run(
        "Run FLASH reconnection application",
        "./reconnection-solver > reconnection.log 2>&1",
        ["reconnection.log", "island_coalescence_hdf5_plt_cnt_*"],
        ["reconnection-solver", "flash.par"],
        timeout=180,
    )
    (ROOT / "project.json").write_text(json.dumps({"project": project["id"], "job": job["id"]}))
    store.update(job["id"], status="completed")
    print("All general-execution cases passed", flush=True)


if __name__ == "__main__":
    main()
