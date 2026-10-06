r"""
Flow past a cylinder: NVIDIA Warp, D2Q9 MRT-LBM, and a smooth PSM body.

This is the forward-solver-only build. The automatic-differentiation machinery
(Warp tape, checkpointed BPTT, objective functions, gradient check, shape
optimization and parameter inference) has been removed. The physics is byte-for-
byte the same: the same fused kernel, the same MRT collision, the same LES and
the same PSM body when the optional lateral sponge is disabled.

Numerics
--------
The fused pull-streaming/collision kernel stores post-collision populations.
MRT uses the Lallemand-Luo basis. The "magic" option sets the odd-moment rate
to 8*(2-s_v)/(8-s_v); "reg" relaxes the ghost moments to equilibrium. This
ghost relaxation is not a general equivalence to every regularized LBM scheme.
Optional Smagorinsky viscosity is computed from the deviatoric non-equilibrium
stress. PSM blends the fluid collision with a moving-solid collision, using
either Noble-Torczynski or linear volume-fraction weighting.

The body is a radial Fourier shape with four harmonics, optionally rotating,
optionally blowing through its surface along the shape normal. For a noncircular
stationary shape, rotation is a prescribed velocity field, not a simulation of a
rigid body whose geometry rotates in time. Jet forcing does not impose a separate
mass source or enforce zero integrated mass flux. The diffuse interface has a
smooth, compact exterior tail. The deep solid center uses a constant fraction to
avoid the undefined polar angle at r=0.

Boundaries: Zou-He velocity inlet, an approximate zero-gradient outlet with a
viscosity sponge, and far/slip/noslip/periodic top and bottom conditions. The
far boundary is not nonreflecting; --side-sponge-len and
--out-eq-sponge-len enable graded relaxation to the free stream for
acoustic-sensitivity tests. The outlet is not an exact nonreflecting boundary.
Macroscopic output uses the
stored post-collision populations; values inside the PSM band depend on this
time convention.

Validation and limitations
--------------------------
nd/sqrt(Re) is a resolution heuristic, not an accuracy certificate. Check grid,
domain, interface-width, and time-window convergence for each application.
No universal blockage correction is applied. The bundled REF_2D ranges are
legacy orientation values without a reproducible benchmark provenance here.
High-Re 2D runs do not resolve 3D cylinder wakes. Force coefficients are
normalized by the baseline U and D of the configuration, not by the actual
inflow magnitude after an angle-of-attack change (they are equal: --aoa rotates
the inflow at fixed |U|).

fp32 is the production precision; --fp64 exists for precision checks and is far
slower on consumer GPUs. Measured fp32-vs-fp64 agreement on this solver: Cd/Cl
differ by order 1e-5 over several thousand steps at both tau0 = 0.53 and the
much harder tau0 = 0.503, and the mean Cd by 0.001%. fp32 plus GPU atomics does
not give bit-identical reruns.

Usage
-----
  python cylinder_warp_lbm_solver.py table
  python cylinder_warp_lbm_solver.py run --re 100 --device cuda --save-field
  python cylinder_warp_lbm_solver.py run --re 500 --device cuda --scale 0.5
  python cylinder_warp_lbm_solver.py run --re 100 --H 40 --side-sponge-len 8 \
      --out-eq-sponge-len 6 --device cuda
  python cylinder_warp_lbm_solver.py sweep --device cuda

  Non-circular, rotating, with an angle of attack:
  python cylinder_warp_lbm_solver.py run --re 200 --shape-a 0.09,-0.06 \
      --shape-b 0.05 --omega 0.5 --aoa 5

  Body and inflow (resolution independent: omega in U/R, jets in U):
    --shape-a / --shape-b   radial Fourier harmonics, sum of |a|+|b| <= 0.45
    --omega                 rotation rate in units of U/R
    --aoa                   angle of attack in degrees, |aoa| <= 45
    --jet-c / --jet-s       surface-normal blowing harmonics in units of U

  Discretization:
    --nd --u --L --H --xc --cs --ghost --tconv --steps --scale
    --wall far|slip|noslip|periodic     --psm nt|linear     --delta
    --side-sponge-len --side-sponge-max  (optional with wall=far)
    --out-eq-sponge-len --out-eq-sponge-max  (optional)

  Rotation and jets are stability limited by resolution. There is no automatic
  cap here: start small, confirm the run stays healthy, then increase.

  Errors from configuration, validation and divergence all exit with a single
  short message and status 2; --traceback restores the full stack.
  Optional --cache-dir selects the Warp compilation cache directory.

Requires warp-lang and numpy; matplotlib is optional for plotting. Regression-
tested with Warp 1.12.1 and 1.17.0. The health kernel uses explicit signed
bounds to avoid unary-negation issues with closed-over float64 constants in the
former.
"""

import os
import sys
import json
import math
import time
import argparse

import numpy as np
import warp as wp

# ==============================================================================
# 0. Design-variable layout (the params array)
# ==============================================================================
NFOUR = 4      # number of shape Fourier harmonics (a_k, b_k), k = 1..NFOUR
NJET  = 4      # number of blowing/suction harmonics (c_k, d_k), k = 1..NJET

P_UX  = 0      # inlet x velocity (lattice units)
P_UY  = 1      # inlet y velocity (angle of attack / transverse forcing)
P_TAU = 2      # base relaxation time tau0 -> nu = (tau0-0.5)/3 -> Re
P_XC  = 3      # cylinder centre x (lattice)
P_YC  = 4      # cylinder centre y (lattice)
P_R   = 5      # cylinder radius   (lattice)
P_OMG = 6      # rotation rate (lattice units, positive = counter-clockwise)
P_A   = 7                    # a_1..a_NFOUR
P_B   = P_A + NFOUR          # b_1..b_NFOUR
P_JC  = P_B + NFOUR          # c_1..c_NJET  (normal blowing/suction, cos terms)
P_JS  = P_JC + NJET          # d_1..d_NJET  (normal blowing/suction, sin terms)
NPAR  = P_JS + NJET

PAR_NAMES = (["U_in_x", "U_in_y", "tau0", "xc", "yc", "R", "omega"]
             + [f"a{k+1}" for k in range(NFOUR)]
             + [f"b{k+1}" for k in range(NFOUR)]
             + [f"jc{k+1}" for k in range(NJET)]
             + [f"js{k+1}" for k in range(NJET)])


WALL_SLIP, WALL_NOSLIP, WALL_PERIODIC, WALL_FAR = 0, 1, 2, 3
WALL_MAP = {"far": WALL_FAR, "slip": WALL_SLIP, "noslip": WALL_NOSLIP,
            "periodic": WALL_PERIODIC}
GHOST_MAGIC, GHOST_REG = 0, 1

# ==============================================================================
# 1. Resolution / relaxation settings per Reynolds number
# ==============================================================================
# nd    : lattice nodes per diameter (D = nd)
# u     : free-stream lattice velocity (<< cs = 0.577 to limit compressibility error)
# L,H   : domain size / D
# xc    : inlet-to-centre distance / D
# cs    : Smagorinsky constant Cs (0 disables LES)
# ghost : MRT ghost-moment strategy
# tconv : total physical time / (D/U)
# Resolution heuristic: nd/sqrt(Re) estimates nodes across a laminar boundary layer.
# It does not replace grid, domain, and interface-width convergence studies.
RE_TABLE = {
    100:   dict(nd=48,  u=0.060, L=32, H=20, xc=8, cs=0.00, ghost="magic", tconv=250),
    200:   dict(nd=64,  u=0.060, L=32, H=20, xc=8, cs=0.00, ghost="magic", tconv=250),
    300:   dict(nd=80,  u=0.070, L=30, H=18, xc=8, cs=0.00, ghost="magic", tconv=200),
    400:   dict(nd=88,  u=0.070, L=30, H=18, xc=8, cs=0.00, ghost="magic", tconv=200),
    500:   dict(nd=96,  u=0.080, L=28, H=16, xc=8, cs=0.00, ghost="magic", tconv=180),
    1000:  dict(nd=128, u=0.080, L=28, H=16, xc=8, cs=0.10, ghost="reg",   tconv=150),
    2000:  dict(nd=160, u=0.090, L=26, H=15, xc=7, cs=0.12, ghost="reg",   tconv=120),
    3000:  dict(nd=176, u=0.090, L=26, H=15, xc=7, cs=0.12, ghost="reg",   tconv=100),
    10000: dict(nd=224, u=0.100, L=24, H=14, xc=7, cs=0.14, ghost="reg",   tconv=80),
}

