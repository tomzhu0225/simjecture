"""Build a progress report from the retained nonlinear Euler evidence."""

import json
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
RECORD = HERE / "record/solver"
formal = json.loads((RECORD / "solver-formal.json").read_text())
numeric = json.loads((RECORD / "validation.json").read_text())
entropy_record = json.loads((RECORD / "entropy-validation.json").read_text())
ec_record = json.loads((RECORD / "ec-validation.json").read_text())
step_record = json.loads((RECORD / "step-bound-validation.json").read_text())
proof = formal["result"]
assert proof["checked"]
figures = HERE / "figures"
figures.mkdir(exist_ok=True)
fig, axes = plt.subplots(1, 2, figsize=(8.7, 3.0), constrained_layout=True)
for amplitude in [0.5, 0.75, 1.0]:
    rows = [row for row in entropy_record["rows"] if row["A"] == amplitude]
    n = np.array([row["n"] for row in rows])
    loss = np.array([row["entropy_loss"] for row in rows])
    label = f"A={amplitude:g}, δ={rows[0]['delta']:g}"
    axes[0].loglog(2 * np.pi / n, loss, "o-", label=label)
    axes[1].plot(
        n,
        [row["relative_entropy_final"] / row["relative_entropy_initial"] for row in rows],
        "o-",
        label=label,
    )
guide_h = 2 * np.pi / np.array([16, 32, 64])
axes[0].loglog(guide_h, 0.21 * guide_h, "--", color="gray", label="h guide (scaled)")
axes[0].set(xlabel="Grid spacing h", ylabel="Observed discrete entropy loss")
axes[0].legend(fontsize=7)
axes[1].set(xlabel="Cells per axis n", ylabel="Remaining relative entropy R(T)/R(0)", ylim=(0, 1))
axes[1].set_xticks([16, 32, 64])
for axis in axes:
    axis.grid(alpha=0.25, which="both")
    axis.spines[["top", "right"]].set_visible(False)
fig.savefig(figures / "entropy_loss.png", dpi=180)
fig.savefig(figures / "entropy_loss.pdf")
plt.close(fig)

fontroot = Path("/usr/share/fonts/truetype/dejavu")
for name, filename in [("Report", "DejaVuSans.ttf"), ("ReportBold", "DejaVuSans-Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name, str(fontroot / filename)))
pdfmetrics.registerFontFamily("Report", normal="Report", bold="ReportBold")
styles = getSampleStyleSheet()
for name, size, leading in [("BodyR", 9, 13), ("SmallR", 8, 11), ("HeadingR", 13, 18)]:
    styles.add(
        ParagraphStyle(
            name,
            fontName="ReportBold" if name == "HeadingR" else "Report",
            fontSize=size,
            leading=leading,
            spaceAfter=8,
            textColor=colors.HexColor("#20334a"),
        )
    )
styles.add(
    ParagraphStyle("TitleR", parent=styles["HeadingR"], fontSize=22, leading=28, spaceAfter=15)
)
story = []


def para(text, style="BodyR"):
    story.append(Paragraph(text, styles[style]))


def table(rows, widths):
    cells = [[Paragraph(str(value), styles["SmallR"]) for value in row] for row in rows]
    result = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eff5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#8fa2b4")),
            ]
        )
    )
    story.extend([result, Spacer(1, 10)])


def page_number(canvas, doc):
    canvas.setFont("Report", 8)
    canvas.setFillColor(colors.HexColor("#586b7e"))
    canvas.drawString(44, 26, "Simjecture • nonlinear Euler research • 2 November 2026")
    canvas.drawRightString(A4[0] - 44, 26, str(doc.page))


