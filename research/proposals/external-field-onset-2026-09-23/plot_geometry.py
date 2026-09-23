"""Conceptual geometry only; no simulated fields or results."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

root = Path(__file__).resolve().parent
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.titleweight": "bold"})
fig = plt.figure(figsize=(15, 7.8), facecolor="#f7f9fc")
ax = fig.add_subplot(121)
ax.set_facecolor("#ffffff")
left, right, guide, out = "#2274a5", "#cf653e", "#8253ad", "#268668"
for x, color in [(-3, left), (1.0, right)]:
    ax.add_patch(Rectangle((x, -2), 2, 4, facecolor=color, alpha=0.12, edgecolor=color, lw=1.6))
ax.add_patch(
    Rectangle((-1, -2), 2, 4, facecolor=guide, alpha=0.10, edgecolor=guide, lw=1.2, linestyle="--")
)
for z in [-1.15, 0, 1.15]:
    ax.annotate(
        "", xy=(-0.95, z), xytext=(-2.55, z), arrowprops=dict(arrowstyle="-|>", color=left, lw=2.3)
    )
    ax.annotate(
        "", xy=(0.95, z), xytext=(2.55, z), arrowprops=dict(arrowstyle="-|>", color=right, lw=2.3)
    )
for x in [-2.8, -1.7]:
    ax.annotate(
        "", xy=(x, 1.2), xytext=(x, -0.6), arrowprops=dict(arrowstyle="-|>", color=left, lw=2)
    )
for x in [1.7, 2.8]:
    ax.annotate(
        "", xy=(x, -1.2), xytext=(x, 0.6), arrowprops=dict(arrowstyle="-|>", color=right, lw=2)
    )
for z in [-1.35, 0, 1.35]:
    ax.text(0, z, r"$\odot$", color=guide, fontsize=27, ha="center", va="center")
ax.text(-2, 2.18, "Left magnetized flow", ha="center", color=left, weight="bold")
ax.text(2, 2.18, "Right magnetized flow", ha="center", color=right, weight="bold")
ax.text(-2, -2.25, r"$u_x>0,\ B_z>0$", ha="center", color=left)
ax.text(2, -2.25, r"$u_x<0,\ B_z<0$", ha="center", color=right)
ax.text(
    0,
    -2.85,
    "Initially low-density gap\nExternal field $B_y$ points out of the page",
    ha="center",
    color=guide,
)
ax.annotate(
    "",
    xy=(0, 2.8),
    xytext=(0, 2.03),
    arrowprops=dict(arrowstyle="-|>", color=out, lw=1.8, linestyle="--"),
)
ax.text(0.15, 2.6, "Possible later outflow", color=out, fontsize=10)
ax.annotate(
    "", xy=(3.5, -1.9), xytext=(3.5, -2.7), arrowprops=dict(arrowstyle="->", color="#273647")
)
ax.annotate(
    "", xy=(4.2, -2.7), xytext=(3.5, -2.7), arrowprops=dict(arrowstyle="->", color="#273647")
)
ax.text(4.2, -2.93, "x")
ax.text(3.4, -1.7, "z")
ax.set_xlim(-3.8, 4.3)
ax.set_ylim(-3.3, 3.35)
ax.set_aspect("equal")
ax.axis("off")
ax.set_title("1. Start with 2D resistive MHD", pad=14)
ax.text(
    0.5,
    1.01,
    r"$\partial/\partial y=0$; all three field components retained",
    transform=ax.transAxes,
    ha="center",
    fontsize=10,
    color="#526273",
)

bx = fig.add_subplot(122, projection="3d")
bx.set_facecolor("#f7f9fc")


def box(x0, x1, y0, y1, z0, z1, color, alpha):
    # Display coordinates are (x,z,y), keeping physical y vertical.
    v = np.array(
        [
            [x0, z0, y0],
            [x1, z0, y0],
            [x1, z1, y0],
            [x0, z1, y0],
            [x0, z0, y1],
            [x1, z0, y1],
            [x1, z1, y1],
            [x0, z1, y1],
        ]
    )
    faces = [
        [v[j] for j in ids]
        for ids in [
            (0, 1, 2, 3),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
        ]
    ]
    bx.add_collection3d(
        Poly3DCollection(faces, facecolors=color, edgecolors=color, alpha=alpha, linewidths=0.7)
    )


box(-3, -1, -1.5, 1.5, -2, 2, left, 0.09)
box(1, 3, -1.5, 1.5, -2, 2, right, 0.09)
box(-1, 1, -1.5, 1.5, -2, 2, guide, 0.035)
for yy in [-0.8, 0.8]:
    bx.quiver(-3.2, 0, yy, 1.8, 0, 0, color=left, linewidth=2, arrow_length_ratio=0.2)
    bx.quiver(3.2, 0, yy, -1.8, 0, 0, color=right, linewidth=2, arrow_length_ratio=0.2)
for xx in [-0.5, 0.5]:
    bx.quiver(xx, 0, -1.25, 0, 0, 2.5, color=guide, linewidth=2, arrow_length_ratio=0.10)
bx.quiver(-2, -0.8, 0, 0, 1.6, 0, color=left, linewidth=2, arrow_length_ratio=0.15)
bx.quiver(2, 0.8, 0, 0, -1.6, 0, color=right, linewidth=2, arrow_length_ratio=0.15)
# Candidate exhaust is marked schematic, not an observed flow.
bx.quiver(0, 1.1, 0, 0, 1.4, 0, color=out, linewidth=1.5, arrow_length_ratio=0.15, linestyle="--")
bx.quiver(0, -1.1, 0, 0, -1.4, 0, color=out, linewidth=1.5, arrow_length_ratio=0.15, linestyle="--")
bx.text(0, 0, 1.9, "End boundary: open / periodic", ha="center", fontsize=10, color="#273647")
bx.text(0, 0, -2.15, "Same comparison at the lower end", ha="center", fontsize=9, color="#526273")
bx.text(0.35, 0, 0.1, r"$B_y$", color=guide, fontsize=13)
bx.set_xlabel("x: inflow", labelpad=8)
bx.set_ylabel("z: reconnecting field / outflow", labelpad=8, fontsize=9)
bx.set_zlabel("y: external field / finite height", labelpad=9, fontsize=9)
bx.set_xlim(-3.5, 3.5)
bx.set_ylim(-2.6, 2.6)
bx.set_zlim(-1.8, 1.8)
bx.set_xticks([])
bx.set_yticks([])
bx.set_zticks([])
bx.view_init(elev=22, azim=-58)
bx.set_box_aspect((1.3, 1, 0.9))
bx.set_title("2. Compare matched 3D boundary conditions", pad=28, fontsize=12)
fig.suptitle(
    "Before a reconnection layer forms: can 3D transport release the magnetic barrier?",
    x=0.5,
    y=0.98,
    fontsize=17,
    weight="bold",
    color="#182b40",
)
fig.text(
    0.5,
    0.055,
    "Identical inflow drive, resistivity, initial gap and external field. "
    "Change only the y-end boundary condition.\n"
    "The current sheet must form dynamically; it is not imposed. "
    "Geometry is schematic and not to scale.",
    ha="center",
    fontsize=11,
    color="#34495e",
)
fig.subplots_adjust(left=0.035, right=0.96, bottom=0.15, top=0.85, wspace=0.1)
for suffix in ["png", "svg", "pdf"]:
    fig.savefig(root / f"geometry.{suffix}", dpi=180, bbox_inches="tight")