# Legacy reference ranges for orientation only; provenance is not recorded here.
REF_2D = {
    100:   dict(cd=(1.32, 1.40), st=(0.163, 0.168), note="2D and 3D agree, laminar periodic vortex street"),
    200:   dict(cd=(1.30, 1.42), st=(0.190, 0.202), note="onset of 3D transition (mode A), 2D slightly high"),
    300:   dict(cd=(1.35, 1.45), st=(0.205, 0.218), note="real flow already 3D, 2D is a numerical test case"),
    400:   dict(cd=(1.38, 1.50), st=(0.210, 0.225), note="as above"),
    500:   dict(cd=(1.40, 1.55), st=(0.215, 0.232), note="as above"),
    1000:  dict(cd=(1.45, 1.70), st=(0.225, 0.245), note="2D clearly overpredicts (experiment Cd~1.0)"),
    2000:  dict(cd=(1.50, 1.90), st=(0.230, 0.255), note="shear-layer instability dominates, LES required"),
    3000:  dict(cd=(1.55, 2.00), st=(0.230, 0.260), note="as above"),
    10000: dict(cd=(1.60, 2.30), st=(0.200, 0.260), note="experiment (3D) Cd~1.2, St~0.20"),
}


def make_config(re, scale=1.0, override=None):
    """Build the full discrete configuration from Re. scale < 1 shrinks nd for quick tests."""
    _positive(re, "re")
    _positive(scale, "scale")
    if re in RE_TABLE:
        base = dict(RE_TABLE[re])
    else:                                   # Re outside the table: extrapolate from the nearest entry
        key = min(RE_TABLE, key=lambda k: abs(math.log(k) - math.log(max(re, 1))))
        base = dict(RE_TABLE[key])
        base["nd"] = int(round(base["nd"] * math.sqrt(re / key)))
    if override:
        base.update({k: v for k, v in override.items() if v is not None})

    for name in ("nd", "u", "L", "H", "xc", "tconv"):
        _positive(base[name], name)
    _positive(base["cs"], "cs", allow_zero=True)
    if base["u"] >= 1.0 / math.sqrt(3.0):
        raise ValueError("u must be below the lattice sound speed (1/sqrt(3))")
    if base["ghost"] not in ("magic", "reg"):
        raise ValueError("ghost must be 'magic' or 'reg'")

    nd = max(8, int(round(base["nd"] * scale)))
    u  = float(base["u"])
    nu = u * nd / float(re)                 # lattice viscosity
    tau0 = 3.0 * nu + 0.5

    nx = int(round(base["L"] * nd))
    ny = int(round(base["H"] * nd))
    cx = float(base["xc"] * nd)
    cy = float(ny) * 0.5 + 0.5              # half-cell offset breaks symmetry, speeds up shedding
    steps = int(round(base["tconv"] * nd / u))
    if nx < 4 or ny < 4 or steps < 1:
        raise ValueError("the grid must be at least 4x4 and the run must contain a step")
    if min(cx, nx - 1 - cx, cy, ny - 1 - cy) <= 0.5 * nd + 1.0:
        raise ValueError("the cylinder must fit inside the domain with a one-cell margin")

    n_bl = nd / math.sqrt(max(re, 1.0))
    # As tau approaches 0.5 the magic odd-moment rate approaches zero.
    # Use equilibrium ghost relaxation on coarse grids unless explicitly overridden.
    ghost_auto = False
    if (not override or override.get("ghost") is None) \
            and base["ghost"] == "magic" and n_bl < 3.0:
        base["ghost"] = "reg"
        ghost_auto = True
    cfg = dict(re=float(re), nd=nd, D=float(nd), u=u, nu=nu, tau0=tau0,
               n_bl=n_bl, ghost_auto=ghost_auto,
               nx=nx, ny=ny, cx=cx, cy=cy, R=0.5 * nd,
               cs=float(base["cs"]), ghost=base["ghost"], steps=steps,
               tconv=base["tconv"], L=base["L"], H=base["H"])
    if tau0 <= 0.5:
        raise ValueError(f"tau0={tau0} <= 0.5; increase nd or u, or reduce Re")
    return cfg


def _positive(value, name, allow_zero=False):
    """Reject nonfinite or out-of-range scalar settings before allocation."""
    if not math.isfinite(value) or value < 0 or (value == 0 and not allow_zero):
        bound = "nonnegative" if allow_zero else "positive"
        raise ValueError(f"{name} must be finite and {bound}")


def _integer(value, name, minimum=1):
    if not isinstance(value, (int, np.integer)) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return int(value)


def print_table(scale=1.0):
    hdr = (f"{'Re':>7} {'nd':>5} {'u_lb':>6} {'nu_lb':>9} {'tau0':>8} {'Ma':>6} "
           f"{'N_bl':>5} {'nx':>6} {'ny':>6} {'Mcell':>7} {'GB':>5} {'steps':>8} "
           f"{'Gupd':>6} {'LES':>5} {'ghost':>6}")
    print(hdr)
    print("-" * len(hdr))
    tot = 0.0
    for re in sorted(RE_TABLE):
        c = make_config(re, scale)
        ma = c["u"] / math.sqrt(1.0 / 3.0)
        mc = c["nx"] * c["ny"] / 1e6
        gb = mc * 1e6 * 9 * 4 * 2 / 1024 ** 3
        gu = mc * c["steps"] / 1e3
        tot += gu
        print(f"{re:>7d} {c['nd']:>5d} {c['u']:>6.3f} {c['nu']:>9.5f} {c['tau0']:>8.5f} "
              f"{ma:>6.3f} {c['n_bl']:>5.1f} {c['nx']:>6d} {c['ny']:>6d} {mc:>7.2f} "
              f"{gb:>5.2f} {c['steps']:>8d} {gu:>6.0f} {c['cs']:>5.2f} {c['ghost']:>6s}")
    print("\n  N_bl = nd/sqrt(Re) = nodes across the boundary layer "
          "(resolution heuristic; verify convergence)")
    print("  GB   = double-buffered population memory (fp32);  Gupd = billions of node updates")
    print(f"  All nine Re total {tot:.0f} Gupd -- wall time from your measured MLUPS: "
          f"1000 MLUPS ~= {tot/1000/3.6:.1f} h, 2000 MLUPS ~= {tot/2000/3.6:.1f} h")
    print("\n2D reference values:")
    for re in sorted(REF_2D):
        r = REF_2D[re]
        print(f"  Re={re:<6d} Cd ~ {r['cd'][0]:.2f}-{r['cd'][1]:.2f}  "
              f"St ~ {r['st'][0]:.3f}-{r['st'][1]:.3f}   {r['note']}")


# ==============================================================================
# 2. Warp kernels (built per floating-point type, so fp64 gradient checks are possible)
# ==============================================================================
_KERNEL_CACHE = {}


