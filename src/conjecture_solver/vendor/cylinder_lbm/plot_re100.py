"""Figures and comparison table for the Re=100 validation (reads results/<case>/*)."""
import os
import sys
import json
import glob

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

OUT = sys.argv[1] if len(sys.argv) > 1 else "results"

# Literature, 2D, Re = 100 (Qu, Norberg, Davidson, Peng, Wang, J. Fluids Struct. 39 (2013) 347-370,
# their Table 1; CL' is the rms lift about zero; Lc is measured from the rear surface of the
# cylinder, i.e. the closure point lies at x = 0.5 + Lc from the axis)
LIT = [
    ("Park et al. 1998",              0.165,  1.33,  0.235, 1.42),
    ("Kravchenko & Moin 1998",        0.164,  1.32,  0.222, 1.45),
    ("Shi et al. 2004",               0.1640, 1.318, None,  None),
    ("Mittal 2005",                   0.1644, 1.322, 0.226, None),
    ("Stålberg et al. 2006",     0.166,  1.32,  0.233, None),
    ("Posdziech & Grundmann 2007",    0.1644, 1.325, 0.228, None),
    ("Li et al. 2009",                0.164,  1.336, None,  None),
    ("Qu et al. 2013 (H=120)",        0.1648, 1.319, 0.225, 1.41),
]
QU_H = [(200, 0.1647, 1.310, 0.2151), (120, 0.1650, 1.315, 0.2163),
        (100, 0.1652, 1.317, 0.2169), (60, 0.1660, 1.326, 0.2191)]


def load(name):
    d = os.path.join(OUT, name)
    if not os.path.exists(os.path.join(d, "summary.json")):
        return None
    with open(os.path.join(d, "summary.json")) as fh:
        s = json.load(fh)
    return d, s


