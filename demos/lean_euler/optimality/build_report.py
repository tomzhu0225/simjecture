"""Build the PDF and standalone scientific figures from retained evidence."""

import json
from itertools import product
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).resolve().parent
RECORD = HERE / "record"
FIGURES = HERE / "figures"
FIGURES.mkdir(exist_ok=True)
r = json.loads((RECORD / "results.json").read_text())
p = json.loads((RECORD / "formal-results.json").read_text())
visual = np.load(RECORD / "visual_data.npz")
plt.rcParams.update(
    {"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight"}
)


def save(fig, name):
    fig.savefig(FIGURES / f"{name}.png", dpi=170)
    fig.savefig(FIGURES / f"{name}.pdf")
    plt.close(fig)


fig = plt.figure(figsize=(9, 3.7))
for j, (key, title) in enumerate(
    [("material", "Material cube, t = 0"), ("eulerian", "Moving Euler domain, t = 0.75")]
):
    ax = fig.add_subplot(1, 2, j + 1, projection="3d")
    xyz = visual[key][::6]
    scatter = ax.scatter(
        *xyz.T, c=visual["density"][::6], s=5, cmap="viridis", vmin=1.4, vmax=1.6, alpha=0.65
    )
    corners = np.array(list(product([0.0, 1.0], repeat=3)))
    if j:
        from solver import flow

        corners = flow(0.75, corners)
    for a in range(8):
        for b in range(a + 1, 8):
            if bin(a ^ b).count("1") == 1:
                ax.plot(*corners[[a, b]].T, color="#23364d", lw=1)
    ax.set(title=title, xlabel="x", ylabel="y", zlabel="z")
    ax.set_box_aspect((1.2, 1.2, 1))
fig.colorbar(scatter, ax=fig.axes, shrink=0.62, pad=0.05, label="Density")
save(fig, "shear_flow")

rows = r["rows"]
N = np.array([x["oracle_queries"] for x in rows])
bound = np.array([x["exact_real_uniform_bound"] for x in rows])
error = np.array([max(x["sampled_full_state_max_error_by_time"]) for x in rows])
seconds = np.array([x["median_build_seconds"] for x in rows])
fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.3), constrained_layout=True)
axes[0].loglog(N, bound, "o-", label="Proved exact-real upper bound", color="#274a72")
axes[0].loglog(N, error, "s-", label="Observed maximum on test points", color="#c06424")
axes[0].set(xlabel="Density queries N = n³", ylabel="Full-state absolute error")
axes[0].legend(fontsize=8)
axes[1].loglog(N, seconds, "o-", color="#274a72", label="Median NumPy construction")
axes[1].loglog(
    N, seconds[-1] * N / N[-1], "--", color="#929ba6", label="Linear guide, fitted at final point"
)
axes[1].set(xlabel="Density queries N = n³", ylabel="Seconds")
axes[1].legend(fontsize=8)
for ax in axes:
    ax.grid(alpha=0.2, which="both")
save(fig, "accuracy_work")

fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.2), constrained_layout=True)
n = 8
hole = np.array([3, 4, 2])
eps = r["hard_pair"]["epsilon"]
for i in range(n):
    for j in range(n):
        if [i, j] != list(hole[:2]):
            axes[0].plot((i + 0.5) / n, (j + 0.5) / n, ".", color="#274a72", ms=6)
axes[0].add_patch(plt.Rectangle(hole[:2] / n, 1 / n, 1 / n, facecolor="#eaa66f", alpha=0.5))
axes[0].plot(*(hole[:2] + 0.5) / n, "x", color="#9e3027", ms=8)
axes[0].set(
    xlim=(0, 1),
    ylim=(0, 1),
    xlabel="Material X",
    ylabel="Material Y",
    title="A slice through the unqueried cell",
)
axes[0].set_aspect("equal")
xx = np.linspace((hole[0] - 0.3) / n, (hole[0] + 1.3) / n, 400)
s = n * xx - hole[0]
bump = np.where((s > 0) & (s < 1), 16 * s * s * (1 - s) * (1 - s), 0)
axes[1].plot(xx, 1.5 + 2 * eps * bump, label="Admissible density +", color="#c06424")
axes[1].plot(xx, 1.5 - 2 * eps * bump, label="Admissible density −", color="#274a72")
axes[1].axhline(1.5, color="#929ba6", ls="--")
axes[1].set(
    xlabel="Material X through cell center",
    ylabel="Density",
    title="Same answers, different unseen values",
)
axes[1].legend(fontsize=8)
save(fig, "indistinguishable_inputs")