def build_kernels(dt):
    """Build and cache every kernel. dt = wp.float32 / wp.float64.

    Top/bottom boundary (wall):
      0 slip     specular reflection -- an infinite row of mirror images, max blockage
      1 noslip   half-way bounce-back -- a real wind-tunnel wall
      2 periodic
      3 far      free-stream equilibrium for the missing populations; lets mass leave
                 laterally, far less confining than slip, closest to unbounded flow (default)
    """
    if dt in _KERNEL_CACHE:
        return _KERNEL_CACHE[dt]

    v9 = wp.types.vector(length=9, dtype=dt)

    # ---- typed constants (Warp does not mix float32/float64 implicitly) ----
    F0, F05, F1, F15 = dt(0.0), dt(0.5), dt(1.0), dt(1.5)
    F2, F3, F4, F45 = dt(2.0), dt(3.0), dt(4.0), dt(4.5)
    F8, F18 = dt(8.0), dt(18.0)
    R9, R36, R6, R12, R4 = dt(1.0/9.0), dt(1.0/36.0), dt(1.0/6.0), dt(1.0/12.0), dt(0.25)
    W0, W1, W2 = dt(4.0/9.0), dt(1.0/9.0), dt(1.0/36.0)
    TT, SX = dt(2.0/3.0), dt(1.0/6.0)
    EPS = dt(1.0e-12)
    RHOMIN = dt(1.0e-3)
    HEALTH_LOWER, HEALTH_UPPER = dt(-1.0e30), dt(1.0e30)
    SHAPE_MAX = dt(1.45)  # guaranteed by parameter validation
    TAIL_START, TAIL_END = dt(6.0), dt(8.0)

    # --------------------------------------------------------------------
    # D2Q9 equilibrium
    #   i : 0(0,0) 1(1,0) 2(0,1) 3(-1,0) 4(0,-1) 5(1,1) 6(-1,1) 7(-1,-1) 8(1,-1)
    #   opp: 0     3      4      1       2       7      8       5        6
    # --------------------------------------------------------------------
    @wp.func
    def feq(rho: dt, ux: dt, uy: dt) -> v9:
        usq = F15 * (ux * ux + uy * uy)
        e = v9()
        e[0] = W0 * rho * (F1 - usq)
        c = ux
        e[1] = W1 * rho * (F1 + F3 * c + F45 * c * c - usq)
        c = uy
        e[2] = W1 * rho * (F1 + F3 * c + F45 * c * c - usq)
        c = -ux
        e[3] = W1 * rho * (F1 + F3 * c + F45 * c * c - usq)
        c = -uy
        e[4] = W1 * rho * (F1 + F3 * c + F45 * c * c - usq)
        c = ux + uy
        e[5] = W2 * rho * (F1 + F3 * c + F45 * c * c - usq)
        c = -ux + uy
        e[6] = W2 * rho * (F1 + F3 * c + F45 * c * c - usq)
        c = -ux - uy
        e[7] = W2 * rho * (F1 + F3 * c + F45 * c * c - usq)
        c = ux - uy
        e[8] = W2 * rho * (F1 + F3 * c + F45 * c * c - usq)
        return e

    # --------------------------------------------------------------------
    # Solid volume fraction + solid velocity (smooth => differentiable w.r.t. geometry)
    #   phi = r - R[1 + sum_k a_k cos(k*th) + b_k sin(k*th)]
    #   eps = 0.5 [1 - tanh(phi/delta)]
    #   u_s = omega x r  +  4 eps (1-eps) v_n(th) n_hat
    # --------------------------------------------------------------------
    @wp.func
    def solid_at(par: wp.array(dtype=dt), xf: dt, yf: dt, delta: dt):
        dx = xf - par[P_XC]
        dy = yf - par[P_YC]
        Rb = par[P_R]
        r2 = dx * dx + dy * dy
        rmax = Rb * SHAPE_MAX + TAIL_END * delta
        epsS = F0
        usx = F0
        usy = F0
        if r2 < rmax * rmax:
            om = par[P_OMG]
            usx = -om * dy
            usy = om * dx
            epsS = F1
            core_radius = dt(0.1) * Rb
            if r2 > core_radius * core_radius:
                rr = wp.sqrt(r2)
                th = wp.atan2(dy, dx)
                shp = F1
                dshp = F0
                for k in range(NFOUR):
                    kk = dt(k + 1)
                    co, si = wp.cos(kk * th), wp.sin(kk * th)
                    shp += par[P_A + k] * co + par[P_B + k] * si
                    dshp += kk * (-par[P_A + k] * si + par[P_B + k] * co)
                phi = rr - Rb * shp
                z = phi / delta
                fraction = F05 * (F1 - wp.tanh(z))
                taper = F1
                if z >= TAIL_END:
                    taper = F0
                elif z > TAIL_START:
                    a = (z - TAIL_START) / (TAIL_END - TAIL_START)
                    taper = F1 - a*a*a * (dt(10.0) - dt(15.0)*a + dt(6.0)*a*a)
                # Smoothly saturate the inner core, where polar coordinates are singular.
                core_blend = F1
                if rr < dt(0.25) * Rb:
                    a = (rr / Rb - dt(0.1)) / dt(0.15)
                    core_blend = a*a*a * (dt(10.0) - dt(15.0)*a + dt(6.0)*a*a)
                epsS = F1 + core_blend * (fraction * taper - F1)
                wj = F4 * epsS * (F1 - epsS)
                vn = F0
                for k in range(NJET):
                    kk = dt(k + 1)
                    vn += par[P_JC + k] * wp.cos(kk * th) + par[P_JS + k] * wp.sin(kk * th)
                # For r=R*s(theta), the outward normal is proportional to s*e_r-s'*e_theta.
                norm = wp.sqrt(shp * shp + dshp * dshp)
                usx += wj * vn * (shp * dx + dshp * dy) / (rr * norm)
                usy += wj * vn * (shp * dy - dshp * dx) / (rr * norm)
        return epsS, usx, usy

    # --------------------------------------------------------------------
    # Main kernel: fused pull-streaming + boundaries + MRT collision + LES + PSM + force
    #   g_in / g_out hold the **post-collision** populations, layout (9, nx, ny)
    # --------------------------------------------------------------------
    @wp.kernel
    def k_step(g_in:  wp.array3d(dtype=dt),
               g_out: wp.array3d(dtype=dt),
               par:   wp.array(dtype=dt),
               tau_sp: wp.array(dtype=dt),        # extra outlet-sponge viscosity (length nx)
               out_sigma: wp.array(dtype=dt),     # outlet equilibrium sponge (length nx)
               side_sigma: wp.array(dtype=dt),    # lateral equilibrium sponge (length ny)
               force: wp.array2d(dtype=dt),       # (T, 2) aerodynamic force per step
               tstep: int,
               nx: int, ny: int,
               wall: int, ghost: int,
               cs2: dt, se: dt, seps: dt,
               delta: dt, uy_kick: dt, psm_lin: int):

        x, y = wp.tid()

        # ---- outlet: zero gradient (last column copies the upstream column's inflow set) ----
        xg = x
        if x >= nx - 1:
            xg = nx - 2
        xm = xg - 1
        if xm < 0:
            xm = 0
        xp = xg + 1
        if xp > nx - 1:
            xp = nx - 1

        # ------------------------------------------------------------------
        # The populations are gathered into scalars f0..f8 and written into the v9 once
        # at the end, rather than written into the vector and patched in place at the
        # inlet. This build does not differentiate, so the ordering is free -- but keep
        # it: if a vector component is assigned and then overwritten inside a branch,
        # Warp's reverse mode leaves the old value's adjoint path in place and a
        # spurious gradient appears. Scalars are safe because Warp renames them in SSA
        # form. The Zou-He inlet is exactly that "stream in, then overwrite" pattern, so
        # this shape is what makes the kernel safe to differentiate again later.
        # ------------------------------------------------------------------
        f0 = g_in[0, xg, y]
        f1 = g_in[1, xm, y]
        f3 = g_in[3, xp, y]

        # ---- bottom wall y=0: populations 2,5,6 are missing ----
        f2 = F0
        f5 = F0
        f6 = F0
        if y == 0:
            if wall == 0:                       # free slip (specular reflection)
                f2 = g_in[4, xg, 0]
                f5 = g_in[8, xm, 0]
                f6 = g_in[7, xp, 0]
            elif wall == 1:                     # no slip (half-way bounce-back)
                f2 = g_in[4, xg, 0]
                f5 = g_in[7, xg, 0]
                f6 = g_in[8, xg, 0]
            elif wall == 2:                     # periodic
                f2 = g_in[2, xg, ny - 1]
                f5 = g_in[5, xm, ny - 1]
                f6 = g_in[6, xp, ny - 1]
            else:                               # far field (free-stream equilibrium)
                ef = feq(F1, par[P_UX], par[P_UY] + uy_kick)
                f2 = ef[2]
                f5 = ef[5]
                f6 = ef[6]
        else:
            f2 = g_in[2, xg, y - 1]
            f5 = g_in[5, xm, y - 1]
            f6 = g_in[6, xp, y - 1]

        # ---- top wall y=ny-1: populations 4,7,8 are missing ----
        f4 = F0
        f7 = F0
        f8 = F0
        if y == ny - 1:
            if wall == 0:
                f4 = g_in[2, xg, ny - 1]
                f7 = g_in[6, xp, ny - 1]
                f8 = g_in[5, xm, ny - 1]
            elif wall == 1:
                f4 = g_in[2, xg, ny - 1]
                f7 = g_in[5, xg, ny - 1]
                f8 = g_in[6, xg, ny - 1]
            elif wall == 2:
                f4 = g_in[4, xg, 0]
                f7 = g_in[7, xp, 0]
                f8 = g_in[8, xm, 0]
            else:                               # far field
                ef = feq(F1, par[P_UX], par[P_UY] + uy_kick)
                f4 = ef[4]
                f7 = ef[7]
                f8 = ef[8]
        else:
            f4 = g_in[4, xg, y + 1]
            f7 = g_in[7, xp, y + 1]
            f8 = g_in[8, xm, y + 1]

        # ---- inlet x=0: Zou-He velocity BC (differentiable w.r.t. U_in) ----
        if x == 0:
            ux0 = par[P_UX]
            uy0 = par[P_UY] + uy_kick
            rw = (f0 + f2 + f4 + F2 * (f3 + f6 + f7)) / (F1 - ux0)
            f1 = f3 + TT * rw * ux0
            f5 = f7 - F05 * (f2 - f4) + SX * rw * ux0 + F05 * rw * uy0
            f8 = f6 + F05 * (f2 - f4) + SX * rw * ux0 - F05 * rw * uy0

        f = v9()
        f[0] = f0
        f[1] = f1
        f[2] = f2
        f[3] = f3
        f[4] = f4
        f[5] = f5
        f[6] = f6
        f[7] = f7
        f[8] = f8

        # ---- macroscopic quantities ----
        rho = f[0] + f[1] + f[2] + f[3] + f[4] + f[5] + f[6] + f[7] + f[8]
        if rho < RHOMIN:
            rho = RHOMIN
        jx = f[1] - f[3] + f[5] - f[6] - f[7] + f[8]
        jy = f[2] - f[4] + f[5] + f[6] - f[7] - f[8]
        ux = jx / rho
        uy = jy / rho

        # ---- moments (Lallemand-Luo) ----
        s45 = f[5] + f[6] + f[7] + f[8]
        s14 = f[1] + f[2] + f[3] + f[4]
        m1 = -F4 * f[0] - s14 + F2 * s45
        m2 = F4 * f[0] - F2 * s14 + s45
        m4 = -F2 * (f[1] - f[3]) + (f[5] - f[6] - f[7] + f[8])
        m6 = -F2 * (f[2] - f[4]) + (f[5] + f[6] - f[7] - f[8])
        m7 = (f[1] + f[3]) - (f[2] + f[4])
        m8 = f[5] - f[6] + f[7] - f[8]

        j2 = (jx * jx + jy * jy) / rho
        m1e = -F2 * rho + F3 * j2
        m2e = rho - F3 * j2
        m4e = -jx
        m6e = -jy
        m7e = (jx * jx - jy * jy) / rho
        m8e = jx * jy / rho

        # ---- Smagorinsky LES (from the non-equilibrium moments) ----
        tau0 = par[P_TAU] + tau_sp[x]
        tau = tau0
        if cs2 > F0:
            d7 = m7 - m7e
            d8 = m8 - m8e
            Qn = wp.sqrt(d7 * d7 + F4 * d8 * d8 + EPS)
            tau = F05 * (tau0 + wp.sqrt(tau0 * tau0 + F18 * cs2 * Qn / rho))

        sv = F1 / tau
        s_e = se
        s_ep = seps
        s_q = F1
        if ghost == 0:                          # magic: Lambda = 3/16
            s_q = F8 * (F2 - sv) / (F8 - sv)
        else:                                   # regularized: all ghost moments -> equilibrium
            s_e = F1
            s_ep = F1

        m1p = m1 - s_e * (m1 - m1e)
        m2p = m2 - s_ep * (m2 - m2e)
        m4p = m4 - s_q * (m4 - m4e)
        m6p = m6 - s_q * (m6 - m6e)
        m7p = m7 - sv * (m7 - m7e)
        m8p = m8 - sv * (m8 - m8e)

        # ---- inverse transform M^{-1} = M^T diag(1/||row||^2) ----
        n0 = rho * R9
        n1 = m1p * R36
        n2 = m2p * R36
        n3 = jx * R6
        n4 = m4p * R12
        n5 = jy * R6
        n6 = m6p * R12
        n7 = m7p * R4
        n8 = m8p * R4

        gc = v9()
        gc[0] = n0 - F4 * n1 + F4 * n2
        gc[1] = n0 - n1 - F2 * n2 + n3 - F2 * n4 + n7
        gc[2] = n0 - n1 - F2 * n2 + n5 - F2 * n6 - n7
        gc[3] = n0 - n1 - F2 * n2 - n3 + F2 * n4 + n7
        gc[4] = n0 - n1 - F2 * n2 - n5 + F2 * n6 - n7
        gc[5] = n0 + F2 * n1 + n2 + n3 + n4 + n5 + n6 + n8
        gc[6] = n0 + F2 * n1 + n2 - n3 - n4 + n5 + n6 - n8
        gc[7] = n0 + F2 * n1 + n2 - n3 - n4 - n5 - n6 + n8
        gc[8] = n0 + F2 * n1 + n2 + n3 + n4 - n5 - n6 - n8

        # ---- PSM immersed boundary ----
        epsS, usx, usy = solid_at(par, dt(x), dt(y), delta)
        B = F0
        om = v9()
        if epsS > F0:
            # Noble-Torczynski weight: at low viscosity (tau -> 0.5) the interface coupling
            # weakens and the wall gets slightly permeable; the linear weight B = eps is
            # viscosity independent and stiffer at high Re, at a small cost in accuracy.
            if psm_lin == 1:
                B = epsS
            else:
                B = epsS * (tau - F05) / ((F1 - epsS) + (tau - F05))
            es = feq(rho, usx, usy)
            eu = feq(rho, ux, uy)
            om[0] = es[0] - eu[0]
            om[1] = f[3] - f[1] + es[1] - eu[3]
            om[2] = f[4] - f[2] + es[2] - eu[4]
            om[3] = f[1] - f[3] + es[3] - eu[1]
            om[4] = f[2] - f[4] + es[4] - eu[2]
            om[5] = f[7] - f[5] + es[5] - eu[7]
            om[6] = f[8] - f[6] + es[6] - eu[8]
            om[7] = f[5] - f[7] + es[7] - eu[5]
            om[8] = f[6] - f[8] + es[8] - eu[6]
            # fluid momentum gain = B * sum Omega^s c  =>  force on the solid takes a minus sign
            Sx = om[1] - om[3] + om[5] - om[6] - om[7] + om[8]
            Sy = om[2] - om[4] + om[5] + om[6] - om[7] - om[8]
            wp.atomic_add(force, tstep, 0, -B * Sx)
            wp.atomic_add(force, tstep, 1, -B * Sy)

        sigma = F1 - (F1 - side_sigma[y]) * (F1 - out_sigma[x])
        if sigma > F0:
            ef_side = feq(F1, par[P_UX], par[P_UY])
            for i in range(9):
                updated = f[i] + (F1 - B) * (gc[i] - f[i]) + B * om[i]
                g_out[i, x, y] = (F1 - sigma) * updated + sigma * ef_side[i]
        else:
            for i in range(9):
                g_out[i, x, y] = f[i] + (F1 - B) * (gc[i] - f[i]) + B * om[i]

    # --------------------------------------------------------------------
    # Initialization / macroscopic extraction
    # --------------------------------------------------------------------
    @wp.kernel
    def k_init(g: wp.array3d(dtype=dt), par: wp.array(dtype=dt)):
        x, y = wp.tid()
        e = feq(F1, par[P_UX], par[P_UY])
        for i in range(9):
            g[i, x, y] = e[i]

    @wp.kernel
    def k_macro(g: wp.array3d(dtype=dt), out: wp.array3d(dtype=dt)):
        x, y = wp.tid()
        rho = F0
        for i in range(9):
            rho += g[i, x, y]
        if rho < RHOMIN:
            rho = RHOMIN
        jx = g[1, x, y] - g[3, x, y] + g[5, x, y] - g[6, x, y] - g[7, x, y] + g[8, x, y]
        jy = g[2, x, y] - g[4, x, y] + g[5, x, y] + g[6, x, y] - g[7, x, y] - g[8, x, y]
        out[0, x, y] = rho
        out[1, x, y] = jx / rho
        out[2, x, y] = jy / rho

    @wp.kernel
    def k_solidmap(par: wp.array(dtype=dt), out: wp.array2d(dtype=dt), delta: dt):
        x, y = wp.tid()
        e, a, b = solid_at(par, dt(x), dt(y), delta)
        out[x, y] = e







    @wp.kernel
    def k_health(g: wp.array3d(dtype=dt), out: wp.array(dtype=dt)):
        # Device-side reduction so a health check costs one kernel and two scalars
        # instead of nine host transfers. Comparison-based nonfinite detection keeps
        # this working on Warp versions without wp.isfinite.
        x, y = wp.tid()
        s = F0
        bad = F0
        for i in range(9):
            v = g[i, x, y]
            # Use distinct signed constants: -UPPER can miscompile for fp64 in Warp 1.12.1.
            if not (v > HEALTH_LOWER and v < HEALTH_UPPER):
                bad = F1
            s += v
        if bad > F0:
            wp.atomic_max(out, 1, F1)
        else:
            wp.atomic_min(out, 0, s)

    K = dict(step=k_step, init=k_init, macro=k_macro, solidmap=k_solidmap,
             health=k_health, dtype=dt)
    _KERNEL_CACHE[dt] = K
    return K


