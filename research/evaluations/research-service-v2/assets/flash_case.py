"""Launch the operator-installed FLASH driven-sheet executable; not a scientific verdict."""

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


def parameters(a):
    bc = "periodic" if a.mode else "user"
    outflow = "periodic" if a.mode else "outflow"
    p = dict(
        run_comment="Finite driven-sheet benchmark",
        log_file="flash.log",
        basenm="sheet_",
        UnitSystem="none",
        geometry="cartesian",
        xmin=-1.0,
        xmax=1.0,
        ymin=-1.0,
        ymax=1.0,
        xl_boundary_type=bc,
        xr_boundary_type=bc,
        yl_boundary_type=outflow,
        yr_boundary_type=outflow,
        sim_mode=a.mode,
        sim_amplitude=a.amplitude,
        sim_wavelength=0.5,
        sim_phase=a.phase,
        sim_seed=1e-6,
        gamma=5 / 3,
        eosModeInit="dens_pres",
        eos_singleSpeciesA=1.0,
        eos_singleSpeciesZ=1.0,
        smlrho=1e-12,
        smallp=1e-12,
        smallt=1e-12,
        useHydro=True,
        order=2,
        slopeLimiter="mc",
        LimitedSlopeBeta=1.0,
        charLimiting=True,
        use_avisc=False,
        use_flattening=False,
        use_steepening=False,
        use_upwindTVD=False,
        RiemannSolver="HLLD",
        entropy=False,
        shockDetect=False,
        killdivb=True,
        E_modification=True,
        E_upwind=False,
        energyFix=True,
        ForceHydroLimit=False,
        useDiffuse=True,
        useDiffuseTherm=False,
        useDiffuseSpecies=False,
        useDiffuseComputeDtTherm=False,
        useDiffuseComputeDtVisc=True,
        useDiffuseComputeDtSpecies=False,
        useDiffuseComputeDtMagnetic=True,
        dt_diff_factor=0.8,
        useMagneticResistivity=True,
        resistivitySolver="explicit",
        resistivityForm="parallel",
        resistivity=a.eta,
        useViscosity=True,
        useExplicitViscosity=True,
        visc_whichCoefficientIsConst=2,
        diff_visc_nu=a.nu,
        restart=False,
        nend=100000,
        tmax=a.tmax,
        dr_shortenLastStepBeforeTMax=True,
        cfl=a.cfl,
        dtinit=1e-6,
        dtmin=1e-14,
        dtmax=0.01,
        tstep_change_factor=1.2,
        plotFileNumber=0,
        checkpointFileNumber=0,
        plotFileIntervalTime=a.interval,
        plotfileGridQuantityDP=True,
        plotfileMetadataDP=True,
        checkpointFileIntervalTime=1000.0,
        iGridSize=a.n,
        jGridSize=a.n,
        kGridSize=1,
        iProcs=a.ranks,
        jProcs=1,
        kProcs=1,
    )
    for i, v in enumerate(
        ["dens", "pres", "velx", "vely", "magx", "magy", "magp", "divb", "ener", "eint"], 1
    ):
        p[f"plot_var_{i}"] = v

    def fmt(v):
        if isinstance(v, bool):
            return ".true." if v else ".false."
        return json.dumps(v)

    return "\n".join(f"{k} = {fmt(v)}" for k, v in p.items()) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", type=int, choices=[0, 1, 2], default=0)
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--ranks", type=int, default=2)
    p.add_argument("--amplitude", type=float, default=0.0)
    p.add_argument("--phase", type=float, default=0.0)
    p.add_argument("--eta", type=float, required=True)
    p.add_argument("--nu", type=float, default=0.002)
    p.add_argument("--cfl", type=float, default=0.4)
    p.add_argument("--tmax", type=float, default=2.0)
    p.add_argument("--interval", type=float, default=0.1)
    p.add_argument("--timeout", type=float, default=1200)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    exe = Path(os.environ["FLASH_EXECUTABLE"]).resolve(strict=True)
    a.output.mkdir(parents=True, exist_ok=False)
    par = a.output / "flash.par"
    par.write_text(parameters(a))
    cmd = [os.environ.get("FLASH_MPI_LAUNCHER", "/usr/bin/orterun"), "-np", str(a.ranks), str(exe)]
    env = dict(
        os.environ,
        OMPI_MCA_btl="self,vader",
        OMPI_MCA_pml="ob1",
        OMP_NUM_THREADS="1",
        OMPI_MCA_hwloc_base_binding_policy="none",
    )
    start = time.time()
    with (a.output / "stdout.log").open("w") as out, (a.output / "stderr.log").open("w") as err:
        result = subprocess.run(
            cmd, cwd=a.output, env=env, stdout=out, stderr=err, timeout=a.timeout
        )
    metadata = dict(
        returncode=result.returncode,
        wall_seconds=time.time() - start,
        argv=cmd,
        executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        mpi_binding_policy="none",
        parameters_sha256=hashlib.sha256(par.read_bytes()).hexdigest(),
        parameters={k: str(v) if isinstance(v, Path) else v for k, v in vars(a).items()},
        snapshots=[x.name for x in sorted(a.output.glob("sheet_*hdf5_plt_cnt_*"))],
    )
    (a.output / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
