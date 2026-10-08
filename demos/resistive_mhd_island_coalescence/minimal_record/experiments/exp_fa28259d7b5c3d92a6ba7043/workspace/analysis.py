#!/usr/bin/env python3
"""Aggregate prospective island-scaling summaries and plot archived FLASH fields."""
import argparse, io, json, math, tarfile
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import t as student_t


def crossing(ts, ys, target):
    ids = np.flatnonzero(ys >= target)
    if not len(ids):
        return None
    i = int(ids[0])
    if i == 0:
        return float(ts[0])
    if ys[i] <= ys[i-1]:
        return None
    f = (target-ys[i-1])/(ys[i]-ys[i-1])
    return float(ts[i-1]+f*(ts[i]-ts[i-1]))


def archive_screen(path, low, high):
    """Recompute central-sheet resolution and A_z topology directly from plots."""
    minimum_fwhm = float("inf")
    maximum_secondary = 0
    with tarfile.open(path, "r:gz") as tf:
        for member in tf.getmembers():
            if "hdf5_plt_cnt_" not in member.name:
                continue
            stream = tf.extractfile(member)
            if stream is None:
                continue
            with h5py.File(io.BytesIO(stream.read()), "r") as h:
                scalars = h["real scalars"][()]
                tm = float(next(r["value"] for r in scalars if r["name"].decode().strip().casefold()=="time"))
                bx, by = np.asarray(h["magx"][0,0],float), np.asarray(h["magy"][0,0],float)
                nx, ny = bx.shape[1], bx.shape[0]
                dx=dy=1.0/nx
                y=-.5+(np.arange(ny)+.5)*dy
                B0=np.zeros_like(by)
                # Use the same guided flux convention to determine whether this
                # saved state lies inside the prospectively fixed flux interval.
                ix=np.argsort(np.abs(-.5+(np.arange(nx)+.5)*dx))[:2]
                from_left=np.cumsum(by,axis=1)*dx-.5*by*dx
                line=from_left[:,ix].mean(axis=1)
                fy=np.argsort(np.abs(y))[:8]
                design=np.column_stack((np.ones(8),y[fy]**2,y[fy]**4))
                psi=float(np.linalg.lstsq(design,line[fy],rcond=None)[0][0])
                if tm == 0:
                    psi0=psi
                flux=psi-psi0
                if not low <= flux <= high:
                    continue
                jz=np.gradient(by,dx,axis=1)-np.gradient(bx,dy,axis=0)
                central=np.flatnonzero(np.abs(y)<=.15)
                current=np.abs(jz[:,nx//2]); peak=int(central[np.argmax(current[central])])
                half=.5*current[peak]; lo_i=hi_i=peak
                while lo_i>0 and current[lo_i-1]>=half: lo_i-=1
                while hi_i<ny-1 and current[hi_i+1]>=half: hi_i+=1
                minimum_fwhm=min(minimum_fwhm, float(hi_i-lo_i+1))
                # A_z(x,0) follows -dA_z/dx=B_y at the central y-row.
                bymid=.5*(by[ny//2-1]+by[ny//2])
                az=-np.concatenate(([0.0],np.cumsum(bymid[:-1]*dx)))
                x=-.5+(np.arange(nx)+.5)*dx
                ids=np.flatnonzero(np.abs(x)<=.22)
                vals=np.convolve(az[ids],np.array([1,2,3,2,1],float)/9,mode="same")
                count=0
                for q in range(1,len(vals)-1):
                    if abs(x[ids[q]])<.04: continue
                    ismax=vals[q]>vals[q-1] and vals[q]>vals[q+1]
                    ismin=vals[q]<vals[q-1] and vals[q]<vals[q+1]
                    if ismax or ismin:
                        rad=max(2,int(round(.03*nx))); a=max(0,q-rad); b=min(len(vals),q+rad+1)
                        local=vals[a:b]
                        prom=vals[q]-float(np.min(local)) if ismax else float(np.max(local))-vals[q]
                        count += int(prom>=.005)
                maximum_secondary=max(maximum_secondary,count)
    return (None if not np.isfinite(minimum_fwhm) else minimum_fwhm), maximum_secondary


def fit(cases, key):
    good = [c for c in cases if c["eligible"] and c["eta_inverse"] is not None]
    if len(good) < 3:
        return {"n": len(good), "defined": False, "reason": "fewer than three eligible cases"}
    x = np.log([c["eta_inverse"] for c in good])
    y = np.log([c[key] for c in good])
    design = np.column_stack((np.ones(len(x)), x))
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    residual = y-design@beta
    df = len(x)-2
    se = math.sqrt(float(residual@residual/df) / float(np.sum((x-x.mean())**2)))
    crit = float(student_t.ppf(0.975, df))
    grid = np.linspace(float(x.min()), float(x.max()), 80)
    sigma2 = float(residual@residual/df)
    mean_se = np.sqrt(sigma2*(1.0/len(x)+(grid-float(x.mean()))**2/float(np.sum((x-x.mean())**2))))
    means = beta[0]+beta[1]*grid
    return {"n": len(good), "p": float(beta[1]), "ci95": [float(beta[1]-crit*se), float(beta[1]+crit*se)],
            "intercept": float(beta[0]), "mean_fit_logS": grid.tolist(), "mean_fit_logR": means.tolist(),
            "mean_fit_ci95_logR": [ (means-crit*mean_se).tolist(), (means+crit*mean_se).tolist() ],
            "r_squared": float(1-(residual@residual)/np.sum((y-y.mean())**2)),
            "max_abs_log_residual": float(np.max(np.abs(residual))), "df": df}


def load_case(summary_path, archive_path):
    s = json.loads(Path(summary_path).read_text())
    m = s["metrics"]
    ts = np.array([r["time"] for r in s["timeseries"]], dtype=float)
    fluxes = {"by": np.array([r["reconnected_flux_from_by"] for r in s["timeseries"]], dtype=float),
              "bx": np.array([r["reconnected_flux_from_bx"] for r in s["timeseries"]], dtype=float)}
    rates = []
    for f in fluxes.values():
        lo, hi = crossing(ts, f, m["flux_low"]), crossing(ts, f, m["flux_high"])
        if lo is None or hi is None or hi <= lo:
            rates.append(None)
        else:
            rates.append((m["flux_high"]-m["flux_low"])/(hi-lo)/(m["B_up"]**2/math.sqrt(m["rho_up"])))
    vals = [v for v in rates if v is not None]
    rmid = float(np.mean(vals)) if len(vals) == 2 else None
    rlo, rhi = (float(min(vals)), float(max(vals))) if len(vals) == 2 else (None, None)
    checks = s["checks"]
    reached = bool(checks.get("flux_window_reached"))
    resolved = bool(checks.get("nominal_spatial_resolution"))
    fwhm, secondary = archive_screen(archive_path,m["flux_low"],m["flux_high"])
    preplasmoid = secondary == 0
    resolved = resolved and fwhm is not None and fwhm >= 4.0
    finite = all(v is not None and np.isfinite(v) for v in vals)
    eligible = reached and resolved and preplasmoid and finite
    return {"id": s.get("experiment_id", Path(summary_path).parent.name), "eta": s["realized"]["eta"],
            "family": s["realized"].get("resolution_family", "base"),
            "eta_inverse": m["nominal_eta_inverse"], "nx": s["realized"]["nx"], "ny": s["realized"]["ny"],
            "rate": rmid, "rate_path_min": rlo, "rate_path_max": rhi,
            "eligible": eligible, "reached_window": reached, "resolved": resolved,
            "preplasmoid": preplasmoid, "resolution_cells_SP": m["nominal_sp_sheet_width_cells"],
            "measured_current_fwhm_cells": fwhm,
            "secondary_extrema_count_recomputed": secondary,
            "archive": str(archive_path), "summary": str(summary_path), "raw": s}


def draw_field(case, outdir):
    target = 0.03
    s = case["raw"]
    flux = np.array([r["reconnected_flux_from_by"] for r in s["timeseries"]])
    times = np.array([r["time"] for r in s["timeseries"]])
    tmid = crossing(times, flux, target)
    if tmid is None:
        tmid = float(times[-1])
    selected = None
    with tarfile.open(case["archive"], "r:gz") as tf:
        for member in tf.getmembers():
            if "hdf5_plt_cnt_" not in member.name:
                continue
            stream = tf.extractfile(member)
            if stream is None:
                continue
            content = stream.read()
            with h5py.File(io.BytesIO(content), "r") as h:
                row = h["real scalars"][()]
                tm = float(next(r["value"] for r in row if r["name"].decode().strip().casefold() == "time"))
                if selected is None or abs(tm-tmid) < selected[0]:
                    fields = {k: np.asarray(h[k][0, 0], dtype=float) for k in ("magx", "magy")}
                    selected = (abs(tm-tmid), tm, fields)
    if selected is None:
        return None
    _, tm, f = selected
    bx, by = f["magx"], f["magy"]
    ny, nx = bx.shape
    x = np.linspace(-0.5, 0.5, nx, endpoint=False)+0.5/nx
    y = np.linspace(-0.5, 0.5, ny, endpoint=False)+0.5/ny
    jz = np.gradient(by, 1/nx, axis=1)-np.gradient(bx, 1/ny, axis=0)
    az = np.zeros_like(bx)
    az[1:] = np.cumsum(0.5*(bx[:-1]+bx[1:])*(1/ny), axis=0)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), constrained_layout=True)
    im = axes[0].pcolormesh(x, y, np.hypot(bx, by), shading="auto", cmap="viridis")
    axes[0].contour(x, y, az, levels=18, colors="white", linewidths=.45, alpha=.85)
    axes[0].set_title(r"$|B|$ and $A_z$ contours")
    fig.colorbar(im, ax=axes[0], label="normalized magnetic field")
    im2 = axes[1].pcolormesh(x, y, jz, shading="auto", cmap="RdBu_r", vmin=-np.max(np.abs(jz)), vmax=np.max(np.abs(jz)))
    axes[1].set_title(r"$J_z=\partial_x B_y-\partial_y B_x$")
    fig.colorbar(im2, ax=axes[1], label="normalized current density")
    for ax in axes:
        ax.set(xlabel="x", ylabel="y", xlim=(-.5,.5), ylim=(-.5,.5), aspect="equal")
    fig.suptitle(f"{case['id']} at t={tm:.4g}; nearest to reconnected flux 0.03")
    path = Path(outdir)/f"field_current_{case['id']}.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return str(path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--case", action="append", nargs=2, metavar=("SUMMARY", "RAW_TAR"), required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    outdir = Path(a.outdir); outdir.mkdir(parents=True, exist_ok=True)
    cases = [load_case(*pair) for pair in a.case]
    base = [c for c in cases if c["family"] == "base"]
    refined = [c for c in cases if c["family"] == "refined"]
    fb, fr = fit(base, "rate"), fit(refined, "rate")
    eligible = [c for c in cases if c["eligible"]]
    # The band is rejected only if the complete 95% slope interval is disjoint.
    def band_decision(f):
        if not f.get("defined") and "ci95" not in f: return "inconclusive"
        lo, hi = f["ci95"]
        return "disjoint_below" if hi < -.60 else ("disjoint_above" if lo > -.40 else "overlaps_allowed_band")
    plt.figure(figsize=(7.2, 5.2))
    colors = {False:"#2457a6", True:"#d05a35"}
    for c in cases:
        if c["rate"] is not None:
            plt.errorbar(c["eta_inverse"], c["rate"], yerr=[[c["rate"]-c["rate_path_min"]],[c["rate_path_max"]-c["rate"]]], fmt="o", color=colors[c["family"] == "refined"], capsize=3)
    for family, f, color, label in (("base",fb,colors[False],"base-resolution fit"),("refined",fr,colors[True],"refined fit")):
        if "mean_fit_logS" in f:
            xx=np.exp(np.asarray(f["mean_fit_logS"])); yy=np.exp(np.asarray(f["mean_fit_logR"]))
            band=np.exp(np.asarray(f["mean_fit_ci95_logR"]))
            plt.plot(xx, yy, color=color, lw=1.7, label=f"{label}: p={f['p']:.3f} [{f['ci95'][0]:.3f}, {f['ci95'][1]:.3f}]")
            plt.fill_between(xx, band[0], band[1], color=color, alpha=.14)
    plt.xscale("log"); plt.yscale("log")
    plt.xlabel(r"nominal $S_\eta=1/\eta$ (not dimensional Lundquist number)")
    plt.ylabel(r"$R=(d\Psi/dt)/(B_{up}^2/\sqrt{\rho_{up}})$")
    plt.title("Fresh recorded island-coalescence rates; bars show flux-path spread")
    plt.legend(fontsize=8)
    plt.grid(True, which="both", alpha=.25); plt.tight_layout()
    scaling_path = outdir/"scaling_uncertainty.png"; plt.savefig(scaling_path, dpi=180); plt.close()
    field_figures=[]
    for c in cases:
        fig = draw_field(c, outdir)
        if fig: field_figures.append(fig)
    result = {"protocol": {"flux_window": [0.01,0.05], "observable": "fixed-window mean normalized flux-transfer rate",
              "fit": "OLS(log R, log S_eta), two-sided 95% Student-t interval; envelope is conservatively interpreted with the flux-path spread",
              "allowed_p": [-0.60,-0.40], "resolution_rule": "at least 8 cells per nominal delta_SP/L=S_eta^-1/2 and measured central-sheet |Jz| FWHM at least 4 cells",
              "eligibility": "full flux window, resolved, finite rate and zero detected secondary A_z extrema at prominence 0.005 in |x|=[0.04,0.22]",
              "decision": "reject band only if the complete 95% interval is disjoint from [-0.60,-0.40]; otherwise inconclusive; unresolved or plasmoid cases are excluded/censored"},
              "n_cases": len(cases), "n_eligible": len(eligible), "cases": [{k:v for k,v in c.items() if k!="raw"} for c in cases],
              "base_fit": fb, "refined_fit": fr, "base_decision": band_decision(fb), "refined_decision": band_decision(fr),
              "figures": {"scaling": str(scaling_path), "fields_current": field_figures}}
    Path(a.output).write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(json.dumps({k:result[k] for k in ("n_cases","n_eligible","base_fit","refined_fit","base_decision","refined_decision")}, indent=2))

if __name__ == "__main__": main()
