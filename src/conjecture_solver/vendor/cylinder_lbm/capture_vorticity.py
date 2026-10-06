"""Run a validated Re=100 domain and save four phase-resolved vorticity images."""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np
import warp as wp

import cylinder_warp_lbm_solver as lbm


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("docs/figures/vorticity"))
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--nd", type=int, default=32)
    parser.add_argument("--H", type=float, default=80.0)
    parser.add_argument("--L", type=float, default=80.0)
    parser.add_argument("--xc", type=float, default=40.0)
    parser.add_argument("--u", type=float, default=0.06)
    parser.add_argument("--tstart", type=float, default=240.0,
                        help="time in D/U before the first snapshot window")
    parser.add_argument("--st", type=float, default=0.1647,
                        help="estimated Strouhal number used to space four phases")
    parser.add_argument("--side-sponge-len", type=float, default=8.0)
    parser.add_argument("--out-eq-sponge-len", type=float, default=6.0)
    args = parser.parse_args()
    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    warm_steps = int(round(args.tstart * args.nd / args.u))
    phase_steps = int(round(args.nd / (args.u * args.st * 4)))
    if warm_steps < 1 or phase_steps < 1:
        parser.error("tstart and phase spacing must contain at least one step")
    cfg = lbm.make_config(100, override=dict(nd=args.nd, u=args.u, H=args.H,
                 L=args.L, xc=args.xc,
                 tconv=(warm_steps + 4 * phase_steps) * args.u / args.nd))
    wp.init()
    device = wp.get_device(args.device)
    sim = lbm.CylinderLBM(cfg, device=device,
                          side_sponge_len=args.side_sponge_len,
                          out_eq_sponge_len=args.out_eq_sponge_len)

    x0 = max(0, int(round(cfg["cx"] - 2 * args.nd)))
    x1 = min(cfg["nx"], int(round(cfg["cx"] + 18 * args.nd)))
    y0 = max(0, int(round(cfg["cy"] - 4 * args.nd)))
    y1 = min(cfg["ny"], int(round(cfg["cy"] + 4 * args.nd)))
    xs = (np.arange(x0, x1) - cfg["cx"]) / args.nd
    ys = (np.arange(y0, y1) - cfg["cy"]) / args.nd
    inside = xs[:, None] ** 2 + ys[None, :] ** 2 < 0.25
    frames = []

    def capture(step, state):
        mac = sim.macro(state)
        ux = mac[1, x0:x1, y0:y1]
        uy = mac[2, x0:x1, y0:y1]
        omega = (np.gradient(uy, axis=0) - np.gradient(ux, axis=1)) * args.nd / args.u
        omega[inside] = np.nan
        time_star = (warm_steps + step) * args.u / args.nd
        frames.append((time_star, omega.astype(np.float32)))
        print(f"Captured phase {len(frames)}/4 at t*={time_star:.4f}", flush=True)

    state, _ = sim.run(warm_steps, report_every=max(1, warm_steps // 8))
    sim.run(4 * phase_steps, g=state, t0=warm_steps,
            snap_every=phase_steps, snap_cb=capture,
            report_every=phase_steps)
    if len(frames) != 4:
        raise RuntimeError(f"Expected four frames, got {len(frames)}")

    lim = float(np.nanpercentile(np.abs(np.stack([f[1] for f in frames])), 99.5))
    lim = max(4.0, min(12.0, lim))
    extent = [xs[0] - .5 / args.nd, xs[-1] + .5 / args.nd,
              ys[0] - .5 / args.nd, ys[-1] + .5 / args.nd]

    def draw(ax, time_star, omega):
        im = ax.imshow(omega.T, origin="lower", extent=extent, cmap="RdBu_r",
                       vmin=-lim, vmax=lim, interpolation="bilinear", aspect="equal")
        ax.add_patch(Circle((0, 0), .5, facecolor="#202020", edgecolor="white", lw=.8))
        ax.set(xlim=(-2, 18), ylim=(-4, 4), xlabel="x / D", ylabel="y / D",
               title=f"tU/D = {time_star:.2f}")
        return im

    for i, (time_star, omega) in enumerate(frames, 1):
        fig, ax = plt.subplots(figsize=(11, 4.4), constrained_layout=True)
        im = draw(ax, time_star, omega)
        fig.colorbar(im, ax=ax, label="vorticity ωD/U", shrink=.8)
        fig.savefig(out / f"vorticity_phase_{i:02d}.png", dpi=190)
        plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(15, 7.4), sharex=True, sharey=True,
                             constrained_layout=True)
    for ax, (time_star, omega) in zip(axes.flat, frames):
        im = draw(ax, time_star, omega)
    fig.colorbar(im, ax=axes.ravel().tolist(), label="vorticity ωD/U", shrink=.83)
    fig.suptitle("Re=100 cylinder wake: four instants over one shedding cycle")
    fig.savefig(out / "vorticity_four_instants.png", dpi=190)
    plt.close(fig)
    metadata = dict(re=100, nd=args.nd, H=args.H, L=args.L, xc=args.xc,
                    u=args.u, tstart=args.tstart, st_spacing=args.st,
                    phase_steps=phase_steps, side_sponge_len=args.side_sponge_len,
                    out_eq_sponge_len=args.out_eq_sponge_len,
                    times_star=[round(t, 6) for t, _ in frames],
                    crop_x_over_D=[-2, 18], crop_y_over_D=[-4, 4],
                    vorticity_units="omega D / U", color_limit=lim)
    (out / "capture.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Saved four images and montage to {out}")


if __name__ == "__main__":
    main()