# ==============================================================================
# 3. Solver
# ==============================================================================
class CylinderLBM:
    """D2Q9 MRT-LBM solver for flow past a cylinder (differentiable)."""

    def __init__(self, cfg, device=None, fp64=False, wall="far",
                 delta=0.50, sponge_len=3.0, sponge_max=0.7,
                 se=1.19, seps=1.4, kick_amp=0.05, kick_periods=2.0,
                 psm="nt", verbose=True, side_sponge_len=0.0,
                 side_sponge_max=0.04, out_eq_sponge_len=0.0,
                 out_eq_sponge_max=0.04):
        _positive(delta, "delta")
        _positive(sponge_len, "sponge_len", allow_zero=True)
        _positive(sponge_max, "sponge_max", allow_zero=True)
        _positive(out_eq_sponge_len, "out_eq_sponge_len", allow_zero=True)
        _positive(out_eq_sponge_max, "out_eq_sponge_max", allow_zero=True)
        _positive(side_sponge_len, "side_sponge_len", allow_zero=True)
        _positive(side_sponge_max, "side_sponge_max", allow_zero=True)
        if out_eq_sponge_max > 1.0:
            raise ValueError("out_eq_sponge_max must not exceed 1")
        if side_sponge_max > 1.0:
            raise ValueError("side_sponge_max must not exceed 1")
        _positive(kick_amp, "kick_amp", allow_zero=True)
        _positive(kick_periods, "kick_periods", allow_zero=True)
        if wall not in WALL_MAP or psm not in ("nt", "linear"):
            raise ValueError("unsupported wall or PSM option")
        if not (0 < se < 2 and 0 < seps < 2):
            raise ValueError("MRT relaxation rates must be in (0, 2)")
        if delta > 0.25 * cfg["R"]:
            raise ValueError("delta must not exceed one quarter of the baseline radius")
        self.cfg = cfg
        self.dev = wp.get_device(device) if device else wp.get_device()
        self.dt = wp.float64 if fp64 else wp.float32
        self.np_dt = np.float64 if fp64 else np.float32
        self.K = build_kernels(self.dt)
        self.nx, self.ny = cfg["nx"], cfg["ny"]
        self.wall = WALL_MAP[wall]
        self.ghost = GHOST_MAGIC if cfg["ghost"] == "magic" else GHOST_REG
        self.cs2 = cfg["cs"] ** 2
        self.delta = delta
        self.se, self.seps = se, seps
        self.psm_lin = 1 if psm == "linear" else 0
        self.verbose = verbose

        # design variables
        p = np.zeros(NPAR, dtype=self.np_dt)
        p[P_UX] = cfg["u"]
        p[P_UY] = 0.0
        p[P_TAU] = cfg["tau0"]
        p[P_XC] = cfg["cx"]
        p[P_YC] = cfg["cy"]
        p[P_R] = cfg["R"]
        self.par = wp.zeros(NPAR, dtype=self.dt, device=self.dev)
        self.set_params(p)          # the baseline goes through the same validation
        self.p0 = p.copy()

        # Outlet sponge: over the last sponge_len*D the viscosity is raised smoothly so that
        # vortices are absorbed instead of reflecting back into the domain.
        sp = np.zeros(self.nx, dtype=self.np_dt)
        if sponge_len > 0:
            n_sp = min(self.nx - 1, max(2, int(sponge_len * cfg["nd"])))
            x0 = self.nx - n_sp
            s = np.linspace(0.0, 1.0, n_sp)
            sp[x0:] = sponge_max * s ** 2
        self.tau_sp = wp.array(sp, dtype=self.dt, device=self.dev)

        outlet = np.zeros(self.nx, dtype=self.np_dt)
        if out_eq_sponge_len > 0:
            width = int(round(out_eq_sponge_len * cfg["nd"]))
            if width < 2 or width >= self.nx - cfg["cx"] - cfg["R"] - 3 * cfg["nd"]:
                raise ValueError("outlet equilibrium sponge must leave at least 3D after the cylinder")
            distance = np.arange(self.nx)[::-1]
            outlet = out_eq_sponge_max * np.maximum(0.0, (width - distance) / width) ** 2
        self.out_sigma = wp.array(outlet, dtype=self.dt, device=self.dev)

        # Relax outgoing populations smoothly toward the free stream before they
        # reach the equilibrium-inflow lateral boundary. This attenuates sound
        # reflected by that boundary without changing the cylinder's near field.
        side = np.zeros(self.ny, dtype=self.np_dt)
        if side_sponge_len > 0:
            if wall != "far":
                raise ValueError("side sponge requires wall='far'")
            width = int(round(side_sponge_len * cfg["nd"]))
            if width < 2 or width >= self.ny // 2 - 3 * cfg["nd"]:
                raise ValueError("side sponge must leave at least 3D of undamped fluid around the cylinder")
            distance = np.minimum(np.arange(self.ny), np.arange(self.ny)[::-1])
            side = side_sponge_max * np.maximum(0.0, (width - distance) / width) ** 2
        self.side_sigma = wp.array(side, dtype=self.dt, device=self.dev)

        # shedding trigger (a deterministic function of t, not differentiated)
        self.kick_amp = kick_amp * cfg["u"]
        self.kick_T = cfg["nd"] / cfg["u"]
        self.kick_steps = int(kick_periods * self.kick_T)

        # normalization 0.5*rho*U^2*D, frozen at the initial U so that the definition of Cd
        # does not drift while U itself is being optimized
        self.qref = 0.5 * cfg["u"] ** 2 * cfg["D"]
        self.qinv = 1.0 / self.qref

        if verbose:
            print(f"[cfg] Re={cfg['re']:.0f} grid={self.nx}x{self.ny} "
                  f"({self.nx*self.ny/1e6:.2f} Mcells) nd={cfg['nd']} u={cfg['u']:.3f} "
                  f"tau0={cfg['tau0']:.5f} Cs={cfg['cs']:.2f} ghost={cfg['ghost']} "
                  f"device={self.dev} dtype={'fp64' if fp64 else 'fp32'}")
            nb = cfg["n_bl"]
            q = ("check grid and domain convergence" if nb >= 4 else
                 "marginally resolved" if nb >= 2.5 else
                 "severely under-resolved, qualitative / autodiff demo only")
            print(f"[res] N_bl = nd/sqrt(Re) = {nb:.2f} cells ({q});  "
                  f"PSM interface width ~= {2*delta:.1f} cells")
            if cfg.get("ghost_auto"):
                print("[bc ] low resolution: switched automatically from magic to "
                      "regularized ghost for stability (force it with --ghost magic)")

    # ---------------- state management ----------------
    def new_state(self):
        return wp.zeros((9, self.nx, self.ny), dtype=self.dt, device=self.dev)

    def init_state(self, g):
        wp.launch(self.K["init"], dim=(self.nx, self.ny),
                  inputs=[g, self.par], device=self.dev)

    def set_params(self, p_np):
        p = np.asarray(p_np, dtype=self.np_dt)
        if p.shape != (NPAR,) or not np.all(np.isfinite(p)):
            raise ValueError(f"params must contain {NPAR} finite scalars")
        if not 0 < p[P_UX] < 1 / math.sqrt(3) or abs(p[P_UY]) >= 1 / math.sqrt(3):
            raise ValueError("inlet components must be subsonic, with U_in_x > 0")
        if p[P_TAU] <= 0.5 or p[P_R] <= 0:
            raise ValueError("tau0 must exceed 0.5 and R must be positive")
        shape_norm = float(np.sum(np.abs(p[P_A:P_JC])))
        if shape_norm > 0.450001:
            raise ValueError("the sum of absolute shape coefficients must not exceed 0.45")
        extent = float(p[P_R]) * (1.0 + shape_norm) + 1.0
        if min(p[P_XC], self.nx-1-p[P_XC], p[P_YC], self.ny-1-p[P_YC]) <= extent:
            raise ValueError("the shape must fit inside the domain with a one-cell margin")
        self.par.assign(p)

    def get_params(self):
        return self.par.numpy().astype(np.float64)

    def kick(self, t):
        if t >= self.kick_steps:
            return 0.0
        return self.kick_amp * math.sin(2.0 * math.pi * t / self.kick_T)

    # ---------------- single step ----------------
    def step(self, gin, gout, force, tslot, t_global):
        wp.launch(self.K["step"], dim=(self.nx, self.ny),
                  inputs=[gin, gout, self.par, self.tau_sp, self.out_sigma, self.side_sigma, force, tslot,
                          self.nx, self.ny, self.wall, self.ghost,
                          self.cs2, self.se, self.seps,
                          self.delta, self.kick(t_global), self.psm_lin],
                  device=self.dev)

    # ---------------- forward run (no gradient, ping-pong double buffer) ----------------
    def run(self, nsteps, g=None, t0=0, report_every=None, snap_every=0,
            snap_cb=None):
        nsteps = _integer(nsteps, "nsteps")
        _integer(t0, "t0", minimum=0)
        _integer(snap_every, "snap_every", minimum=0)
        if g is None:
            g = self.new_state()
            self.init_state(g)
        gb = self.new_state()
        force = wp.zeros((nsteps, 2), dtype=self.dt, device=self.dev)
        if report_every is None:
            report_every = max(1, nsteps // 20)
        _integer(report_every, "report_every")

        t_start = time.perf_counter()
        for t in range(nsteps):
            self.step(g, gb, force, t, t0 + t)
            g, gb = gb, g
            if (t + 1) % report_every == 0 or t + 1 == nsteps:
                fr = force[max(0, t - 200):t + 1].numpy()
                if not np.all(np.isfinite(fr)):
                    raise FloatingPointError("nonfinite force; increase resolution or viscosity")
                cd = float(np.mean(fr[:, 0])) * self.qinv
                cl = float(fr[-1, 1]) * self.qinv
                el = max(time.perf_counter() - t_start, 1e-9)
                mlups = (t + 1) * self.nx * self.ny / el / 1e6
                if self.verbose:
                    print(f"  step {t+1:>8d}/{nsteps}  t*={(t0+t+1)*self.cfg['u']/self.cfg['nd']:7.1f}"
                          f"  Cd={cd:7.4f}  Cl={cl:+7.4f}  {mlups:7.1f} MLUPS  {el:6.1f}s",
                          flush=True)
            if snap_every and snap_cb and (t + 1) % snap_every == 0:
                snap_cb(t + 1, g)
        result = force.numpy().astype(np.float64)
        if not np.all(np.isfinite(result)):
            raise FloatingPointError("nonfinite force history")
        self._check_state(g)
        return g, result

    def _check_state(self, g):
        """Reduce the field on the device and transfer only (min density, bad flag)."""
        h = wp.array(np.array([1.0e30, 0.0], dtype=self.np_dt), dtype=self.dt,
                     device=self.dev)
        wp.launch(self.K["health"], dim=(self.nx, self.ny), inputs=[g, h],
                  device=self.dev)
        rho_min, bad = (float(v) for v in h.numpy())
        if bad > 0.0:
            raise FloatingPointError("nonfinite populations in the flow field")
        if rho_min <= float(self.np_dt(1.0e-3)):
            raise FloatingPointError(
                f"density reached the numerical floor (min rho = {rho_min:.3e}); "
                "the flow is invalid")

    # ---------------- macroscopic fields ----------------
    def macro(self, g):
        out = wp.zeros((3, self.nx, self.ny), dtype=self.dt, device=self.dev)
        wp.launch(self.K["macro"], dim=(self.nx, self.ny),
                  inputs=[g, out], device=self.dev)
        return out.numpy().astype(np.float64)

    def solid_map(self):
        out = wp.zeros((self.nx, self.ny), dtype=self.dt, device=self.dev)
        wp.launch(self.K["solidmap"], dim=(self.nx, self.ny),
                  inputs=[self.par, out, self.delta], device=self.dev)
        return out.numpy().astype(np.float64)








# ==============================================================================
# 5. Post-processing (Cd/Cl statistics, Strouhal number, plots)
# ==============================================================================
def analyse_forces(fnp, cfg, qinv, frac=0.5):
    fnp = np.asarray(fnp, dtype=np.float64)
    if fnp.ndim != 2 or fnp.shape[1] != 2 or not len(fnp) or not np.all(np.isfinite(fnp)):
        raise ValueError("force history must be a nonempty finite (T, 2) array")
    if not math.isfinite(frac) or not 0 < frac <= 1:
        raise ValueError("stat_frac must be in (0, 1]")
    _positive(qinv, "qinv")
    cd = fnp[:, 0] * qinv
    cl = fnp[:, 1] * qinv
    n = len(cd)
    i0 = int(n * (1.0 - frac))
    scd, scl = cd[i0:], cl[i0:]
    res = dict(cd_mean=float(np.mean(scd)), cd_std=float(np.std(scd)),
               cl_mean=float(np.mean(scl)), cl_rms=float(np.sqrt(np.mean(scl ** 2))),
               cl_std=float(np.std(scl)), stat_start=i0,
               cl_amp=float(np.max(np.abs(scl - np.mean(scl)))) if len(scl) else 0.0,
               st=float("nan"), f_lat=float("nan"))
    m = len(scl)
    if m > 64 and np.std(scl) > 1e-12 * max(1.0, float(np.max(np.abs(scl)))):
        y = (scl - np.mean(scl)) * np.hanning(m)
        sp = np.abs(np.fft.rfft(y))
        fr = np.fft.rfftfreq(m, d=1.0)          # cycles per lattice time step
        k = int(np.argmax(sp[1:])) + 1
        if 1 <= k < len(sp) - 1:                # parabolic interpolation of the peak
            a, b, c = sp[k - 1], sp[k], sp[k + 1]
            den = (a - 2 * b + c)
            dk = 0.5 * (a - c) / den if abs(den) > 1e-30 else 0.0
        else:
            dk = 0.0
        f = (k + dk) * (fr[1] - fr[0])
        res["f_lat"] = float(f)
        res["st"] = float(f * cfg["nd"] / cfg["u"])
    return res


def vorticity(mac, cfg):
    ux, uy = mac[1], mac[2]
    duy_dx = np.gradient(uy, axis=0)
    dux_dy = np.gradient(ux, axis=1)
    return (duy_dx - dux_dy) * cfg["nd"] / cfg["u"]      # non-dimensionalized omega*D/U


def make_plots(outdir, tag, fnp, mac, solid, cfg, stats, qinv):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:                                # pragma: no cover
        print(f"  [warn] matplotlib not available, skipping plots ({e})")
        return []
    files = []
    nd, u = cfg["nd"], cfg["u"]
    tstar = (np.arange(len(fnp)) + 1) * u / nd
    cd, cl = fnp[:, 0] * qinv, fnp[:, 1] * qinv

    # --- vorticity field ---
    w = vorticity(mac, cfg)
    sub = max(1, cfg["nx"] // 1600)
    ws = w[::sub, ::sub].T
    ss = solid[::sub, ::sub].T
    ws = np.ma.masked_where(ss > 0.5, ws)
    fig, ax = plt.subplots(figsize=(13, max(3.0, 12.2 * cfg["ny"] / cfg["nx"] + 0.7)),
                           constrained_layout=True)
    lim = float(np.nanpercentile(np.abs(ws.compressed()), 99.0)) if ws.count() else 5.0
    lim = max(lim, 1e-6)
    ex = [0, cfg["nx"] / nd, 0, cfg["ny"] / nd]
    im = ax.imshow(ws, origin="lower", extent=ex, cmap="RdBu_r",
                   vmin=-lim, vmax=lim, interpolation="bilinear")
    ax.contour(np.linspace(ex[0], ex[1], ss.shape[1]),
               np.linspace(ex[2], ex[3], ss.shape[0]), ss, levels=[0.5],
               colors="k", linewidths=1.0)
    ax.set_xlabel("x/D"); ax.set_ylabel("y/D")
    ax.set_title(f"Re={cfg['re']:.0f}  vorticity $\\omega D/U$   "
                 f"$\\overline{{C_d}}$={stats['cd_mean']:.3f}  St={stats['st']:.3f}")
    fig.colorbar(im, ax=ax, shrink=0.85, label="$\\omega D/U$")
    p = os.path.join(outdir, f"vorticity_{tag}.png")
    fig.savefig(p, dpi=130); plt.close(fig); files.append(p)

    # --- force history + spectrum ---
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.2))
    skip = int(2.0 * nd / u)
    # Retain short histories instead of reducing them to a single invisible point.
    k0 = skip if len(tstar) > skip + 64 else 0
    axs[0].plot(tstar[k0:], cd[k0:], lw=0.8, label="$C_d$")
    axs[0].plot(tstar[k0:], cl[k0:], lw=0.8, label="$C_l$")
    axs[0].axhline(stats["cd_mean"], color="k", ls="--", lw=0.8,
                   label=f"$\\overline{{C_d}}$={stats['cd_mean']:.3f}")
    axs[0].set_xlabel("$t U/D$"); axs[0].set_ylabel("force coefficient")
    seg = slice(stats["stat_start"], None)
    lo = min(cl[seg].min(), cd[seg].min()) - 0.4
    hi = max(cl[seg].max(), cd[seg].max()) + 0.4
    axs[0].set_ylim(lo, hi)
    axs[0].legend(fontsize=8); axs[0].grid(alpha=.3)
    i0 = stats["stat_start"]
    y = cl[i0:] - cl[i0:].mean()
    if len(y) > 64:
        sp = np.abs(np.fft.rfft(y * np.hanning(len(y))))
        fr = np.fft.rfftfreq(len(y), d=1.0) * nd / u
        axs[1].semilogy(fr[1:], sp[1:] + 1e-30, lw=0.8)
        if np.isfinite(stats["st"]):
            axs[1].axvline(stats["st"], color="r", ls="--", lw=0.8,
                           label=f"St={stats['st']:.4f}")
            axs[1].legend(fontsize=8)
        axs[1].set_xlim(0, 1.2)
    else:
        axs[1].text(0.5, 0.5, "Not enough samples for a spectrum",
                    transform=axs[1].transAxes, ha="center", va="center")
    axs[1].set_xlabel("St = f D / U"); axs[1].set_ylabel("|FFT($C_l$)|")
    axs[1].grid(alpha=.3)
    fig.suptitle(f"Re = {cfg['re']:.0f}")
    fig.tight_layout()
    p = os.path.join(outdir, f"forces_{tag}.png")
    fig.savefig(p, dpi=130); plt.close(fig); files.append(p)
    return files