para("Nonlinear 3D Euler:<br/>checked solver foundations", "TitleR")
para("Active research goal • draft PR #90 • progress record, 2 November 2026", "SmallR")
para(
    "<b>Accuracy and optimality remain unproved.</b> Lean has checked the named foundations "
    "listed below. The result is not yet a solver certified to reach a specified physical "
    "error, and no matching total-work lower bound has been established."
)
para("The physical problem", "HeadingR")
para(
    "Full, unforced, compressible Euler with γ = 2 on the periodic cube [0, 2π]³. "
    "The family has amplitude A ∈ [0.5, 1] and density perturbation δ ∈ [−0.05, 0.05]. "
    "Only initial conditions are supplied; all five conserved fields must evolve."
)
para(
    "ρ₀ = 1 + δ sin x sin y sin z<br/>"
    "v₀ = A (sin x cos y cos z, −cos x sin y cos z, 0)<br/>"
    "p₀ = 1 + (A²/16)(cos 2x + cos 2y)(cos 2z + 2)<br/>"
    "E₀ = p₀ + ρ₀|v₀|²/2"
)
para(
    "Initially ρ₀ ≥ 0.95 and p₀ ≥ 0.625. At (0, 0, π/4), the vertical momentum "
    "equation forces ∂ₜ(ρv<sub>z</sub>) = A²/4 ≥ 1/16. This rules out freezing the "
    "initial zero vertical velocity. It does not prove that no analytic representation "
    "could ever exist."
)
para("Candidate and intended result", "HeadingR")
para(
    "The baseline is a conservative, explicit, global-speed Rusanov finite-volume "
    "method. An alternative uses an existing entropy-conservative flux plus LF diffusion "
    "and a timestep-halving acceptance test, now with explicit per-state bounds "
    "(pages 7–8). Both use analytic initial averages. "
    "T = 0.25 is the numerical target; a common smooth existence interval is still unproved. "
    "The intended error includes the full evolved field, spatial reconstruction and time "
    "integration, using volume-normalized L1 error in each conserved component."
)
table(
    [
        ["Required for completion", "Current status"],
        ["Common smooth time and uniform regularity", "Unproved"],
        ["Fully discrete nonlinear stability and continuum error", "Unproved; foundations checked"],
        ["Scientifically justified competitor class", "Initial search scope; not finalized"],
        ["Matching total-work upper and lower bounds", "Unproved"],
    ],
    [290, 215],
)
para(
    "All competitors receive the explicit initial-condition formulas. The target is not "
    "initial-data sampling complexity, a cache schedule, a CFL count, an output-size bound, "
    "or a ranking of a finite benchmark catalogue."
)

story.append(PageBreak())
para("What Lean has checked", "TitleR")
para(
    f"The retained audit checks <b>{len(proof['theorems'])} named statements</b> with "
    f"{proof['lean_version']}. Transitive axiom dependencies are limited to the standard "
    "principles propext, Classical.choice and Quot.sound. Statements must still "
    "be interpreted with their definitions and explicit premises."
)
table(
    [
        ["Layer", "Checked claim and its limit"],
        [
            "Actual nonlinear finite-volume update",
            "Exact-real positive density/pressure from computed wave speeds and a valid CFL ratio; "
            "periodic conservation of all five components. This does not prove convergence.",
        ],
        [
            "Conservative / primitive connection",
            "Actual derivative rules, invertible state-map derivative, equivalent Euler "
            "residuals, and a positive symmetrizing energy. This does not construct a solution.",
        ],
        [
            "Frozen principal update",
            "The constant-coefficient linearized update contracts its discrete energy "
            "under the stated wave-speed and CFL bounds.",
        ],
        [
            "Varying principal update",
            "An exact energy defect and an explicit growth estimate from stated spatial "
            "difference bounds. This is not the full nonlinear update stability theorem.",
        ],
        [
            "Grid embedding and state-box bounds",
            "A mesh-independent 3D embedding and explicit coercivity/coefficient bounds. "
            "The trajectory's derivative energies and state-box membership are not bounded yet.",
        ],
        [
            "Actual mathematical entropy",
            "Conserved-variable gradient and positive Hessian, convexity on admissible "
            "states, finite averaging bound, canonical entropy-flux potential and local "
            "entropy balance implied by differentiable Euler balance.",
        ],
        [
            "Actual finite-step entropy estimate",
            "Flux residual, six-neighbor increment bound and finite-step Taylor remainder "
            "combine into entropy dissipation under explicit convex-region and step conditions. "
            "These conditions are not established for the full numerical trajectory.",
        ],
        [
            "Concrete bounds and obstruction",
            "A convex physical region contains the full initial family and has proved "
            "curvature/flux bounds. An exact witness shows the present global viscosity "
            "criterion cannot certify the candidate's wave-speed recipe there.",
        ],
    ],
    [140, 365],
)
para("Principal-update energy estimate", "HeadingR")
para(
    "Write q = 1/ρ, e = (e<sub>q</sub>, e<sub>v</sub>, e<sub>p</sub>) and "
    "g<sub>q,p</sub>(e,e) = e<sub>p</sub>²/(2p) + |e<sub>v</sub>|²/q + "
    "(e<sub>q</sub>/q + e<sub>p</sub>/(2p))². Sum this over cells to obtain E. "
    "For the principal update, the proof gives<br/>"
    "<b>E<sub>after</sub> ≤ [1 + 756 Δt (256 B K + 32 D)] E<sub>before</sub>.</b>"
)
para(
    "Both energies use the old local metric. Premises include 1/4 ≤ q,p ≤ 4, "
    "|a<sub>d</sub>| + |v<sub>d</sub>| ≤ B, a valid CFL ratio, an identity central shift, "
    "and neighbor differences satisfying |Δq| + |Δp| ≤ hK and |Δv<sub>d</sub>| ≤ hD. "
    "Here Δt = ratio × h. The constant does not depend on the number of cells when "
    "B, K and D have uniform bounds. Proving such bounds, the time variation of the metric "
    "and the nonlinear remainder are outstanding steps."
)
para(
    "<b>Exact negative control:</b> with two cells, q = (1,2), p = 1, v = 0, "
    "directional speeds 2 and ratio 1/12, the CFL number is 1/2. A specific error field "
    "has energy 5 before and 125/16 = 7.8125 after the principal update. Thus a varying "
    "local metric need not contract. This error-field example does not replace the "
    "nonlinear Taylor–Green research family."
)