def fig_timeseries(d, s):
    f = np.load(os.path.join(d, "forces.npz"))
    cd, cl, u, nd = f["cd"].astype(float), f["cl"].astype(float), float(f["u"]), int(f["nd"])
    t = (np.arange(len(cd)) + 1) * u / nd
    fig, ax = plt.subplots(2, 2, figsize=(12, 7))
    ax[0, 0].plot(t, cl, lw=0.5)
    ax[0, 0].set(xlabel="t* = tU/D", ylabel="C_L", title="(a) lift history, full run")
    ax[0, 1].plot(t, cd, lw=0.5, color="C1")
    ax[0, 1].set(xlabel="t* = tU/D", ylabel="C_D", title="(b) drag history, full run",
                 ylim=(1.2, 1.6))
    T = s["T_steps"] * u / nd
    t1 = t[-1]
    m = t > t1 - 5 * T
    ax[1, 0].plot(t[m], cl[m], color="C0")
    ax[1, 0].plot(t[m], cd[m] - np.mean(cd[m]), color="C1", lw=1)
    ax[1, 0].set(xlabel="t* = tU/D", title="(c) last 5 cycles: C_L (blue), C_D - mean (orange)")
    ax[1, 0].grid(alpha=0.3)
    n = len(cl)
    seg = cl[n // 2:] - np.mean(cl[n // 2:])
    seg = seg * np.hanning(len(seg))
    sp = np.abs(np.fft.rfft(seg, n=8 * len(seg)))
    fr = np.fft.rfftfreq(8 * len(seg), d=u / nd)
    ax[1, 1].semilogy(fr, sp / sp.max())
    ax[1, 1].axvspan(0.164, 0.166, color="g", alpha=0.25, label="literature St 0.164-0.166")
    ax[1, 1].axvline(s["St"], color="r", ls="--", label=f"this run St = {s['St']:.4f}")
    ax[1, 1].set(xlim=(0, 0.5), ylim=(1e-5, 2), xlabel="St", title="(d) C_L spectrum")
    ax[1, 1].legend()
    fig.suptitle(f"Re = 100, nd = {nd}: C_D = {s['cd_mean']:.4f}, "
                 f"C_L' = {s['cl_rms0']:.4f}, St = {s['St']:.4f}")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig1_timeseries.png"), dpi=140)
    plt.close(fig)


def pick_events(cl):
    """Indices (in the last 16 snapshots) of C_L max, down-crossing, min, up-crossing."""
    n = len(cl)
    w = np.arange(n - 16, n)
    c = cl[w]
    mid = 0.5 * (c.max() + c.min())
    d = np.roll(c, -1) - np.roll(c, 1)
    imax, imin = int(np.argmax(c)), int(np.argmin(c))
    dn = np.where(d < 0, np.abs(c - mid), np.inf)
    up = np.where(d > 0, np.abs(c - mid), np.inf)
    return [w[imax], w[int(np.argmin(dn))], w[imin], w[int(np.argmin(up))]]


def fig_phases(d, s):
    p = os.path.join(d, "snaps.npz")
    if not os.path.exists(p):
        return
    z = np.load(p)
    om, rho, xs, ys = z["om"], z["rho"], z["xs"], z["ys"]
    u, nd, cl = float(z["u"]), int(z["nd"]), z["cl"]
    ev = pick_events(cl)
    names = ["C_L max", "C_L = mean, falling", "C_L min", "C_L = mean, rising"]
    fig, ax = plt.subplots(2, 4, figsize=(18, 6.6))
    ext = [xs[0], xs[-1], ys[0], ys[-1]]
    for j, (i, nm) in enumerate(zip(ev, names)):
        a = ax[0, j]
        im = a.imshow(om[i].T, origin="lower", extent=ext, cmap="RdBu_r", vmin=-3, vmax=3,
                      interpolation="bilinear")
        a.add_patch(Circle((0, 0), 0.5, fc="0.7", ec="k", lw=0.8))
        a.set(xlim=(-2, 14), ylim=(-3, 3), title=f"{nm}   C_L = {cl[i]:+.3f}")
        if j == 0:
            a.set_ylabel("y/D  (vorticity  ωD/U)")
        cp = ((rho[i] - 1.0) / 3.0) / (0.5 * u * u)
        b = ax[1, j]
        im2 = b.imshow(cp.T, origin="lower", extent=ext, cmap="PRGn", vmin=-1.0, vmax=1.0,
                       interpolation="bilinear")
        b.add_patch(Circle((0, 0), 0.5, fc="0.7", ec="k", lw=0.8))
        b.set(xlim=(-2, 14), ylim=(-3, 3), xlabel="x/D")
        if j == 0:
            b.set_ylabel("y/D  (pressure  C_p)")
    fig.colorbar(im, ax=ax[0, :], fraction=0.012, pad=0.01, label="ωD/U")
    fig.colorbar(im2, ax=ax[1, :], fraction=0.012, pad=0.01, label="C_p = (p - p_inf)/(0.5 U^2)")
    fig.suptitle("Re = 100, typical instants of one shedding cycle (flow is left to right)")
    fig.savefig(os.path.join(OUT, "fig2_phases.png"), dpi=130)
    plt.close(fig)
    # one more figure: 8 evenly spaced phases of the vorticity, last cycle
    fig, ax = plt.subplots(4, 2, figsize=(11, 11))
    idx = np.arange(len(cl) - 16, len(cl), 2)
    for a, i in zip(ax.ravel(), idx):
        a.imshow(om[i].T, origin="lower", extent=ext, cmap="RdBu_r", vmin=-3, vmax=3,
                 interpolation="bilinear")
        a.add_patch(Circle((0, 0), 0.5, fc="0.7", ec="k", lw=0.8))
        a.set(xlim=(-2, 14), ylim=(-3, 3), title=f"phase {(i - idx[0]) / 16:.3f} T    C_L = {cl[i]:+.3f}")
    fig.suptitle("Vorticity ωD/U over one shedding period (8 equally spaced phases)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig2b_vorticity_8phases.png"), dpi=110)
    plt.close(fig)