# ==============================================================================
# 7. Command-line sub-commands
# ==============================================================================
def _mkout(d):
    os.makedirs(d, exist_ok=True)
    return d


def _re_tag(re):
    """Preserve distinct float Reynolds numbers while keeping legacy integer names."""
    re = float(re)
    _positive(re, "re")
    label = str(int(re)) if re.is_integer() else repr(re)
    return f"Re{label}"


def _sim_from_args(args, re, verbose=True):
    ov = dict(nd=args.nd, u=args.u, cs=args.cs, L=args.L, H=args.H,
              xc=args.xc, ghost=args.ghost, tconv=args.tconv)
    cfg = make_config(re, scale=args.scale, override=ov)
    if args.steps is not None:
        cfg["steps"] = args.steps
    sim = CylinderLBM(cfg, device=args.device, fp64=args.fp64, wall=args.wall,
                      delta=args.delta, psm=args.psm,
                      out_eq_sponge_len=args.out_eq_sponge_len,
                      out_eq_sponge_max=args.out_eq_sponge_max,
                      side_sponge_len=args.side_sponge_len,
                      side_sponge_max=args.side_sponge_max, verbose=verbose)
    apply_body_args(sim, cfg, args)
    return cfg, sim




def cmd_run(args, re=None, outdir=None):
    re = re if re is not None else args.re
    outdir = _mkout(outdir or args.out)
    cfg, sim = _sim_from_args(args, re)
    tag = _re_tag(re)

    t0 = time.perf_counter()
    g, fnp = sim.run(cfg["steps"])
    wall = max(time.perf_counter() - t0, 1e-9)

    stats = analyse_forces(fnp, cfg, sim.qinv, frac=args.stat_frac)
    mac = sim.macro(g)
    solid = sim.solid_map()

    np.savetxt(os.path.join(outdir, f"forces_{tag}.csv"),
               np.column_stack([(np.arange(len(fnp)) + 1) * cfg["u"] / cfg["nd"],
                                fnp[:, 0] * sim.qinv, fnp[:, 1] * sim.qinv]),
               delimiter=",", header="t_star,Cd,Cl", comments="")
    if args.save_field:
        np.savez_compressed(os.path.join(outdir, f"field_{tag}.npz"),
                            rho=mac[0].astype(np.float32),
                            ux=mac[1].astype(np.float32),
                            uy=mac[2].astype(np.float32),
                            solid=solid.astype(np.float32),
                            params=sim.get_params().astype(np.float64),
                            param_names=np.array(PAR_NAMES),
                            **{k: v for k, v in cfg.items()})
    if not args.no_plot:
        make_plots(outdir, tag, fnp, mac, solid, cfg, stats, sim.qinv)

    ref = REF_2D.get(int(re))
    print(f"\n=== Re = {float(re):g} ===")
    print(f"  grid {cfg['nx']}x{cfg['ny']}  steps {cfg['steps']}  wall time {wall:.1f}s "
          f"({cfg['steps']*cfg['nx']*cfg['ny']/wall/1e6:.1f} MLUPS)")
    print(f"  Cd_mean = {stats['cd_mean']:.4f}   Cd_std = {stats['cd_std']:.4f}")
    print(f"  Cl_rms  = {stats['cl_rms']:.4f}   Cl_std = {stats['cl_std']:.4f}   "
          f"Cl_amp = {stats['cl_amp']:.4f}")
    print(f"    (Cl_rms is taken about zero, Cl_std about the sample mean; statistics "
          f"use the last {100*args.stat_frac:.0f}% of the history)")
    print(f"  St      = {stats['st']:.4f}")
    if ref:
        print(f"  2D reference: Cd {ref['cd'][0]:.2f}-{ref['cd'][1]:.2f}, "
              f"St {ref['st'][0]:.3f}-{ref['st'][1]:.3f}   [{ref['note']}]")
    stats.update(re=float(re), nx=cfg["nx"], ny=cfg["ny"], nd=cfg["nd"],
                 u=cfg["u"], tau0=cfg["tau0"], steps=cfg["steps"], wall_s=wall,
                 params={n: float(v) for n, v in zip(PAR_NAMES, sim.get_params())})
    return stats