story.append(PageBreak())
para("Grid control and numerical evidence", "TitleR")
para(
    "The checked embedding gives |f(i,j,k)|² ≤ 8 E₃(f). In one dimension, "
    "E₁(f) = n⁻¹ Σ f² + n Σ(f<sub>k+1</sub> − f<sub>k</sub>)²; "
    "E₂ and E₃ apply this construction recursively in the other directions. "
    "It contains the eight mixed differences with each coordinate differentiated at most "
    "once, scaled to the unit cube. The constant 8 is independent of n. "
    "This controls values from derivative energies; it does not bound those energies "
    "along the Euler evolution."
)
para("Independent candidate checks", "HeadingR")
para(
    f"Initial cell averages agree with independent eight-point-per-axis Gauss quadrature to "
    f"{numeric['cell_average_quadrature_max_error']:.2e} in the tested cells. "
    f"A randomized admissible-field update has conservation drift "
    f"{numeric['random_state_update_conservation_error']:.2e}. "
    "An intentionally too-small split speed gives pressure −49, independently reproduced "
    "by Lean. These checks do not certify floating-point error or continuum accuracy."
)
rows = [["n", "A / δ", "Steps", "min ρ", "min p", "max |v_z|"]]
for row in numeric["rows"]:
    rows.append(
        [
            row["n"],
            f"{row['A']:g} / {row['delta']:g}",
            row["steps"],
            f"{row['min_density']:.6f}",
            f"{row['min_pressure']:.6f}",
            f"{row['vertical_velocity_max']:.6f}",
        ]
    )
table(rows, [35, 100, 45, 105, 105, 115])
para(
    "All six runs end at T = 0.25. They show evolving vertical velocity and admissible "
    "sampled states on two grids. Their success neither proves the full parameter family "
    "remains smooth nor supplies an exact continuum reference. No speedup or optimality "
    "claim is inferred from these runs."
)
para("Reproducibility and next proof obligations", "HeadingR")
para(
    "The source is under demos/lean_euler/nonlinear/formal. record/solver contains the "
    "frozen assembled Lean input, generated audit, logs, result JSON, component hashes, "
    "numerical checks and local-lab job receipts. The Python method is not a verified "
    "extraction of the Lean definitions."
)
para(
    "Run from the repository root with a new output directory:<br/>"
    ".venv/bin/python demos/lean_euler/nonlinear/run_solver_study.py<br/>"
    "--output artifacts/nonlinear-energy-replay"
)
para(
    "The next required bridge is quantitative regularity and a stability/error estimate "
    "for the actual nonlinear update. Initialization and continuous reconstruction must "
    "then be connected to the evolved PDE solution. A complete cost model and a matching "
    "necessary-accuracy lower bound remain essential before the goal can be completed."
)
para(
    f"Assembled proof SHA-256: {proof['source_sha256'][:32]}<br/>"
    f"{proof['source_sha256'][32:]}<br/>"
    'Draft PR: <link href="https://github.com/tomzhu0225/simjecture/pull/90">'
    "github.com/tomzhu0225/simjecture/pull/90</link>",
    "SmallR",
)