fontroot = Path("/usr/share/fonts/truetype/dejavu")
for name, file in [
    ("ReportSans", "DejaVuSans.ttf"),
    ("ReportSans-Bold", "DejaVuSans-Bold.ttf"),
    ("ReportMono", "DejaVuSansMono.ttf"),
]:
    pdfmetrics.registerFont(TTFont(name, str(fontroot / file)))
pdfmetrics.registerFontFamily(
    "ReportSans",
    normal="ReportSans",
    bold="ReportSans-Bold",
    italic="ReportSans",
    boldItalic="ReportSans-Bold",
)
styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        "BodyX",
        fontName="ReportSans",
        fontSize=9.3,
        leading=13.5,
        spaceAfter=8,
        textColor=colors.HexColor("#23364d"),
    )
)
styles.add(
    ParagraphStyle(
        "TitleX",
        fontName="ReportSans-Bold",
        fontSize=22,
        leading=27,
        spaceAfter=13,
        textColor=colors.HexColor("#183c60"),
    )
)
styles.add(
    ParagraphStyle(
        "HeadingX",
        fontName="ReportSans-Bold",
        fontSize=15,
        leading=20,
        spaceAfter=12,
        textColor=colors.HexColor("#183c60"),
    )
)
styles.add(ParagraphStyle("SmallX", parent=styles["BodyX"], fontSize=7.8, leading=11))
styles.add(
    ParagraphStyle(
        "FormulaX", parent=styles["BodyX"], fontSize=12, leading=19, spaceBefore=7, spaceAfter=12
    )
)
styles.add(
    ParagraphStyle("CodeX", fontName="ReportMono", fontSize=7.2, leading=10.5, spaceAfter=10)
)
story = []


def para(text, style="BodyX"):
    story.append(Paragraph(text, styles[style]))


def title(text):
    para(text, "HeadingX")


def picture(name, width=465):
    from PIL import Image as PILImage

    with PILImage.open(FIGURES / f"{name}.png") as im:
        w, h = im.size
    story.append(Image(str(FIGURES / f"{name}.png"), width=width, height=width * h / w))
    story.append(Spacer(1, 8))


