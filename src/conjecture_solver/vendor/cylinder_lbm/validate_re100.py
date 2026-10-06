"""Re=100 validation driver for cylinder_warp_lbm_solver.py (forward LBM only).

For each case it runs the solver, measures the shedding period from the lift
history, then samples the wake at 16 phases per cycle over 3 cycles. From that
it produces cycle-based Cd/Cl/St statistics, the time-mean wake, the wake closure
length Lc, and (optionally) the full set of snapshots for typical-instant plots.
"""
import os
import sys
import json
import math
import time
import argparse

import numpy as np
import cylinder_warp_lbm_solver as S

CASES = {
    "base":  dict(nd=48,  H=20, L=32, tconv=250, snaps=True),
    "nd32":  dict(nd=32,  H=20, L=32, tconv=250),
    "nd64":  dict(nd=64,  H=20, L=32, tconv=250),
    "nd96":  dict(nd=96,  H=20, L=32, tconv=250, snaps=True),
    "nd128": dict(nd=128, H=20, L=32, tconv=250),
    "H10":   dict(nd=48,  H=10, L=32, tconv=250),
    "H40":   dict(nd=48,  H=40, L=32, tconv=250),
    "H80":   dict(nd=48,  H=80, L=32, tconv=250),
    # sensitivity of the PSM / compressibility / outlet settings at nd = 48
    "d035":  dict(nd=48,  H=20, L=32, tconv=250, delta=0.35),
    "plin":  dict(nd=48,  H=20, L=32, tconv=250, psm="linear"),
    "u03":   dict(nd=48,  H=20, L=32, tconv=250, u=0.03),
    "L48":   dict(nd=48,  H=20, L=48, tconv=250),
    # domain-height / lateral-boundary diagnosis at the cheaper nd = 32 (grid-converged to ~1%)
    "n32H10":     dict(nd=32, H=10,  L=32, tconv=250),
    "n32H40":     dict(nd=32, H=40,  L=32, tconv=250),
    "n32H40L48":  dict(nd=32, H=40,  L=48, tconv=250),
    "n32H20L48":  dict(nd=32, H=20,  L=48, tconv=250),
    "n32H40L48abs8": dict(nd=32, H=40, L=48, tconv=250, side_sponge_len=8.0),
    "n32H20out6": dict(nd=32, H=20, L=32, tconv=250, out_eq_sponge_len=6.0),
    "n32H40out6": dict(nd=32, H=40, L=32, tconv=250, out_eq_sponge_len=6.0),
    "n32H20L48out6": dict(nd=32, H=20, L=48, tconv=250, out_eq_sponge_len=6.0),
    "n32H40L48out6": dict(nd=32, H=40, L=48, tconv=250, out_eq_sponge_len=6.0),
    "n32H20both": dict(nd=32, H=20, L=32, tconv=250, side_sponge_len=2.0, out_eq_sponge_len=6.0),
    "n32H40both": dict(nd=32, H=40, L=32, tconv=250, side_sponge_len=8.0, out_eq_sponge_len=6.0),
    "n32H20L48both": dict(nd=32, H=20, L=48, tconv=250, side_sponge_len=2.0, out_eq_sponge_len=6.0),
    "n32H40L48both": dict(nd=32, H=40, L=48, tconv=250, side_sponge_len=8.0, out_eq_sponge_len=6.0),
    "n48H20both": dict(nd=48, H=20, L=32, tconv=250, side_sponge_len=2.0, out_eq_sponge_len=6.0),
    "n48H40both": dict(nd=48, H=40, L=32, tconv=250, side_sponge_len=8.0, out_eq_sponge_len=6.0),
    "n48H20L48both": dict(nd=48, H=20, L=48, tconv=250, side_sponge_len=2.0, out_eq_sponge_len=6.0),
    "n48H40L48both": dict(nd=48, H=40, L=48, tconv=250, side_sponge_len=8.0, out_eq_sponge_len=6.0),
    "n32H10both": dict(nd=32, H=10, L=32, tconv=250, side_sponge_len=1.0, out_eq_sponge_len=6.0),
    "n48H10both": dict(nd=48, H=10, L=32, tconv=250, side_sponge_len=1.0, out_eq_sponge_len=6.0),
    "n32H80":     dict(nd=32, H=80,  L=32, tconv=250),
    "n32H160":    dict(nd=32, H=160, L=32, tconv=250),
    "n32H20u03":  dict(nd=32, H=20,  L=32, tconv=250, u=0.03),
    "n32H40u03":  dict(nd=32, H=40,  L=32, tconv=250, u=0.03),
    "n32H20per":  dict(nd=32, H=20,  L=32, tconv=250, wall="periodic"),
    "n32H40per":  dict(nd=32, H=40,  L=32, tconv=250, wall="periodic"),
    "n32H20slip": dict(nd=32, H=20,  L=32, tconv=250, wall="slip"),
    "n32H40slip": dict(nd=32, H=40,  L=32, tconv=250, wall="slip"),
    "n32H20abs":  dict(nd=32, H=20, L=32, tconv=250, side_sponge_len=4.0),
    "n32H40abs":  dict(nd=32, H=40, L=32, tconv=250, side_sponge_len=4.0),
    "n32H20abs2": dict(nd=32, H=20, L=32, tconv=250, side_sponge_len=2.0),
    "n32H40abs8": dict(nd=32, H=40, L=32, tconv=250, side_sponge_len=8.0),
    "n48H20abs2": dict(nd=48, H=20, L=32, tconv=250, side_sponge_len=2.0),
    "n48H40abs8": dict(nd=48, H=40, L=32, tconv=250, side_sponge_len=8.0),
}
NSNAP_PER_CYCLE = 16
NSNAP_CYCLES = 3