story.append(PageBreak())
para("Entropy: the proposed error mechanism", "TitleR")
para(
    "For γ = 2, the mathematical entropy is η(U) = −ρ log(p/ρ²). Lean now checks "
    "its actual gradient and Hessian, convexity on the admissible conserved-state set, "
    "and the local entropy balance that follows from differentiable Euler balance. "
    "The Hessian was derived from η, not defined as a convenient positive form. "
    "Existence of a smooth solution and the periodic integral conservation theorem "
    "are still required."
)
para(
    "A further checked result says a finite averaging map with nonnegative weights and "
    "unit row/column sums cannot increase this convex entropy. A bridge to the actual "
    "continuous output reconstruction remains unfinished."
)
story.append(Image(str(figures / "entropy_loss.png"), width=505, height=505 * 3 / 8.7))
story.append(Spacer(1, 8))
para(
    "<b>Observed quantities, not certified continuum errors.</b> Nine runs of the actual "
    "Rusanov update use n = 16, 32, 64, CFL = 0.3 and T = 0.25. Entropy loss is measured "
    "between discrete initial and final states. R is relative entropy about the conserved "
    "grid mean. The scaled h line is a visual guide; no rate or proof constant is inferred "
    "from this finite sample.",
    "SmallR",
)
rows = [["A / δ (n = 64)", "Entropy loss / h", "R(T) / R(0)", "Min observed drop / (Δt h R)"]]
for row in entropy_record["rows"]:
    if row["n"] == 64:
        rows.append(
            [
                f"{row['A']:g} / {row['delta']:g}",
                f"{row['entropy_loss_over_dx']:.6f}",
                f"{row['relative_entropy_final'] / row['relative_entropy_initial']:.6f}",
                f"{row['minimum_drop_over_dt_dx_relative']:.6f}",
            ]
        )
table(rows, [120, 120, 115, 150])
para(
    "<b>Remaining argument.</b> Develop a sharper finite-step estimate compatible with "
    "the candidate, and prove the uniform trajectory conditions. Connect accumulated "
    "loss to final continuum error through proved state bounds and the reconstruction. "
    "Only then could a necessary mesh resolution support a total-work lower bound. "
    "The data above do not discharge any of these obligations."
)
para(
    "The initial search scope includes higher-order methods; first-order Rusanov cannot "
    "be declared optimal in that scope without further argument. The proposed LF/Rusanov "
    "class with convex reconstruction is still under investigation, with explicit "
    "initial formulas and all preprocessing available to competitors."
)
para(
    'Reference: <link href="https://www.math.umd.edu/~tadmor/pub/TV%2Bentropy/'
    'Tadmor_Acta2003.pdf">Tadmor, Acta Numerica 12 (2003), §§7–8</link>, on the '
    "balance between spatial entropy dissipation and explicit time discretization. "
    "The reference is not imported as a Lean theorem.",
    "SmallR",
)