def fig_mean(d, s):
    z = np.load(os.path.join(d, "mean.npz"))
    xs, ys, ux, uy = z["xs"], z["ys"], z["ux"], z["uy"]
    u = float(z["u"])
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.8), gridspec_kw=dict(width_ratios=[1.2, 1]))
    sx = (xs > -1.5) & (xs < 7)
    sy = (ys > -2.5) & (ys < 2.5)
    X, Y = np.meshgrid(xs[sx], ys[sy], indexing="ij")
    im = ax[0].pcolormesh(xs[sx], ys[sy], (ux[np.ix_(sx, sy)] / u).T, cmap="RdBu_r",
                          vmin=-1.2, vmax=1.2, shading="auto")
    ax[0].streamplot(xs[sx], ys[sy], (ux[np.ix_(sx, sy)] / u).T, (uy[np.ix_(sx, sy)] / u).T,
                     color="k", linewidth=0.6, density=1.6)
    ax[0].add_patch(Circle((0, 0), 0.5, fc="0.7", ec="k"))
    ax[0].set(xlabel="x/D", ylabel="y/D", title="time-mean u/U with streamlines (3 cycles)",
              aspect="equal", xlim=(-1.5, 7), ylim=(-2.5, 2.5))
    fig.colorbar(im, ax=ax[0], fraction=0.04, label="u/U")
    xl, cm = z["x_line"], z["centerline"] / u
    ax[1].plot(xl, cm, "C0", label="this run, y = 0")
    ax[1].axhline(0, color="k", lw=0.5)
    ax[1].axvspan(1.91, 1.95, color="g", alpha=0.3, label="literature closure x = 0.5 + L_c (L_c = 1.41-1.45)")
    if np.isfinite(s["Lc_over_D"]):
        ax[1].axvline(s["Lc_over_D"], color="r", ls="--",
                      label=f"this run: x = {s['Lc_over_D']:.3f} D  (L_c = {s['Lc_over_D'] - 0.5:.3f})")
    ax[1].set(xlim=(0, 6), ylim=(-0.4, 1.1), xlabel="x/D (from the axis)", ylabel="mean u/U",
              title="mean centerline velocity and wake closure")
    ax[1].legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig3_mean_wake.png"), dpi=140)
    plt.close(fig)


def fig_conv(rows):
    grid = [r for r in rows if r["name"] in ("nd32", "base", "nd64", "nd96", "nd128")]
    dom = [r for r in rows if r["name"] in ("H10", "base", "H40", "H80")]
    grid.sort(key=lambda r: r["nd"])
    dom.sort(key=lambda r: r["H"])
    keys = [("St", "St", 0.164, 0.166, 1), ("cd_mean", "C_D", 1.318, 1.336, 2),
            ("cl_rms0", "C_L' (rms)", 0.222, 0.235, 3)]
    fig, ax = plt.subplots(2, 3, figsize=(15, 8))
    for j, (k, lab, lo, hi, qi) in enumerate(keys):
        a = ax[0, j]
        a.plot([1.0 / r["nd"] for r in grid], [r[k] for r in grid], "o-", label="this solver (H = 20 D)")
        a.axhspan(lo, hi, color="g", alpha=0.25, label="literature spread (7 studies)")
        a.set(xlabel="1/nd", ylabel=lab, title=f"grid refinement: {lab}")
        a.legend(fontsize=8)
        b = ax[1, j]
        b.plot([1.0 / r["H"] for r in dom], [r[k] for r in dom], "o-", label="this solver (nd = 48)")
        b.plot([1.0 / q[0] for q in QU_H], [q[qi] for q in QU_H], "s--", color="gray",
               label="Qu et al. 2013 (H = 60-200)")
        b.axhspan(lo, hi, color="g", alpha=0.25)
        b.set(xlabel="blockage 1/H", ylabel=lab, title=f"domain height: {lab}")
        b.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig4_convergence.png"), dpi=130)
    plt.close(fig)


def main():
    base = load("base")
    if base is None:
        print("no base case")
        return
    d, s = base
    fig_timeseries(d, s)
    fig_phases(d, s)
    fig_mean(d, s)
    rows = []
    for p in sorted(glob.glob(os.path.join(OUT, "*", "summary.json"))):
        with open(p) as fh:
            r = json.load(fh)
        if r.get("ok") and r["name"] != "custom":
            rows.append(r)
    if len(rows) > 1:
        fig_conv(rows)
    lines = ["| case | nd | H | blockage | cycles | St | Cd_mean | Cd_rms | Cl_rms (about 0) | Cl_amp | Lc/D (from rear surface) | amp drift |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["H"] != 20, r["nd"], r["H"])):
        lines.append(f"| {r['name']} | {r['nd']} | {r['H']:g} | {r['blockage']*100:.2f}% | {r['n_cycles']} | "
                     f"{r['St']:.4f} | {r['cd_mean']:.4f} | {r['cd_rms']:.4f} | {r['cl_rms0']:.4f} | "
                     f"{r['cl_amp']:.4f} | {r['Lc_over_D'] - 0.5:.3f} | {r['cl_amp_drift']*100:+.2f}% |")
    lines += ["", "| literature (2D, Re=100) | St | Cd | Cl' rms | Lc/D |", "|---|---|---|---|---|"]
    for n_, st_, cd_, cl_, lc_ in LIT:
        f = lambda v, p: "-" if v is None else f"{v:.{p}f}"
        lines.append(f"| {n_} | {f(st_, 4)} | {f(cd_, 3)} | {f(cl_, 3)} | {f(lc_, 2)} |")
    with open(os.path.join(OUT, "comparison.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