def table(data, widths=None):
    cells = [[Paragraph(str(c), styles["SmallX"]) for c in row] for row in data]
    t = Table(cells, colWidths=widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7eef5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#8193a6")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 10))


def page():
    story.append(PageBreak())


para("A Lean-checked work-optimal solver<br/>for a restricted 3D Euler family", "TitleX")
para("Simjecture research experiment • 1 November 2026 • Draft PR #90", "SmallX")
para(
    "<b>Result.</b> A finite characteristic reconstruction attains a "
    "prescribed uniform physical-field error with work proportional to "
    "(L/ε)³. Every deterministic adaptive point-query algorithm solving the "
    "same family has a matching worst-case lower bound. Lean checks the "
    "actual Euler equations, the approximation guarantee, and the work "
    "argument."
)
para("W*(L, ε) = Θ((L/ε)<super>3</super>)", "FormulaX")
para(
    "<b>Scope.</b> Full compressible Euler in three dimensions, γ = 2, with "
    "arbitrary C1 Lipschitz initial density in [1,2], a fixed affine shear "
    "velocity, constant pressure, and a prescribed moving material wall. The "
    "output error covers all five conserved variables throughout the moving "
    "cube."
)
picture("shear_flow")
para(
    (
        "The density shown is 1.5 + 0.1 sin(2πX) sin(2πY) sin(2πZ). The theorem "
        "covers the entire stated density family, not only this demonstration."
    ),
    "SmallX",
)
para(
    "<b>Meaning of optimal.</b> The exponent is optimal up to fixed "
    "multiplicative constants in an exact-real RAM/oracle model. This is not "
    "a proof of the fastest wall time, the best constant, or optimality for "
    "pressure-driven or shock-forming Euler flows."
)

page()
title("The problem that was frozen before proof construction")
para(
    "Material position a = (X,Y,Z) lies in Q = [0,1]³. The Eulerian domain is"
    " F<sub>t</sub>(Q), and the wall moves with F<sub>t</sub>. The original "
    "contract uses 0 ≤ t ≤ 1. The formulas and checked estimates also hold at"
    " any real t."
)
para(
    (
        "F<sub>t</sub>(X,Y,Z) = (X + tY, Y + tZ, Z + "
        "t)<br/>F<sub>t</sub><super>−1</super>(x,y,z) = (x − ty + t²z − t³, y − "
        "tz + t², z − t)"
    ),
    "FormulaX",
)
para(
    (
        "ρ(t,x) = ρ<sub>0</sub>(F<sub>t</sub><super>−1</super>(x))<br/>v(t,x) = "
        "(y − tz + t², z − t, 1), &nbsp; p = 1<br/>U = (ρ, ρv<sub>x</sub>, "
        "ρv<sub>y</sub>, ρv<sub>z</sub>, 1 + ρ|v|²/2)"
    ),
    "FormulaX",
)
para(
    "All variables are nondimensional. The input function ρ<sub>0</sub>: R³ → R "
    "is globally C1, takes values in"
    " [1,2], and has Lipschitz constant at most L ≥ 1 in the coordinate "
    "maximum norm. It may vary independently in all three spatial "
    "coordinates. A competitor can learn it only by point evaluations."
)
table(
    [
        ["Checked physical property", "What it establishes"],
        [
            "C1 regularity and canonical Euler residual",
            (
                "Actual time and spatial differentiation of all five conservation"
                " equations; ideal-gas pressure is recovered from the conserved "
                "state."
            ),
        ],
        [
            "Initial condition",
            "The field at t = 0 has density ρ₀, velocity (Y,Z,1), and pressure 1.",
        ],
        [
            "Boundary motion",
            (
                "The material trajectory derivative equals the fluid velocity, "
                "including on every wall face."
            ),
        ],
        [
            "Invertible trajectory map",
            (
                "Mapping an Eulerian evaluation point back to the material cube "
                "is exact in the real-arithmetic theorem."
            ),
        ],
    ],
    [150, 315],
)
para(
    "This velocity has nonzero vorticity and nonzero convective terms, but "
    "its motion is known analytically and does not depend on ρ₀. The "
    "numerical problem is therefore recovery and transport of density within "
    "an exactly reducible Euler family. No general pressure dynamics are "
    "solved by this construction."
)
para(
    (
        "Accuracy is relative to the explicitly constructed classical solution. "
        "Uniqueness among every possible Euler solution is not a formalized "
        "claim."
    ),
    "SmallX",
)

page()
title("Constructive accuracy and complete modeled work")
para(
    "1. Set n = ceil(3L/(4ε)).<br/>2. Enumerate all n³ material cells and "
    "query ρ₀ at their centers.<br/>3. Retain the density table and the fixed"
    " reconstruction rule.<br/>4. At an output point, use "
    "F<sub>t</sub><super>−1</super>, its material cell, and the exact "
    "velocity to reconstruct U."
)
para(
    "Every material point is within 1/(2n) of its cell center. "
    "Consequently:<br/><b>density error ≤ L/(2n)</b>, and <b>full-state error"
    " ≤ 3L/(4n) ≤ ε</b>. The factor 3/2 comes from the energy component; the "
    "material velocity is (Y,Z,1). This is a uniform bound over the "
    "continuous domain."
)
table(
    [
        ["Counted part", "RAM work"],
        ["Enumerating triples in three nested loops", "5n³ + 4n² + 4n + 2"],
        ["Center arithmetic, oracle calls, table writes and fill-loop control", "13n³ + 2"],
        ["Table initialization, resolution, casts and output descriptor", "n³ + 8"],
        ["Total", "19n³ + 4n² + 4n + 12 ≤ 39n³"],
    ],
    [320, 145],
)
para(
    "For the stated small-tolerance regime, the checked upper bound is <b>W ≤"
    " 312(L/ε)³</b>. The RAM model charges scalar casts, additions, "
    "divisions, ceiling, indexing/storage, and oracle calls at unit cost. The"
    " table has n³ values; index enumeration and storage are included."
)
para(
    "The output is a finite representation of the full field. Evaluating "
    "additional requested points has additional cost. Finite functions "
    "represent constant-time RAM arrays in the formal program; the result is "
    "not a cost bound for persistent function closures. Bit complexity, "
    "floating-point rounding, compiler behavior and hardware scheduling are "
    "outside this model."
)
para(
    "The NumPy demonstration implements the same mathematical reconstruction "
    "with vectorized arrays. Lean has not verified that Python "
    "implementation. Its observed elapsed time is reported separately from "
    "the formal RAM count."
)

page()
title("A lower bound against adaptive competitors")
para(
    "The machine model permits arbitrary internal state, adaptive queries "
    "anywhere in R³, and arbitrary final output representations. Only "
    "admissible inputs must terminate. A point query costs one unit; any "
    "additional scalar or memory work is nonnegative."
)
para(
    "Follow the transcript produced by the constant input ρ₀ = 3/2. If fewer "
    "than n³ queries are made, one of n³ disjoint small cells receives no "
    "informative query. Lean constructs two globally smooth densities, 3/2 ± "
    "b, supported around that untouched cell. Their bounds and Lipschitz "
    "constants are checked. Both give the same answers throughout the "
    "transcript but differ by 4ε at the cell center. Their common output "
    "cannot be within ε of both."
)
picture("indistinguishable_inputs")
para(
    (
        "The figure uses a concrete quartic bump for numerical illustration. The "
        "proof constructs a tensor product of Mathlib smooth one-dimensional "
        "bumps and proves a fixed Lipschitz bound exists."
    ),
    "SmallX",
)
para(
    (
        "For one fixed K ≥ 1, independent of L and ε, every correct competitor "
        "satisfies<br/>(L/(4Kε))³ ≤ number of queries ≤ total charged "
        "work,<br/>provided L ≥ 1 and 0 &lt; ε ≤ 1/(4K)."
    ),
    "FormulaX",
)
para(
    "<b>K is not numerically evaluated.</b> The theorem establishes the "
    "matching asymptotic exponent. It does not supply a sharp "
    "finite-tolerance lower-bound constant or a measured speedup. The lower "
    "bound concerns the same full-state accuracy target because density is "
    "its first component."
)

page()
title("Local numerical demonstration and negative controls")
para(
    "The example uses the three-coordinate sinusoidal density on page 1, with"
    " L = 2. Each grid was constructed three times. Evaluation used 100,008 "
    "material points at t = 0, 0.25, 0.75 and 1, including cube corners. "
    "Construction timings include sample coordinates, density calls, table "
    "allocation and descriptor creation; reference/error analysis is "
    "separate."
)
data = [["ε", "n", "Queries", "Proved bound", "Observed max", "Build, ms"]]
for x in rows:
    data.append(
        [
            f"{x['epsilon']:g}",
            x["n"],
            f"{x['oracle_queries']:,}",
            f"{x['exact_real_uniform_bound']:.4f}",
            f"{max(x['sampled_full_state_max_error_by_time']):.5f}",
            f"{1000 * x['median_build_seconds']:.3f}",
        ]
    )
table(data, [45, 32, 85, 85, 85, 80])
picture("accuracy_work")
c = r["resolution_negative_control"]
para(
    "<b>Accuracy negative control.</b> Replacing the required n = "
    f"{c['correct_n']} by n = {c['altered_n']} fails on a smooth tanh density "
    "with global Lipschitz constant 2. At the recorded point, full-state "
    f"error rises from {c['correct_error']:.5f} to {c['altered_error']:.5f}, "
    "above ε = 0.05. The corresponding modified Lean source also fails to "
    "check."
)
para(
    "The independent central-difference Euler residual check gave a maximum "
    f"of {r['finite_difference_euler_residual_max']:.2e} with step 10⁻⁵. This "
    "is a numerical consistency check; the zero residual is proved separately"
    " in Lean.",
    "SmallX",
)
para(
    (
        "These timings are local observations for a simple density oracle. No "
        "comparison is made to Rusanov/MUSCL runs with different periodic "
        "boundaries, and no general-purpose solver speedup is inferred."
    ),
    "SmallX",
)

page()
title("Audit, reproduction, and what remains outside the result")
para(
    f"<b>{len(p['positive']['theorems'])} named statements passed</b> "
    "compilation and a separate transitive axiom audit. Allowed dependencies "
    "are propext, Classical.choice and Quot.sound. The checker retains the "
    "exact source, commands, runtime identity, diagnostics and hashes. The "
    "changed-resolution source is retained as an unsuccessful negative "
    "control."
)
para(
    "Central statement: "
    "<b>Machines.certified_general_optimality</b>.<br/>Physical solution: "
    "<b>Certificate.admissible_is_classical_euler</b>.<br/>Algorithm/value "
    "connection: <b>Work.solver_program_matches_query_algorithm</b>."
)
para("From the Simjecture repository root:", "SmallX")
para(
    (
        ".venv/bin/simjecture install lean<br/>.venv/bin/python "
        "demos/lean_euler/optimality/run_local.py \\<br/>&nbsp;&nbsp;--output "
        "artifacts/euler-optimality-replay"
    ),
    "CodeX",
)
para(
    "Use a new output directory. The replay creates an isolated local worker,"
    " runs the numerical experiment and bounded Lean capability, and retains "
    "lab receipts. The proof worker reserves 8 GB of address space; Lean "
    "itself uses one thread and a 2 GB managed-memory setting. A 4 GB "
    "address-space replay failed while loading the analysis libraries, before"
    " proof diagnostics. No global memory limit was changed."
)
para("Source SHA-256: " + p["positive"]["source_sha256"], "SmallX")
table(
    [
        ["Established", "Outside this proof"],
        [
            "Classical Euler equations for the frozen shear family",
            "General pressure-driven flow, shocks, turbulence, other boundary/initial classes",
        ],
        [
            "Uniform full-state accuracy for the returned representation",
            "Certified Python/IEEE error, input-class verification from samples",
        ],
        [
            "Matching worst-case work scaling against adaptive point-oracle machines",
            (
                "Best constants, randomized algorithms, "
                "derivative/integral/formula oracles, fastest hardware runtime"
            ),
        ],
    ],
    [230, 235],
)
para(
    (
        "Function recovery lower bounds have a substantial prior literature: C. "
        'A. Micchelli, T. J. Rivlin and S. Winograd, <link href="https://research'
        '.ibm.com/publications/the-optimal-recovery-of-smooth-functions" '
        'color="#274a72">The optimal recovery of smooth functions (1976)</link>. '
        "Affine Euler motions also predate this experiment; see T. C. Sideris, "
        '<link href="https://arxiv.org/abs/1512.03288" color="#274a72">Global '
        "existence and asymptotic behavior of affine motion of 3D ideal fluids "
        "surrounded by vacuum</link>, whose boundary/data family differs from "
        "this one."
    ),
    "SmallX",
)
para(
    (
        "This PR makes a scoped proof workflow reproducible. Mathematical novelty"
        " and priority are not established. A next research step would require a "
        "new frozen contract with unknown pressure dynamics, a proved numerical "
        "accuracy bound, and a lower bound for that enlarged class."
    ),
    "SmallX",
)


def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor("#d5dee7"))
    canvas.line(45, 40, A4[0] - 45, 40)
    canvas.setFont("ReportSans", 7.2)
    canvas.setFillColor(colors.HexColor("#607080"))
    canvas.drawString(45, 27, "Simjecture • restricted 3D Euler work optimality • 2026-11-01")
    canvas.drawRightString(A4[0] - 45, 27, str(doc.page))


SimpleDocTemplate(
    str(HERE / "report.pdf"),
    pagesize=A4,
    rightMargin=52,
    leftMargin=52,
    topMargin=45,
    bottomMargin=55,
    title="Lean-checked work optimality for a restricted 3D Euler family",
    author="Simjecture research experiment",
).build(story, onFirstPage=footer, onLaterPages=footer)
print(HERE / "report.pdf")