story.append(PageBreak())
para("A checked finite-step theorem", "TitleR")
para(
    "The new theorem concerns the actual nonlinear Rusanov finite-volume update. "
    "It includes explicit time discretization. It is a conditional method theorem; "
    "the required uniform trajectory membership and a useful certified parameter "
    "choice remain to be established. Concrete region constants and their limitation "
    "are checked on the following page."
)
para("The region conditions", "HeadingR")
para(
    "Let K be a convex set of positive-density, positive-pressure conserved states. "
    "Both the old and the updated cell states must lie in K. Throughout K, for every "
    "conserved-state tangent k, require<br/>"
    "λ |k|² ≤ D²η(U)[k,k] ≤ M |k|²,<br/>"
    "and |F<sub>d</sub>(V) − F<sub>d</sub>(U)|² ≤ L² |V − U|² for every direction. "
    "These are bounds on the actual physical entropy Hessian and flux, using the "
    "sum of the five squared nondimensional components. They are not numerical "
    "error estimates supplied as assumptions."
)
para("The viscosity and timestep conditions", "HeadingR")
para(
    "Here viscosity refers to artificial diffusion in the numerical face flux: "
    "the Rusanov term is −(a<sub>d</sub>/2)(U<sub>right</sub> − U<sub>left</sub>). "
    "It is not physical fluid viscosity. The target PDE remains inviscid 3D Euler."
)
para(
    "Write r = Δt/h and 0 &lt; a<sub>min</sub> ≤ a<sub>d</sub> ≤ a<sub>max</sub> "
    "for the directional global viscosities. A sufficient pair of conditions is<br/>"
    "M(1 + L²) ≤ a<sub>min</sub>λ/2,<br/>"
    "3 M r (a<sub>max</sub>² + L²) ≤ a<sub>min</sub>λ/8."
)
para(
    "With H<sub>total</sub> = Σ<sub>cells</sub> η(U) and "
    "J = Σ<sub>forward periodic faces</sub> |U<sub>right</sub> − U<sub>left</sub>|², "
    "Lean proves<br/><b>H<sub>total</sub>(after) ≤ H<sub>total</sub>(before) "
    "− (r a<sub>min</sub> λ/8) J.</b>"
)
para("How the proof connects to the update", "HeadingR")
table(
    [
        ["Checked piece", "Role"],
        [
            "Actual entropy calculus",
            "The derivative of the actual entropy gradient pairs with the Euler flux "
            "to give the momentum component of the tangent.",
        ],
        [
            "Rusanov face residual",
            "The Hessian and flux bounds control the central flux term; sufficiently "
            "large LF viscosity supplies a negative quadratic face contribution.",
        ],
        [
            "Periodic sum and finite step",
            "The entropy potential telescopes. A six-neighbor quadratic bound and an "
            "actual Hessian-based Taylor estimate control temporal entropy production.",
        ],
    ],
    [155, 350],
)
para(
    "<b>Practical limitation.</b> On the concrete region considered next, this "
    "sufficient viscosity criterion cannot certify the current wave-speed recipe, "
    "even with improved global curvature constants. A smaller timestep alone cannot "
    "resolve that viscosity condition. This does not refute the solver's actual "
    "entropy behaviour. Uniform trajectory bounds, continuum error and work "
    "optimality remain unproved."
)

story.append(PageBreak())
para("Concrete bounds and a<br/>proof-method obstruction", "TitleR")
para(
    "Lean now checks a concrete convex region K of conserved states with "
    "1/4 ≤ ρ ≤ 4, total energy density E ≤ 4, and p ≥ 1/4. "
    "It implies p ≤ 4 and |v|² ≤ 30. The complete initial family belongs to K "
    "for every allowed A, δ and every spatial point. This is initial membership, "
    "not invariance during the nonlinear evolution."
)
para("Explicit bounds, derived from the physical definitions", "HeadingR")
para(
    "Throughout K, the checked constants are λ = 1/12500, M = 100000 and L = 1200. "
    "The Hessian is the actual conserved-variable entropy Hessian. The finite flux "
    "bound follows from proved physical-flux derivatives and the mean value theorem. "
    "The constants are deliberately coarse. Inserting them into the preceding "
    "viscosity criterion would require a ≥ 3,600,002,500,000,000, which is not a "
    "useful certificate for the present method."
)
para("Improving those constants alone is insufficient on K", "HeadingR")
para(
    "The rest state U* = (1,0,0,0,1) belongs to K and occurs in every member of "
    "the actual initial family at (0, π/2, π/2). Lean checks two exact directional "
    "Hessian values there:"
)
table(
    [
        ["Direction k", "|k|²", "D²η(U*)[k,k]", "Necessary bound"],
        ["(1,0,0,0,2)", "5", "2", "λ ≤ 2/5"],
        ["(2,0,0,0,−1)", "5", "13", "M ≥ 13/5"],
    ],
    [170, 55, 130, 150],
)
para(
    "For every state in K, each physical directional wave speed is at most 12. "
    "Therefore the candidate's computed global directional speeds are at most 12 "
    "whenever its grid states are in K. The sufficient condition then has a left "
    "side M(1+L²) ≥ 13/5 and a right side aλ/2 ≤ 12/5. It is impossible. "
    "This obstruction holds for any valid global curvature constants on K, not "
    "only the coarse numerical values above."
)
para(
    "<b>Meaning.</b> This rules out certifying the candidate with this particular "
    "global sufficient criterion on K. It does not prove the numerical method "
    "unstable, falsify the observed entropy loss, or show that Euler solver "
    "optimality is impossible. The physical problem and accuracy goal are unchanged."
)
para(
    "<b>Next direction.</b> The alternative flux on the following page cancels the "
    "central face entropy residual exactly, avoiding this criterion. Uniform regularity, "
    "common smooth existence to T = 0.25, continuous reconstruction, full nonlinear "
    "accuracy and matching work bounds still require proof."
)

