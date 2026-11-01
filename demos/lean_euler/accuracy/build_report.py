"""Build the stage-3 PDF and standalone scientific figure from frozen records.

Optional dependencies: matplotlib, reportlab; uses system DejaVu fonts.
"""

# Long report paragraphs preserve intentional inline markup.
# ruff: noqa: E501
import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

LABELS = {
    "reference": "Original first order",
    "cached": "Cached first order",
    "fused": "Shared timestep/update",
    "muscl_rk2": "MUSCL / RK2",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("report.pdf"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    r = json.loads((root / "record/accuracy.json").read_text())
    audit = json.loads((root / "record/representation.json").read_text())
    checks = json.loads((root / "record/validation.json").read_text())
    ledger = json.loads((root / "record/ledger.json").read_text())
    proof = json.loads((root / "record/formal-results.json").read_text())
    assert all(p["checked"] for p in proof.values())
    figures = root / "figures"
    figures.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.1), constrained_layout=True)
    for method, label in LABELS.items():
        rows = [x for x in r["summary"] if x["method"] == method]
        x = [z["density_l1"] for z in rows]
        axes[0].loglog(x, [z["median_solver_seconds"] for z in rows], "o-", label=label, ms=4)
        axes[1].loglog(x, [z["eos_cell_evaluations"] for z in rows], "o-", label=label, ms=4)
    for ax in axes:
        ax.set_xlabel("Density L1 error in cell averages")
        ax.grid(True, which="both", alpha=0.18)
        for eps in r["contract"]["accuracy_targets"]:
            ax.axvline(eps, color="#777777", ls=":", lw=0.8)
    axes[0].set_ylabel("Complete solve time (s), median of 3")
    axes[1].set_ylabel("EOS evaluations of individual cells")
    axes[0].legend(fontsize=8, loc="lower left")
    fig.savefig(figures / "error_work.png", dpi=180)
    fig.savefig(figures / "error_work.pdf")
    plt.close(fig)
    font = Path("/usr/share/fonts/truetype/dejavu")
    pdfmetrics.registerFont(TTFont("Body", str(font / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("BodyBold", str(font / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily(
        "Body", normal="Body", bold="BodyBold", italic="Body", boldItalic="BodyBold"
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Text", fontName="Body", fontSize=9.2, leading=13.7, spaceAfter=8))
    styles.add(
        ParagraphStyle(
            "TitleA",
            fontName="BodyBold",
            fontSize=24,
            leading=30,
            spaceAfter=14,
            textColor=colors.HexColor("#143D4B"),
        )
    )
    styles.add(
        ParagraphStyle(
            "SubA", fontName="BodyBold", fontSize=12.5, leading=17, spaceBefore=11, spaceAfter=7
        )
    )
    styles.add(ParagraphStyle("TinyA", fontName="Body", fontSize=7.5, leading=10.5, spaceAfter=7))
    story = []

    def p(text, style="Text"):
        story.append(Paragraph(text, styles[style]))

    def table(rows, widths):
        t = Table(
            [[Paragraph(escape(str(v)), styles["TinyA"]) for v in row] for row in rows],
            colWidths=widths,
            repeatRows=1,
            hAlign="LEFT",
        )
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4EEEF")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#CAD6DA")),
                ]
            )
        )
        story.append(t)

    strict = {c["method"]: c["minimum_sampled_work"] for c in r["choices"] if c["epsilon"] == 0.005}
    speed = strict["fused"]["median_solver_seconds"] / strict["muscl_rk2"]["median_solver_seconds"]
    p("SIMJECTURE × LEAN  /  STAGE 3  /  2026-11-01", "TinyA")
    p("Total work at a<br/>specified solution error", "TitleA")
    p(
        f"<b>Measured result:</b> at absolute density L1 error ≤ 0.005, the sampled second-order method meets the cell-average target on 16³ cells; the first-order method needs 64³. It takes about <b>{speed:.1f}× less complete-solve time</b> than the improved first-order implementation in this smooth test. This is an empirical comparison, not a general optimality theorem."
    )
    p("The exact problem", "SubA")
    p(
        "A periodic unit cube contains a gamma=2 ideal gas with pressure 1, velocity (0.5, 0.2, −0.1), and density 1 + 0.1 sin[2π(x+y+z−0.6t)]. All five conserved variables are evolved to T=0.05. This is a transported entropy wave embedded in 3D, not a general nonlinear-interaction or shock test. It is an exact solution of the mathematical PDE; no experimental validation of the physical model is implied."
    )
    p(
        "The primary ruler compares exact cell averages: the sinusoidal amplitude is multiplied by sinc(1/n)³. Error targets 0.02, 0.01 and 0.005 are absolute nondimensional density errors. Target 0.005 is 0.5% of the mean density, not 0.5% relative to the perturbation. A separate reconstructed-field audit checks the representation issue."
    )
    table(
        [
            ["Method at target 0.005", "Grid", "Actual error", "Median solve (s)"],
            *[
                [
                    LABELS[m],
                    f"{strict[m]['n']}³",
                    f"{strict[m]['density_l1']:.6f}",
                    f"{strict[m]['median_solver_seconds']:.4f}",
                ]
                for m in LABELS
            ],
        ],
        [69 * mm, 24 * mm, 36 * mm, 40 * mm],
    )
    p("What changed from the earlier caching result", "SubA")
    p(
        "The full solve now counts initial-data construction, timestep selection, all stages, allocation, and per-step admissibility checks. The new first-order implementation shares thermodynamics between timestep selection and the update. The higher-order comparator uses MC-limited conservative reconstruction, Rusanov fluxes and SSPRK2. It intentionally changes the discretization; this is a standard-method comparison, not discovery of a novel algorithm."
    )
    story.append(PageBreak())
    p("The measured error–work frontier", "TitleA")
    story.append(Image(str(figures / "error_work.png"), width=170 * mm, height=66.4 * mm))
    p(
        "Each curve contains all six tested grids. Dashed lines mark the three tolerances. Lower error lies to the left. Timing is a median of three trials with shuffled method order; all trials are retained. These are candidate implementations on one non-isolated CPU host, not best-in-class production solvers.",
        "TinyA",
    )
    rows = [["Target", "First-order grid", "MUSCL/RK2 grid", "Status"]]
    for eps in r["contract"]["accuracy_targets"]:
        by = {c["method"]: c["minimum_sampled_work"] for c in r["choices"] if c["epsilon"] == eps}
        rows.append(
            [eps, f"{by['fused']['n']}³", f"{by['muscl_rk2']['n']}³", "Cell-average criterion"]
        )
    table(rows, [30 * mm, 42 * mm, 47 * mm, 50 * mm])
    p("Accounting is part of the ruler", "SubA")
    p(
        f"At target 0.005, the improved first-order solve uses {strict['fused']['cell_stage_updates']:,} cell-stage updates and {strict['fused']['eos_cell_evaluations']:,} EOS cell evaluations. MUSCL/RK2 uses {strict['muscl_rk2']['cell_stage_updates']:,} cell-stage updates and {strict['muscl_rk2']['eos_cell_evaluations']:,} EOS cell evaluations. A MUSCL stage costs more than a first-order stage: these proxies are not equal-cost FLOPs. Instrumentation independently verifies the EOS counts."
    )
    verified = {}
    for m in ["fused", "muscl_rk2"]:
        rows = [x for x in r["rows"] if x["method"] == m and x["n"] == strict[m]["n"]]
        verified[m] = float(np.median([x["solver_seconds"] + x["analysis_seconds"] for x in rows]))
    p(
        f"Including final analytic error analysis gives median solve-plus-analysis times of {verified['fused']:.4f} s and {verified['muscl_rk2']:.4f} s, respectively. Program startup, file writing and orchestration are outside these times and visible in the lab receipts."
    )
    c = ledger["calibration"]
    p(
        f"The primary 72-solve calibration sweep itself cost {c['solver_seconds']:.1f} s of solver time, {c['analysis_seconds']:.2f} s of error analysis, and {c['primary_job_wall_seconds']:.1f} s of lab-job wall time. It performed {c['cell_stage_updates']:,} cell-stage updates. Calibration and verification are not free and are not amortized into the selected single-solve times."
    )
    p(
        "All three first-order variants have identical recorded solution and timestep hashes. The second-order results have different errors and step counts. General positivity is not proved: reconstructed states, RK stages and completed steps are checked and invalid runs would be rejected."
    )
    story.append(PageBreak())
    p("Physical representation changes admission", "TitleA")
    p(
        "A small error in cell averages can hide subcell structure. The audit applies the same MC-limited piecewise-linear density reconstruction to selected outputs, then integrates absolute error numerically with tensor Gauss quadrature. Orders 3 and 5 are compared; this is not an interval-certified error bound."
    )
    table(
        [
            ["Method / grid", "Average L1", "Reconstructed L1", "Target / pass"],
            *[
                [
                    f"{LABELS[z['method']]} / {z['n']}³",
                    f"{z['cell_average_l1']:.6f}",
                    f"{z['reconstruction_l1_order5']:.6f}",
                    f"{z['epsilon']} / {'yes' if z['numerically_meets_reconstructed_target'] else 'no'}",
                ]
                for z in audit["cases"]
            ],
        ],
        [67 * mm, 32 * mm, 36 * mm, 34 * mm],
    )
    p(
        "The 8³ MUSCL result passes projected error 0.01 but fails reconstructed-field error 0.01. It must not be advertised as satisfying the latter. The selected 64³ first-order and 16³ second-order results still meet the numerical reconstructed target 0.005. The reconstruction cost is included in the separate single-solve audit; those single samples are not used as repeated timing evidence."
    )
    alias = audit["one_cell_projection_negative_control"]
    p(
        f"A sharper negative control has zero cell-average error on a one-cell grid but reconstructed density L1 error about {alias['reconstructed_l1']:.4f}. This demonstrates why output representation, resolution and error norm must all be specified before using a performance claim."
    )
    p("Reference and implementation audits", "SubA")
    p(
        f"An independent 8-point-per-axis quadrature checks the analytic cell-average formula to {checks['quadrature_max_error']:.2e} on the sampled cells. Comparing point samples with cell averages can differ by {checks['point_sample_vs_cell_average_max']:.3f}; the benchmark does not confuse the two. A run stopping before T=0.05 is rejected, and a coarse first-order run fails its tolerance as expected."
    )
    p(
        "Measured pressure and velocity drift remain at roundoff scale, and conservation diagnostics are retained for every case. These checks support the smooth-wave experiment. They do not validate shock accuracy, arbitrary physical observables, or the Euler model against laboratory measurements."
    )
    story.append(PageBreak())
    p("What is proved—and what is still open", "TitleA")
    p(
        "Twelve named theorems passed Lean and transitive-axiom audits in the bounded Simjecture executor. Only propext, Classical.choice and Quot.sound appear in the recorded dependencies. The theorem statements and hypotheses remain the authority."
    )
    table(
        [
            ["Formal artifact", "Checked result", "Scope"],
            [
                "ContactReference.lean",
                "Pressure/velocity embedding, algebraic residual reduction and component-error factors",
                "Density derivatives are supplied to the residual identity",
            ],
            [
                "WaveDerivative.lean",
                "Affine-phase sine derivative and transport-phase cancellation",
                "Scalar analytic reference ingredients",
            ],
            [
                "ErrorWork.lean",
                "Convex-stencil nonexpansiveness; error accumulation; error/work conversion",
                "Conditional hypotheses, not discharged for nonlinear Euler codes",
            ],
        ],
        [42 * mm, 67 * mm, 60 * mm],
    )
    p(
        "The conditional rule is: if initial error is zero, each step contributes at most C/n², and the run takes at most K n steps, then final error is at most K C/n. With m ≤ k n, the modeled work satisfies n³m ≤ k n⁴. A desired epsilon can therefore define a sufficient grid when the constants and hypotheses have actually been certified."
    )
    p(
        "<b>Those stability and local-defect hypotheses have not been established for the implemented Rusanov or MUSCL/RK2 solvers.</b> No measured convergence curve is promoted to a proof. The uniform-error lemma is also distinct from the measured L1 norm. There is no unconditional error certificate, floating-point refinement, or matching global lower bound here."
    )
    p("Replay and next proof target", "SubA")
    p(
        "<font size='8'>.venv/bin/python demos/lean_euler/accuracy/run_local.py<br/>--output artifacts/lean-euler/accuracy-replay-001</font>"
    )
    p(
        "Use a new output directory after installing the Lean capability. The replay runs the primary timing sweep before audit/proof workloads and retains all receipts, hashes, errors and failures. The next proof task is a certified stability/defect bound for a restricted Euler family or a certified case-specific error estimate. A smooth nonlinear vortex and validated shock test are the next empirical extensions."
    )
    p(
        "Sources: <link href='https://www.clawpack.org/riemann_book/html/Euler_approximate.html'>Clawpack's Euler/contact discussion</link>; <link href='https://www.clawpack.org/pyclaw/solvers.html'>official discussion of accuracy versus per-step cost</link>. We do not benchmark Clawpack here. Code, data and proof receipts: <link href='https://github.com/tomzhu0225/simjecture/pull/90'>draft PR #90</link>. This is scripted assistant-authored research without independent scientific review.",
        "TinyA",
    )

    def footer(canvas, doc):
        canvas.setFont("Body", 7)
        canvas.setFillColor(colors.HexColor("#68797D"))
        canvas.drawString(
            20 * mm,
            13 * mm,
            "Simjecture · Stage 3 · Measured accuracy/work; nonlinear convergence proof remains open",
        )
        canvas.drawRightString(190 * mm, 13 * mm, str(doc.page))

    doc = SimpleDocTemplate(
        str(args.output),
        pagesize=(210 * mm, 297 * mm),
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=19 * mm,
        bottomMargin=23 * mm,
        title="3D Euler: total work at prescribed solution error",
        author="Simjecture research record",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(args.output)


if __name__ == "__main__":
    main()
