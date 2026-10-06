"""Run selected extended-domain Re=100 validation cases on a CUDA GPU."""
import argparse
import json
from pathlib import Path

import warp as wp

from validate_re100 import run_case


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "long_domain_results"
BASE = dict(nd=32, tconv=400, side_sponge_len=8.0,
            out_eq_sponge_len=6.0)
CASES = {
    "H40_L64_Xu8": dict(H=40, L=64, xc=8),
    "H80_L64_Xu8": dict(H=80, L=64, xc=8),
    "H120_L64_Xu8": dict(H=120, L=64, xc=8),
    "H80_L80_Xu40": dict(H=80, L=80, xc=40),
    "H80_L80_Xu40_nd32_t300": dict(H=80, L=80, xc=40, nd=32, tconv=300),
    "H80_L80_Xu40_nd48": dict(H=80, L=80, xc=40, nd=48, tconv=300),
    "H80_L80_Xu40_nd64": dict(H=80, L=80, xc=40, nd=64, tconv=300),
    "H80_L80_Xu40_nd80": dict(H=80, L=80, xc=40, nd=80, tconv=300),
    "H80_L80_Xu40_bare": dict(H=80, L=80, xc=40,
                                 side_sponge_len=0.0, out_eq_sponge_len=0.0),
    "H40_L80_Xu40": dict(H=40, L=80, xc=40),
    "H60_L80_Xu40": dict(H=60, L=80, xc=40),
    "H120_L80_Xu40": dict(H=120, L=80, xc=40),
    "H160_L80_Xu40": dict(H=160, L=80, xc=40),
    "H120_L120_Xu60": dict(H=120, L=120, xc=60),
    "H160_L120_Xu60": dict(H=160, L=120, xc=60),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="+", choices=list(CASES))
    ap.add_argument("--out", type=Path, default=OUT,
                    help="result directory (choose a new directory to rerun existing cases)")
    args = ap.parse_args()
    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    wp.init()
    dev = wp.get_device("cuda:0")
    for name in args.cases:
        target = out / name / "summary.json"
        if target.exists():
            print(f"SKIP {name} (summary exists)", flush=True)
            continue
        spec = BASE | CASES[name]
        print(f"START {name} {spec}", flush=True)
        summary = run_case(name, spec, str(out), dev)
        if summary is None:
            summary = json.loads(target.read_text())
        print(f"DONE {name} St={summary['St']:.6f} Cd={summary['cd_mean']:.6f} "
              f"Cl_rms={summary['cl_rms0']:.6f} "
              f"drift={summary['cl_amp_drift']:.4%}", flush=True)


if __name__ == "__main__":
    main()