story.append(PageBreak())
para("An alternative with a<br/>terminating one-step search", "TitleR")
para(
    "The new candidate uses Chandrashekar's existing logarithmic-mean entropy-conservative "
    "flux, plus −(a<sub>d</sub>/2)(U<sub>R</sub>−U<sub>L</sub>). It changes the numerical "
    "method; no exact equivalence to the Rusanov baseline or speedup is claimed. "
    "The physical PDE remains inviscid Euler."
)
para("What the new Lean proof establishes", "HeadingR")
para(
    "The actual five-component flux satisfies the physical Euler consistency and "
    "canonical entropy jump identities in all three directions. Its dissipative face "
    "residual is nonpositive for <b>any nonnegative a<sub>d</sub></b>. This eliminates "
    "the large-diffusion condition of the previous face estimate."
)
para(
    "For any finite admissible periodic grid, define D as the sum of "
    "(a<sub>d</sub>/2) Δη′ · ΔU over forward faces, and H = Ση(U). Freeze the old-state "
    "residual while halving a positive trial ratio r = Δt/h. Accept a trial only when "
    "every cell has positive density and pressure and<br/>"
    "<b>H(U<sub>trial</sub>) ≤ H(U) − rD/2.</b>"
)
para(
    "Lean proves that the derivative of trial entropy at r = 0 is −D. For D &gt; 0, "
    "sufficiently small positive trials pass. For D = 0 with positive coefficients, "
    "strict entropy-gradient monotonicity forces equal states across neighboring faces; "
    "the residual is then zero. Thus <b>a finite real-arithmetic halving search succeeds</b>. "
    "The first accepted positive step preserves all conserved totals, admissibility "
    "and the finite-step entropy inequality; earlier trials fail its acceptance test."
)
para("Independent numerical checks", "HeadingR")
para(
    "Logarithmic means are compared with 70-digit arithmetic. An independent complex-step "
    "entropy gradient checks 1,024 random state pairs in all directions. The maximum "
    f"scaled entropy-identity residual is {ec_record['tadmor_identity_max_scaled_error']:.2e}. "
    "An excessive proposal triggers two halvings; a constant-state control stays unchanged."
)
table(
    [["A / δ at n = 64", "Accepted steps", "Rejected", "Min ρ / min p"]]
    + [
        [
            f"{row['A']:g} / {row['delta']:g}",
            row["steps"],
            row["rejected_steps"],
            f"{row['min_density']:.5f} / {row['min_pressure']:.5f}",
        ]
        for row in ec_record["rows"]
        if row["n"] == 64
    ],
    [145, 110, 80, 170],
)
para(
    "All nine 16³/32³/64³ runs reach T = 0.25 with ordinary wave-speed diffusion and "
    "CFL = 0.3, without rejected trials. All sampled entropy margins are nonnegative. "
    "These are finite observations, not universal accuracy or cost bounds.",
    "SmallR",
)
para(
    "<b>Remaining gap.</b> The theorem uses exact real comparisons, not verified "
    "floating-point guards. It gives no uniform retry/timestep bound, no guarantee for "
    "Python's cap of 60 halvings, and no proof of reaching T in finitely many steps. "
    "Continuum accuracy, complete computational work and a matching competitor lower "
    "bound remain unproved. Page 8 adds explicit per-state step/retry bounds; "
    "uniform trajectory control remains open."
)
para(
    'Reference: <link href="https://arxiv.org/pdf/1209.4994">Chandrashekar (2013), '
    "section 4.4</link>. Sources: LogMean.lean, EntropyConservativeFlux.lean, "
    "EntropyCandidateStep.lean. Retained evidence: record/solver, including "
    f"ec-validation.json and the {len(proof['theorems'])}-statement audit.",
    "SmallR",
)