def cmd_sweep(args):
    outdir = _mkout(args.out)
    res = []
    for re in [float(x) for x in args.re_list.split(",")]:
        try:
            res.append(cmd_run(args, re=re, outdir=outdir))
        except Exception as e:
            print(f"  [Re={re}] failed: {e}")
            res.append(dict(re=re, cd_mean=float("nan"), st=float("nan"), error=str(e)))
    with open(os.path.join(outdir, "sweep_summary.json"), "w") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    print("\n" + "=" * 74)
    print(f"{'Re':>8} {'grid':>13} {'Cd_mean':>9} {'Cd_std':>8} {'Cl_rms':>8} "
          f"{'St':>8} {'Cd_ref':>12}")
    print("-" * 74)
    for r in res:
        ref = REF_2D.get(int(r["re"]))
        rs = f"{ref['cd'][0]:.2f}-{ref['cd'][1]:.2f}" if ref else "-"
        gr = f"{r.get('nx','-')}x{r.get('ny','-')}"
        print(f"{r['re']:>8.0f} {gr:>13} {r['cd_mean']:>9.4f} "
              f"{r.get('cd_std',float('nan')):>8.4f} {r.get('cl_rms',float('nan')):>8.4f} "
              f"{r['st']:>8.4f} {rs:>12}")
    print("=" * 74)
    print(f"results written to {outdir}")
    failed = sum("error" in result for result in res)
    if failed:
        raise RuntimeError(f"{failed} of {len(res)} sweep cases failed; "
                           f"see {os.path.join(outdir, 'sweep_summary.json')}")
    return res






