def upcross(y, thr):
    """Sample positions (fractional) where y crosses thr upwards."""
    s = np.asarray(y, dtype=np.float64) - thr
    i = np.where((s[:-1] < 0.0) & (s[1:] >= 0.0))[0]
    return i + (-s[i]) / (s[i + 1] - s[i])


def cycle_stats(cd, cl, nd, u, ncyc=10):
    """Statistics over the last ncyc complete lift cycles (cd, cl already normalized)."""
    n = len(cl)
    thr = float(np.mean(cl[n // 2:]))
    zc = upcross(cl, thr)
    zc = zc[zc > 0.4 * n]
    if len(zc) < 3:
        return dict(ok=False, n_cycles=0)
    ncyc = min(ncyc, len(zc) - 1)
    zc = zc[-(ncyc + 1):]
    i0, i1 = int(math.ceil(zc[0])), int(math.floor(zc[-1]))
    scd, scl = cd[i0:i1], cl[i0:i1]
    T = (zc[-1] - zc[0]) / ncyc
    amps = []
    for k in range(ncyc):
        a, b = int(math.ceil(zc[k])), int(math.floor(zc[k + 1]))
        seg = cl[a:b]
        amps.append(0.5 * float(seg.max() - seg.min()))
    pers = np.diff(zc)
    return dict(ok=True, n_cycles=int(ncyc), T_steps=float(T), St=float(nd / (u * T)),
                St_period_relstd=float(np.std(pers) / np.mean(pers)),
                cd_mean=float(np.mean(scd)), cd_rms=float(np.std(scd)),
                cd_amp=float(0.5 * (scd.max() - scd.min())),
                cl_mean=float(np.mean(scl)),
                cl_rms0=float(np.sqrt(np.mean(scl ** 2))),
                cl_rms_mean=float(np.std(scl)),
                cl_amp=float(np.mean(amps)), cl_amp_first=float(amps[0]),
                cl_amp_last=float(amps[-1]),
                cl_amp_drift=float(amps[-1] / amps[0] - 1.0),
                t_star_window=[float((i0 + 1) * u / nd), float(i1 * u / nd)])


def centerline(arr, cy):
    j = int(math.floor(cy))
    fr = cy - j
    return (1.0 - fr) * arr[:, j] + fr * arr[:, min(j + 1, arr.shape[1] - 1)]


def wake_closure(ux_c, cfg):
    """Second zero of the mean centerline u (negative -> positive), measured from the axis, in D."""
    nd = cfg["nd"]
    x = np.arange(len(ux_c), dtype=np.float64) - cfg["cx"]
    start = int(np.searchsorted(x, 0.5 * nd + 1.0))
    seg = ux_c[start:]
    neg = np.where(seg < -0.02 * cfg["u"])[0]
    if not len(neg):
        return float("nan"), float("nan"), float("nan")
    k = int(neg[0])
    cr = np.where((seg[k:-1] < 0.0) & (seg[k + 1:] >= 0.0))[0]
    if not len(cr):
        return float("nan"), float("nan"), float("nan")
    k2 = k + int(cr[0])
    xf = x[start + k2] + (-seg[k2]) / (seg[k2 + 1] - seg[k2])
    kmin = int(np.argmin(seg[:k2 + 2]))
    return float(xf / nd), float(seg[kmin] / cfg["u"]), float(x[start + kmin] / nd)


def run_case(name, spec, outdir, device):
    ov = dict(nd=spec["nd"], H=spec["H"], L=spec["L"], tconv=spec["tconv"])
    if "xc" in spec:
        ov["xc"] = spec["xc"]
    if spec.get("ghost"):
        ov["ghost"] = spec["ghost"]
    if spec.get("u"):
        ov["u"] = spec["u"]
    cfg = S.make_config(100.0, override=ov)
    sim = S.CylinderLBM(cfg, device=device, wall=spec.get("wall", "far"), delta=spec.get("delta", 0.5),
                        psm=spec.get("psm", "nt"), side_sponge_len=spec.get("side_sponge_len", 0.0),
                        side_sponge_max=spec.get("side_sponge_max", 0.04),
                        out_eq_sponge_len=spec.get("out_eq_sponge_len", 0.0),
                        out_eq_sponge_max=spec.get("out_eq_sponge_max", 0.04),
                        verbose=True)
    nd, u, steps = cfg["nd"], cfg["u"], cfg["steps"]
    cdir = os.path.join(outdir, name)
    os.makedirs(cdir, exist_ok=True)

    T_est = nd / (u * 0.165)
    rem = int(3.3 * T_est)
    n1 = steps - rem
    if n1 < 10:
        raise ValueError("tconv too short for the snapshot phase")
    t_wall = time.perf_counter()
    g, f1 = sim.run(n1, report_every=max(1, n1 // 10))
    cl1 = f1[:, 1] * sim.qinv
    zc = upcross(cl1, float(np.mean(cl1[len(cl1) // 2:])))
    zc = zc[zc > 0.4 * len(cl1)]
    T_true = float(np.mean(np.diff(zc[-6:]))) if len(zc) >= 3 else T_est
    snap_every = max(1, int(round(T_true / NSNAP_PER_CYCLE)))
    nsnap = NSNAP_PER_CYCLE * NSNAP_CYCLES
    n2 = nsnap * snap_every
    gap = max(0, rem - n2)
    f1b = np.zeros((0, 2))
    if gap > 0:
        g, f1b = sim.run(gap, g=g, t0=n1, report_every=max(1, gap))
    t2 = n1 + gap

    # crop window for stored fields (wake region), subsampled to at most ~48 px per D
    x0, x1 = max(0, int(cfg["cx"] - 4 * nd)), min(cfg["nx"], int(cfg["cx"] + 16 * nd))
    y0, y1 = max(0, int(cfg["cy"] - 4 * nd)), min(cfg["ny"], int(cfg["cy"] + 4 * nd))
    st = max(1, nd // 48)
    keep = bool(spec.get("snaps"))
    store = dict(om=[], ux=[], uy=[], rho=[], k=[])
    mean = None
    clines = []

    def cb(k, gg):
        nonlocal mean
        mac = sim.macro(gg)
        ux, uy, rho = mac[1], mac[2], mac[0]
        clines.append(centerline(ux, cfg["cy"]))
        cux, cuy, crho = (a[x0:x1, y0:y1] for a in (ux, uy, rho))
        om = (np.gradient(cuy, axis=0) - np.gradient(cux, axis=1)) * nd / u
        sl = (slice(None, None, st), slice(None, None, st))
        arrs = [a[sl].astype(np.float32) for a in (om, cux, cuy, crho)]
        if mean is None:
            mean = [np.zeros_like(a, dtype=np.float64) for a in arrs]
        for m, a in zip(mean, arrs):
            m += a
        if keep:
            for key, a in zip(("om", "ux", "uy", "rho"), arrs):
                store[key].append(a)
        store["k"].append(k)

    g, f2 = sim.run(n2, g=g, t0=t2, snap_every=snap_every, snap_cb=cb,
                    report_every=max(1, n2 // 4))
    wall = time.perf_counter() - t_wall

    fall = np.vstack([f1, f1b, f2])
    cd, cl = fall[:, 0] * sim.qinv, fall[:, 1] * sim.qinv
    stats = cycle_stats(cd, cl, nd, u)
    fft = S.analyse_forces(fall, cfg, sim.qinv, frac=0.5)
    cm = np.mean(clines, axis=0)
    # wake_closure returns the x coordinate from the cylinder centre; published
    # Lc is measured from the rear stagnation point, x/D = 0.5.
    Lc, umin, xmin = wake_closure(cm, cfg)
    stats.update(name=name, nd=nd, H=spec["H"], L=spec["L"], xc=cfg["cx"] / nd,
                 Xu=cfg["cx"] / nd, Xd=(cfg["nx"] - cfg["cx"]) / nd,
                 tconv=spec["tconv"],
                 nx=cfg["nx"], ny=cfg["ny"], steps=int(len(fall)), tau0=cfg["tau0"],
                 ghost=cfg["ghost"], n_bl=cfg["n_bl"], blockage=1.0 / spec["H"],
                 side_sponge_len=spec.get("side_sponge_len", 0.0),
                 side_sponge_max=spec.get("side_sponge_max", 0.04),
                 out_eq_sponge_len=spec.get("out_eq_sponge_len", 0.0),
                 out_eq_sponge_max=spec.get("out_eq_sponge_max", 0.04),
                 St_fft_last50=fft["st"], cd_mean_last50=fft["cd_mean"],
                 cl_rms0_last50=fft["cl_rms"],
                 Lc_over_D=Lc, x_closure_over_D=Lc,
                 Lc_rear_over_D=Lc - 0.5,
                 u_min_over_U=umin, x_umin_over_D=xmin,
                 T_est_steps=T_est, T_true_steps=T_true, snap_every=snap_every,
                 wall_s=wall, mlups=len(fall) * cfg["nx"] * cfg["ny"] / wall / 1e6)
    kk = np.array(store["k"])
    fidx = np.clip(t2 + kk - 1, 0, len(cl) - 1)
    stats["cl_at_snaps"] = [float(v) for v in cl[fidx]]
    with open(os.path.join(cdir, "summary.json"), "w") as fh:
        json.dump(stats, fh, indent=1)
    np.savez_compressed(os.path.join(cdir, "forces.npz"), cd=cd.astype(np.float32),
                        cl=cl.astype(np.float32), u=u, nd=nd)
    xs = (np.arange(x0, x1)[::st] - cfg["cx"]) / nd
    ys = (np.arange(y0, y1)[::st] - cfg["cy"]) / nd
    np.savez_compressed(os.path.join(cdir, "mean.npz"), om=(mean[0] / len(kk)).astype(np.float32),
                        ux=(mean[1] / len(kk)).astype(np.float32),
                        uy=(mean[2] / len(kk)).astype(np.float32),
                        rho=(mean[3] / len(kk)).astype(np.float32),
                        xs=xs, ys=ys, centerline=cm,
                        x_line=(np.arange(cfg["nx"]) - cfg["cx"]) / nd, u=u)
    if keep:
        np.savez_compressed(os.path.join(cdir, "snaps.npz"),
                            om=np.array(store["om"]), ux=np.array(store["ux"]),
                            uy=np.array(store["uy"]), rho=np.array(store["rho"]),
                            k=kk, cl=cl[fidx], cd=cd[fidx], xs=xs, ys=ys, u=u, nd=nd)
    print(f"\n=== {name}: nd={nd} H={spec['H']} ===")
    for key in ("St", "cd_mean", "cd_rms", "cl_rms0", "cl_amp", "cl_amp_drift",
                "Lc_over_D", "u_min_over_U", "St_fft_last50", "n_cycles", "mlups", "wall_s"):
        print(f"  {key:>14s} = {stats.get(key)}", flush=True)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="base")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", default="results")
    ap.add_argument("--custom", default=None, help="nd,H,L,tconv[,ghost] for a custom case")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.custom:
        p = a.custom.split(",")
        CASES["custom"] = dict(nd=int(p[0]), H=float(p[1]), L=float(p[2]), tconv=float(p[3]),
                               ghost=p[4] if len(p) > 4 else None, snaps=True)
        a.cases = "custom"
    for name in a.cases.split(","):
        try:
            run_case(name, CASES[name], a.out, a.device)
        except Exception as exc:                       # keep going with the other cases
            import traceback
            traceback.print_exc()
            print(f"CASE {name} FAILED: {exc}", flush=True)


if __name__ == "__main__":
    main()