story.append(PageBreak())
para("Quantitative step and<br/>retry bounds", "TitleR")
para(
    "The new proof bounds the accepted timestep and the number of halvings from the "
    "current grid state. It uses the actual directional entropy curvature, avoiding "
    "the earlier coarse global Hessian constant. The numerical method is unchanged."
)
para("Bounds derived from the conserved variables", "HeadingR")
para(
    "For one cell, write U = (ρ,m,E) and let k be its frozen update residual. Define<br/>"
    "Q = 2ρE − |m|² = 2ρp,<br/>"
    "Q₁ = 2k<sub>ρ</sub>E + 2ρk<sub>E</sub> − 2m·k<sub>m</sub>,<br/>"
    "Q₂ = 2k<sub>ρ</sub>k<sub>E</sub> − |k<sub>m</sub>|², and W = |Q₁| + 2|Q₂|."
)
para(
    "Along U + sk, the pressure polynomial is exactly Q + sQ₁ + s²Q₂. With<br/>"
    "R = 1 / {2[1 + max<sub>cells</sub>(|k<sub>ρ</sub>|/ρ + (|Q₁|+|Q₂|)/Q)]},<br/>"
    "Lean proves positive density/pressure for every 0 ≤ s ≤ R. The actual entropy "
    "second directional derivative is at most the explicit cell value<br/>"
    "b = 6k<sub>ρ</sub>²/ρ + 4|k<sub>ρ</sub>|W/Q + 6ρ|Q₂|/Q + 6ρ(W/Q)²."
)
para("The resulting quantitative guarantee", "HeadingR")
para(
    "Let B = Σb and let D be the face entropy dissipation from page 7. For D &gt; 0, "
    "set c = min(R, D/(B+D)). Lean proves c &gt; 0 and<br/>"
    "H(U+rk) ≤ H(U) − rD + r²B/2 for 0 ≤ r ≤ R.<br/>"
    "Every 0 ≤ r ≤ c therefore passes the positivity/entropy acceptance test."
)
para(
    "For a positive proposed ratio r₀, the first accepted halving index is at most "
    "<b>N = clog₂(ceil(r₀/c))</b>, where clog₂(n) is the least integer N ≥ 0 with "
    "n ≤ 2ᴺ. The accepted ratio is at least <b>min(r₀,c/2)</b>. When D = 0, the "
    "stationary update accepts the original proposal with zero halvings."
)
para("Numerical evaluation of the bound", "HeadingR")
rows = [["Cells per axis", "Largest proposed r₀/c", "Predicted / actual halvings"]]
for n in [16, 32, 64]:
    selected = [row for row in step_record["rows"] if row["n"] == n]
    rows.append(
        [
            n,
            f"{max(row['max_proposal_over_cap'] for row in selected):.4f}",
            f"{max(row['max_predicted_halvings'] for row in selected)} / "
            f"{max(row['max_actual_halvings'] for row in selected)}",
        ]
    )
table(rows, [110, 175, 220])
para(
    "These nine trajectories use ordinary wave speeds, CFL = 0.3 and T = 0.25. "
    "An excessive proposal has a bound of six halvings and actually uses two. "
    "Independent complex-step Hessians on 2,048 random states and five trial positions "
    "agree with the polynomial expression to "
    f"{step_record['hessian_complex_step_max_scaled_error']:.2e} "
    "maximum scaled error. The solver does not execute this diagnostic bound.",
    "SmallR",
)
para(
    "<b>What remains.</b> The cap is proved from each current state. There is no proved "
    "uniform lower bound for it over the entire evolving parameter family and all meshes. "
    "Floating-point evaluations are not certified enclosures. Target-time completion, "
    "continuum accuracy, complete computational work and matching optimality remain open."
)
para(
    "Sources: PressurePolynomial.lean and EntropyStepBounds.lean. Five bounded jobs "
    "replay the current audit and numerical diagnostics; step-bound-validation.json "
    "retains the new measurements and their source hashes.",
    "SmallR",
)
SimpleDocTemplate(
    str(HERE / "report.pdf"),
    pagesize=A4,
    leftMargin=44,
    rightMargin=44,
    topMargin=40,
    bottomMargin=44,
    title="Nonlinear 3D Euler: checked solver foundations",
    author="Simjecture research record",
).build(story, onFirstPage=page_number, onLaterPages=page_number)
print(HERE / "report.pdf")