# ==============================================================================
# 8. main
# ==============================================================================
def _vec_arg(text, n, name, scale=1.0):
    """Parse 'x1,x2,...' into n floats, scaled. Empty or None gives zeros."""
    if not text:
        return np.zeros(n)
    parts = [t for t in text.replace(";", ",").split(",") if t.strip()]
    if len(parts) > n:
        raise ValueError(f"{name} takes at most {n} comma-separated numbers")
    try:
        vals = [float(t) for t in parts]
    except ValueError:
        raise ValueError(f"{name} must be comma-separated numbers")
    if not all(math.isfinite(v) for v in vals):
        raise ValueError(f"{name} must be finite")
    out = np.zeros(n)
    out[:len(vals)] = vals
    return out * scale


def apply_body_args(sim, cfg, args):
    """Set the physical body/inflow parameters from the command line.

    Shape harmonics, rotation and surface jets are properties of the simulated body,
    so they stay reachable even though the optimizer that used to drive them is gone.
    """
    p = sim.get_params()
    a = _vec_arg(args.shape_a, NFOUR, "--shape-a")
    b = _vec_arg(args.shape_b, NFOUR, "--shape-b")
    p[P_A:P_A + NFOUR] = a
    p[P_B:P_B + NFOUR] = b
    # Rotation is given in units of U/R and jets in units of U, so the same command
    # line means the same physics at any resolution.
    p[P_OMG] = args.omega * cfg["u"] / cfg["R"]
    p[P_JC:P_JC + NJET] = _vec_arg(args.jet_c, NJET, "--jet-c", cfg["u"])
    p[P_JS:P_JS + NJET] = _vec_arg(args.jet_s, NJET, "--jet-s", cfg["u"])
    # Angle of attack rotates the inflow at fixed speed, instead of only adding a
    # transverse component and changing |U| with it.
    rad = math.radians(args.aoa)
    p[P_UX] = cfg["u"] * math.cos(rad)
    p[P_UY] = cfg["u"] * math.sin(rad)
    sim.set_params(p)
    if sim.verbose:
        changed = []
        if np.any(a) or np.any(b):
            changed.append("shape a=[" + ",".join(f"{v:+.3f}" for v in a) + "] "
                           "b=[" + ",".join(f"{v:+.3f}" for v in b) + "]")
        if args.omega:
            changed.append(f"omega={args.omega:+.3f} U/R "
                           f"(surface speed {abs(args.omega)*cfg['u']:.4f})")
        if args.aoa:
            changed.append(f"aoa={args.aoa:+.2f} deg")
        if args.jet_c or args.jet_s:
            changed.append("surface jets active")
        if changed:
            print("[body] " + ";  ".join(changed))
    return p


