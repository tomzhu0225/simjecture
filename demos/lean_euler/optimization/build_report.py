"""Render the 3D Euler report from retained empirical and formal records.

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
    formal = json.loads((root / "formal/record/formal-results.json").read_text())
    instrument = json.loads((root / "formal/record/instrumentation.json").read_text())
    assert all(item["checked"] for item in formal.values())
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
    p("3D Euler cache:<br/>equivalence and a scoped optimum", "Title3D")
    p("A staged investigation of optimal solvers within a restricted class.", "Sub3D")
    p(
        "<b>Current result:</b> Lean checks exact-arithmetic cache equivalence, conservation, and minimum thermodynamic-call cost within a fixed schedule interface. CPU timing separately shows a 1.05–1.25× one-step speedup. <b>Optimal time to solve the Euler PDE at a given accuracy remains open.</b>"
    )
    p("The fixed problem", "Sub3D")
    p(
        "The investigation improves the implementation of a fixed three-dimensional fluid discretization and now checks a model of that change formally. It does not search over numerical methods or establish the fastest route to a given PDE accuracy. The proof, executable correspondence checks, and hardware measurements remain separate evidence layers."
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
    p("What has and has not been proved", "Sub3D")
    p(
        "The formal result is over real-valued five-component states, arbitrary periodic neighbor permutations, and supplied timestep/grid ratios. The cache must be fresh. Neither positivity after a step nor PDE convergence follows from equality with the original scheme. Python execution, floating-point rounding, and compiler behavior are not formally refined to the Lean model."
    )
    story.append(PageBreak())
    p("The Lean-checked result", "Title3D")
    p(
        "Fifteen named theorems passed compilation and an independent transitive-axiom audit in Simjecture's bounded capability sandbox. Their only recorded axioms are propext, Classical.choice, and Quot.sound. Both model files, generated audits, logs, hashes, and job receipts are retained under formal/record/."
    )
    p("Exact-arithmetic equivalence", "Sub3D")
    p(
        "EulerCache.lean defines pressure, sound speed, physical flux, the spectral bound, Rusanov face flux, and both three-axis updates. Fresh-cache substitution proves equality at every cell and component. A second theorem proves equality for every finite number of fixed-ratio steps with a fresh cache each step. The concrete cached update conserves all five component totals on finite periodic grids."
    )
    p("Restricted schedule model", "Sub3D")
    p(
        "Eval(i) creates a thermodynamic pair from the immutable old state. Use(a,i) requires that pair to be present. Drop(i) evicts it. The cache starts empty, and all three directions at every cell must be used. Only Eval creates data: algebraic bypasses, half-pair caching, cross-cell reuse, warm starts, and changed numerical methods are excluded. Availability is modeled separately from the fresh-value condition in the equivalence proof."
    )
    table(
        [
            ["Quantity", "Reference", "Cached"],
            ["Thermodynamic evaluations", "3N", "N"],
            ["Directional Uses (single pass)", "3N", "3N"],
            ["Weighted library cost", "(3t + 3f)N", "(t + 3f)N"],
        ],
        [75 * mm, 47 * mm, 47 * mm],
    )
    p(
        "Every consumed cell must first be evaluated. Counting distinct evaluated cells yields the lower bound N; the cached schedule attains it. With nonnegative integer costs t per Eval, f per Use, and d per Drop, it minimizes weighted cost among legal, complete schedules with exactly 3N Uses. The saving is 2tN, strictly positive when t>0 and N>0. The unchanged face/update work is not counted; adding an identical common cost preserves the comparison."
    )
    p("Connection to NumPy", "Sub3D")
    p(
        f"Instrumentation observes 3N versus N pressure/square-root evaluations at 3³, 8³, and 16³. The scalar transcription of the Lean formula matches the tested NumPy update (maximum difference {instrument['scalar_model_transcription_max_difference']:.1e}). Deliberately stale pressure changes the result by {instrument['stale_pressure_negative_control_max_difference']:.3e}; omitting an Eval is rejected by the schedule interpreter. These are empirical correspondence checks, not a compiler or floating-point proof."
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
        f"All checked steps retained positive density and pressure. The largest absolute drift of a volume-weighted conserved total was {drift:.2e}. The 3N-to-N evaluation reduction is now instrumented, and N is proved minimal within the restricted schedule interface."
    )
    p("What these measurements do not establish", "Sub3D")
    p(
        "The random and coupled cases exercise nonlinear three-dimensional states. The spherical pressure blast is an execution/admissibility check without an independently validated shock solution. There is no convergence result for these cases. The real-valued all-state model equivalence is separately proved; these finite tests do not establish IEEE floating-point equivalence for all inputs."
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
                "Proved in scoped model",
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
        "The achieved optimum concerns caching schedules in a fixed kernel interface. It is a dependency lower bound, not a lower bound for every possible Euler algorithm. Nonuniform memory costs, cache capacity, algebraic transformations outside the interface, numerical accuracy, and total simulation work require further analysis."
    )
    p("Reproduce locally", "Sub3D")
    p(
        "From the repository root, run stage 1 with optimization/run_local.py. For the new proof and instrumentation jobs:<br/><font size='8'>.venv/bin/python demos/lean_euler/optimization/formal/run_local.py<br/>--output artifacts/lean-euler/formal-replay-001</font>"
    )
    p(
        "Choose a new output directory. The formal driver submits two exploratory lab jobs, freezes the Lean/Python sources, and retains formal-results.json, instrumentation.json and receipts. The records distinguish proved, empirical and open claims. This is assistant-authored scripted formalization without independent scientific review or autonomous algorithm discovery."
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
            "Simjecture research record · Stages 1–2 · Scoped cache optimum, not Euler PDE optimality",
        )
        canvas.drawRightString(190 * mm, 13 * mm, str(doc.page))

    document = SimpleDocTemplate(
        str(args.output),
        pagesize=(210 * mm, 297 * mm),
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=19 * mm,
        bottomMargin=23 * mm,
        title="3D Euler cache: equivalence and scoped cost optimality",
        author="Simjecture research record",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print(args.output)


if __name__ == "__main__":
    main()
