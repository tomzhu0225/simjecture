"""Render the preliminary 3D Euler report from the retained experimental record.

Run with reportlab 4.4.5 installed; no remote service is used.
"""

# Long report paragraphs retain deliberate inline markup.
# ruff: noqa: E501
import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("report.pdf"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    r = json.loads((root / "record/optimization.json").read_text())
    font_root = Path("/usr/share/fonts/truetype/dejavu")
    pdfmetrics.registerFont(TTFont("Body", str(font_root / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("BodyBold", str(font_root / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily(
        "Body", normal="Body", bold="BodyBold", italic="Body", boldItalic="BodyBold"
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Text", fontName="Body", fontSize=9.5, leading=14, spaceAfter=9))
    styles.add(
        ParagraphStyle(
            "Title3D",
            fontName="BodyBold",
            fontSize=25,
            leading=31,
            spaceAfter=18,
            textColor=colors.HexColor("#163D4A"),
        )
    )
    styles.add(
        ParagraphStyle(
            "Sub3D", fontName="BodyBold", fontSize=13, leading=18, spaceBefore=14, spaceAfter=9
        )
    )
    styles.add(ParagraphStyle("Tiny", fontName="Body", fontSize=7.8, leading=11, spaceAfter=8))
    styles.add(
        ParagraphStyle(
            "Kicker",
            fontName="BodyBold",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#33796F"),
            spaceAfter=10,
        )
    )
    story = []

    def p(text, style="Text"):
        story.append(Paragraph(text, styles[style]))

    def table(rows, widths):
        items = [[Paragraph(escape(str(v)), styles["Tiny"]) for v in row] for row in rows]
        t = Table(items, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4EEEF")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#33796F")),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#CDD8DC")),
                ]
            )
        )
        story.append(t)

    p("SIMJECTURE × LEAN  /  LOCAL RESEARCH RECORD  /  2026-11-01", "Kicker")
    p("3D Euler: the first<br/>optimization experiment", "Title3D")
    p("A staged investigation of optimal solvers within a restricted class.", "Sub3D")
    p(
        "<b>Current result:</b> caching old-state thermodynamics preserved every tested update and reduced one-step CPU time. <b>No 3D Euler solver optimality theorem has been proved.</b>"
    )
    p("The first gate", "Sub3D")
    p(
        "The experiment asks a deliberately bounded question: can an AI-assisted workflow improve the implementation of a fixed three-dimensional fluid discretization, preserve its output, and retain enough evidence to support a later proof? It does not yet search over numerical methods or establish the fastest route to a given PDE accuracy."
    )
    table(
        [
            ["Item", "Fixed contract"],
            [
                "Equations",
                "3D compressible Euler; ideal gas; gamma = 2; density, three momenta, total energy",
            ],
            [
                "Discretization",
                "Uniform periodic Cartesian grid; first-order shared-face Rusanov flux; forward Euler",
            ],
            [
                "Candidate change",
                "Compute pressure and sound speed once from the old state; reuse them for x, y and z fluxes",
            ],
            [
                "Output requirement",
                "Same complete discrete update for the same state and supplied timestep",
            ],
            [
                "Measured objective",
                "CPU time per full update kernel, including cache and output allocation",
            ],
        ],
        [36 * mm, 133 * mm],
    )
    p("Why this is a first step", "Sub3D")
    p(
        "The previous 1D Poisson baseline had a direct linear solve and an output-size lower bound. Those facts do not transfer to a full nonlinear Euler evolution. The present candidate changes implementation work only. A broader claim will need its own algorithm class, accuracy contract, and lower bound."
    )
    story.append(PageBreak())
    p("Measured evidence", "Title3D")
    p(
        "One warm-up call per kernel; 11 timing trials per grid; deterministically shuffled execution order. Times include cache creation and returned-array allocation. Timestep selection and validation are outside the timing interval."
    )
    rows = [["Grid", "Reference (ms)", "Cached (ms)", "Ratio"]]
    for t in r["timings"]:
        rows.append(
            [
                f"{t['n']}³",
                f"{1000 * t['median_seconds']['reference']:.3f}",
                f"{1000 * t['median_seconds']['cached']:.3f}",
                f"{t['reference_over_cached']:.3f}×",
            ]
        )
    table(rows, [28 * mm, 48 * mm, 48 * mm, 45 * mm])
    p("Update and admissibility checks", "Sub3D")
    rows = [["Input", "Grid / steps", "Equality", "Minimum rho / p"]]
    for c in r["equivalence_checks"]:
        rows.append(
            [
                c["kind"],
                f"{c['n']}³ / {c['steps']}",
                "Bitwise identical" if c["bitwise_equal"] else "See record",
                f"{c['min_density']:.4f} / {c['min_pressure']:.4f}",
            ]
        )
    table(rows, [32 * mm, 35 * mm, 51 * mm, 51 * mm])
    drift = max(abs(v) for c in r["equivalence_checks"] for v in c["conserved_total_drift"])
    p(
        f"All checked steps retained positive density and pressure. The largest absolute drift of a volume-weighted conserved total was {drift:.2e}. Pressure and sound-speed evaluations decrease from 3N to N by source inspection; this count has not been proved minimal."
    )
    p("What these measurements do not establish", "Sub3D")
    p(
        "The random and coupled cases exercise nonlinear three-dimensional states. The spherical pressure blast is an execution/admissibility check without an independently validated shock solution. There is no convergence result for these cases. Bitwise equality on finite tests is not an all-state formal equivalence theorem."
    )
    p(
        "The timing ratio compares two NumPy implementations on one CPU host. It does not prove a best constant, end-to-end speedup, GPU advantage, or optimal time to a prescribed error. The roughly 1.05× result at 32³ is small enough to warrant repetition under controlled host load."
    )
    p(escape(r["environment"]["platform"]), "Tiny")
    p(
        "Host: AMD Ryzen 9 9900X. Python "
        + escape(r["environment"]["python"])
        + "; NumPy "
        + escape(r["environment"]["numpy"])
        + ". This experiment uses CPU execution.",
        "Tiny",
    )
    story.append(PageBreak())
    p("Proof gates and replay", "Title3D")
    table(
        [
            ["Gate", "Required evidence", "Status"],
            [
                "1. Preserve the update",
                "Frozen source, nonlinear 3D trajectories, conservation/admissibility checks, all timing trials",
                "Empirically passed",
            ],
            [
                "2. Formalize implementation",
                "Actual Euler flux; admissibility assumptions; exact-arithmetic cache equivalence; allowed dataflow transformations; meaningful cost lower bound",
                "Next",
            ],
            [
                "3. Solve to an error target",
                "Manufactured smooth solutions, independent shock references, refinement studies, all timesteps and setup costs",
                "Open",
            ],
            [
                "4. Discover broader methods",
                "New flux/reconstruction/time-integrator candidates, certified counterexamples, matched-accuracy baselines, new lower bounds",
                "Open-ended",
            ],
        ],
        [36 * mm, 104 * mm, 29 * mm],
    )
    p(
        "The next theorem must be named at its actual scope. A minimum count of thermodynamic evaluations would establish that subproblem's optimum, not optimality of an entire fluid solver. If only a linear output-size bound is available, the report must say so."
    )
    p("Reproduce locally", "Sub3D")
    p(
        "From the repository root:<br/><font size='8'>.venv/bin/python demos/lean_euler/optimization/run_local.py<br/>--output artifacts/lean-euler/optimization-replay-001</font>"
    )
    p(
        "Choose a new output directory. The driver submits an exploratory Simjecture lab job, freezes experiment.py and euler.py, and retains the receipt and optimization.json. The committed record stores all samples and the source SHA256 hashes. The study has no independent scientific review."
    )
    p("Sources and provenance", "Sub3D")
    p(
        "The candidate and measured evidence are in PR #90: <link href='https://github.com/tomzhu0225/simjecture/pull/90'>github.com/tomzhu0225/simjecture/pull/90</link>. The PR is draft while the 3D research develops.",
        "Tiny",
    )
    p(
        "[1] X. Zhang and C.-W. Shu (2010), positivity-preserving Euler schemes on rectangular meshes. This provides established context for separate admissibility arguments, not an optimality proof for this candidate. <link href='https://www.math.purdue.edu/~zhan1966/research/paper/euler.pdf'>Author-hosted paper</link>.",
        "Tiny",
    )
    p(
        "[2] Clawpack, Riemann solvers: directional interface solvers in multidimensional methods. <link href='https://www.clawpack.org/riemann.html'>Official documentation</link>.",
        "Tiny",
    )
    for name, digest in r["source_sha256"].items():
        p(escape(name) + " SHA256:<br/>" + digest, "Tiny")

    def footer(canvas, doc):
        canvas.setFont("Body", 7.5)
        canvas.setFillColor(colors.HexColor("#64777D"))
        canvas.drawString(
            20 * mm,
            13 * mm,
            "Simjecture research record · Preliminary 3D stage 1 · No optimality claim",
        )
        canvas.drawRightString(190 * mm, 13 * mm, str(doc.page))

    document = SimpleDocTemplate(
        str(args.output),
        pagesize=(210 * mm, 297 * mm),
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=19 * mm,
        bottomMargin=23 * mm,
        title="3D Euler optimization: first restricted experiment",
        author="Simjecture research record",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print(args.output)


if __name__ == "__main__":
    main()