def build_argparser():
    ap = argparse.ArgumentParser(
        description="Flow past a cylinder (Warp / D2Q9 MRT-LBM + smooth PSM body)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage")[-1])
    ap.add_argument("cmd", choices=["run", "sweep", "table"])
    # general
    ap.add_argument("--re", type=float, default=100.0)
    ap.add_argument("--re-list", default="100,200,300,400,500,1000,2000,3000,10000")
    ap.add_argument("--device", default=None, help="cpu / cuda / cuda:0")
    ap.add_argument("--cache-dir", default=None, help="Warp compilation cache directory")
    ap.add_argument("--traceback", action="store_true",
                    help="re-raise errors with the full traceback instead of a short message")
    ap.add_argument("--fp64", action="store_true",
                    help="double precision; far slower, for precision checks only")
    ap.add_argument("--scale", type=float, default=1.0, help="resolution scaling, for quick tests")
    # discretization overrides
    ap.add_argument("--nd", type=int, default=None, help="override lattice nodes per diameter")
    ap.add_argument("--u", type=float, default=None, help="override the lattice inflow velocity")
    ap.add_argument("--cs", type=float, default=None, help="override the Smagorinsky Cs")
    ap.add_argument("--L", type=float, default=None, help="override streamwise domain length / D")
    ap.add_argument("--H", type=float, default=None, help="override domain height / D (blockage = 1/H)")
    ap.add_argument("--xc", type=float, default=None, help="override inlet-to-centre distance / D")
    ap.add_argument("--ghost", default=None, choices=["magic", "reg"])
    ap.add_argument("--tconv", type=float, default=None, help="override total time / (D/U)")
    ap.add_argument("--steps", type=int, default=None, help="override the total number of steps")
    ap.add_argument("--wall", default="far", choices=list(WALL_MAP),
                    help="top/bottom BC: far (default) / slip / noslip / periodic")
    ap.add_argument("--side-sponge-len", type=float, default=0.0,
                    help="optional lateral acoustic sponge width / D for wall=far")
    ap.add_argument("--side-sponge-max", type=float, default=0.04,
                    help="maximum per-step lateral sponge relaxation (0..1)")
    ap.add_argument("--out-eq-sponge-len", type=float, default=0.0,
                    help="optional outlet acoustic sponge width / D")
    ap.add_argument("--out-eq-sponge-max", type=float, default=0.04,
                    help="maximum per-step outlet equilibrium sponge relaxation (0..1)")
    ap.add_argument("--delta", type=float, default=0.50,
                    help="PSM interface width in cells; smaller is sharper and more accurate")
    ap.add_argument("--psm", default="nt", choices=["nt", "linear"],
                    help="PSM weight: nt (Noble-Torczynski) / linear (B=eps, stiffer at high Re)")
    # body and inflow
    ap.add_argument("--shape-a", default=None, metavar="a1,a2,a3,a4",
                    help=f"cosine shape harmonics, up to {NFOUR}; r(th)/R = 1 + sum a_k cos k*th + b_k sin k*th")
    ap.add_argument("--shape-b", default=None, metavar="b1,b2,b3,b4",
                    help=f"sine shape harmonics, up to {NFOUR}; sum of |a|+|b| must stay <= 0.45")
    ap.add_argument("--omega", type=float, default=0.0,
                    help="cylinder rotation in units of U/R (positive = counter-clockwise)")
    ap.add_argument("--aoa", type=float, default=0.0,
                    help="angle of attack in degrees; rotates the inflow at fixed |U|")
    ap.add_argument("--jet-c", default=None, metavar="c1,c2,c3,c4",
                    help=f"surface-normal blowing, cosine harmonics in units of U, up to {NJET}")
    ap.add_argument("--jet-s", default=None, metavar="s1,s2,s3,s4",
                    help=f"surface-normal blowing, sine harmonics in units of U, up to {NJET}")
    # output
    ap.add_argument("--out", default="out")
    ap.add_argument("--no-plot", action="store_true")
    ap.add_argument("--save-field", action="store_true")
    ap.add_argument("--stat-frac", type=float, default=0.5,
                    help="trailing fraction of the history used for statistics")
    return ap


def main(argv=None):
    ap = build_argparser()
    args = ap.parse_args(argv)
    try:
        validate_args(args)
    except ValueError as exc:
        ap.error(str(exc))
    if args.cmd == "table":
        print_table(args.scale); return
    if args.cache_dir:
        wp.config.kernel_cache_dir = os.path.abspath(args.cache_dir)
    wp.init()
    handler = dict(run=cmd_run, sweep=cmd_sweep)[args.cmd]
    # One error surface: configuration, validation and divergence all report the same
    # way. --traceback restores the full stack for debugging.
    try:
        handler(args)
    except (ValueError, FloatingPointError, RuntimeError, FileNotFoundError,
            KeyError) as exc:
        if args.traceback:
            raise
        print(f"{ap.prog}: error: {exc}", file=sys.stderr)
        raise SystemExit(2)


def validate_args(args):
    for name in ("re", "scale", "delta"):
        _positive(getattr(args, name), name)
    if args.cs is not None:
        _positive(args.cs, "cs", allow_zero=True)
    for name in ("nd", "u", "L", "H", "xc", "tconv", "steps"):
        value = getattr(args, name)
        if value is not None:
            _positive(value, name)
    if not math.isfinite(args.stat_frac) or not 0 < args.stat_frac <= 1:
        raise ValueError("stat-frac must be in (0, 1]")
    if not math.isfinite(args.omega):
        raise ValueError("omega must be finite")
    if not math.isfinite(args.aoa) or abs(args.aoa) > 45.0:
        raise ValueError("aoa must be finite and within +/- 45 degrees; the "
                         "zero-gradient outlet is not meant for large angles")
    # Parse the vector arguments now so a typo fails before any allocation.
    _vec_arg(args.shape_a, NFOUR, "--shape-a")
    _vec_arg(args.shape_b, NFOUR, "--shape-b")
    _vec_arg(args.jet_c, NJET, "--jet-c")
    _vec_arg(args.jet_s, NJET, "--jet-s")
    if args.cmd == "sweep":
        for value in args.re_list.split(","):
            _positive(float(value), "re-list entry")


if __name__ == "__main__":
    main()
