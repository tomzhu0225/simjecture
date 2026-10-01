# ruff: noqa: E501  # Embedded visual text, ASS and HTML assets.
"""Original 1080p documentary graphics drawn from the frozen public dashboard."""

import io
import json
from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/benchmark-video-20261001"
DATA = json.loads(Path(__file__).with_name("content.json").read_text())
FACTS = json.loads((OUT / "facts.json").read_text())
TASK = {t["id"]: t for t in FACTS["tasks"]}
REGULAR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
BG = "#0a1221"
CARD = "#121f33"
FG = "#edf5ff"
MUTED = "#9eb2cc"
CYAN = "#45d5cd"
AMBER = "#ffbf69"
RED = "#f58390"
BLUE = "#8da6ff"
FONT = FontProperties(fname=REGULAR, size=18)
plt.rcParams.update(
    {
        "font.size": 18,
        "figure.facecolor": CARD,
        "axes.facecolor": CARD,
        "axes.labelcolor": FG,
        "text.color": FG,
        "xtick.color": MUTED,
        "ytick.color": FG,
        "axes.edgecolor": MUTED,
        "grid.color": "#2a3b52",
    }
)


# Model identity is consistent across the film. Backend is not a colour category.
MODEL_COLOURS = {
    "deepseek-flash": "#4da6ff",
    "deepseek-v4-pro": "#aabfff",
    "gpt-6-luna": "#00d9a6",
    "gpt-6.1-sol": "#b091ff",
    "gpt-6-astra": "#f280b5",
    "gemini-3.8-flash": "#ff7722",
    "gemini-3.7-flash": "#f29f66",
    "gemini-3.6-flash": "#ffc857",
    "gemini-3.1-pro": "#e4d975",
    "gpt-5.5": "#e6e1d4",
    "gpt-5.6-luna": "#46b8b4",
    "gpt-5.6-sol": "#d4c5a9",
    "gpt-5.6-terra": "#a7cb54",
    "gpt-6-sol": "#54c95a",
    "gpt-oss-120b-medium": "#a6cbd0",
    "gpt-reserve": "#c5bbc9",
    "grok-4.5": "#ec6c63",
    "grok-4.6": "#db869e",
    "grok-4.7": "#dc524c",
    "grok-4.7-build-fast": "#cc9661",
    "mimo-v2.6-flash": "#c1d971",
    "mimo-v2.6-pro": "#94c474",
    "claude-opus-4-6-thinking": "#ecafca",
    "claude-sonnet-4-6": "#d6b8ff",
    "glm-5.3": "#7996b5",
}
MODEL_NAMES = {
    "deepseek-flash": "DeepSeek Flash",
    "deepseek-v4-pro": "DeepSeek V4 Pro",
    "gpt-6-luna": "GPT 6 Luna",
    "gpt-6.1-sol": "GPT 6.1 Sol",
    "gpt-6-astra": "GPT 6 Astra",
    "gpt-5.5": "GPT 5.5",
    "gpt-5.6-luna": "GPT 5.6 Luna",
    "gpt-5.6-sol": "GPT 5.6 Sol",
    "gpt-5.6-terra": "GPT 5.6 Terra",
    "gpt-6-sol": "GPT 6 Sol",
    "gpt-reserve": "GPT Reserve",
    "gpt-oss-120b-medium": "GPT OSS 120B",
    "gemini-3.1-pro": "Gemini 3.1 Pro",
    "gemini-3.6-flash": "Gemini 3.6 Flash",
    "gemini-3.7-flash": "Gemini 3.7 Flash",
    "gemini-3.8-flash": "Gemini 3.8 Flash",
    "mimo-v2.6-flash": "MiMo 2.6 Flash",
    "mimo-v2.6-pro": "MiMo 2.6 Pro",
    "grok-4.5": "Grok 4.5",
    "grok-4.6": "Grok 4.6",
    "grok-4.7": "Grok 4.7",
    "grok-4.7-build-fast": "Grok 4.7 Build Fast",
    "claude-opus-4-6-thinking": "Claude Opus 4.6 thinking",
    "claude-sonnet-4-6": "Claude Sonnet 4.6",
    "glm-5.3": "GLM 5.3",
}
assert len(set(MODEL_COLOURS.values())) == len(MODEL_COLOURS)
assert {r["family_label"] for t in TASK.values() for r in t["rows"]} <= MODEL_COLOURS.keys()
MARKERS = {
    name: ["o", "s", "D", "^", "v", "P", "X", "h", "p", "*"][i % 10]
    for i, name in enumerate(sorted(MODEL_COLOURS))
}
MARKERS.update(
    {
        "deepseek-flash": "D",
        "gpt-6-luna": "o",
        "gpt-6.1-sol": "^",
        "gpt-6-astra": "s",
        "gemini-3.8-flash": "h",
    }
)


def model_colour(row):
    return MODEL_COLOURS[row["family_label"]]


def model_name(row):
    return MODEL_NAMES[row["family_label"]]


def f(size, bold=False):
    return ImageFont.truetype(BOLD if bold else REGULAR, size)


def text(draw, xy, value, size=32, color=FG, bold=False):
    draw.text(xy, str(value), font=f(size, bold), fill=color)


def fittext(draw, xy, value, width, size=64, color=FG, bold=True):
    while draw.textlength(value, font=f(size, bold)) > width:
        size -= 1
    text(draw, xy, value, size, color, bold)


def wrap(draw, value, width, size):
    font = f(size)
    if any("\u4e00" <= c <= "\u9fff" for c in value):
        lines = []
        line = ""
        for c in value:
            if c == "\n":
                lines.append(line)
                line = ""
                continue
            if draw.textlength(line + c, font=font) > width and line:
                lines.append(line)
                line = c
            else:
                line += c
        return lines + [line] if line else lines
    lines = []
    for paragraph in value.split("\n"):
        line = ""
        for word in paragraph.split():
            candidate = (line + " " + word).strip()
            if draw.textlength(candidate, font=font) > width and line:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


def para(draw, xy, value, width=800, size=32, color=MUTED, spacing=1.45):
    x, y = xy
    for line in wrap(draw, value, width, size):
        text(draw, (x, y), line, size, color)
        y += int(size * spacing)
    return y


def card(draw, box):
    draw.rounded_rectangle(box, radius=25, fill=CARD)


def pick(lang, en, zh):
    return zh if lang == "zh" else en


def base(lang, s, index, phase):
    im = Image.new("RGB", (1920, 1080), BG)
    d = ImageDraw.Draw(im)
    for x in range(0, 1920, 80):
        d.line((x, 0, x, 1080), fill="#0e192a")
    for y in range(0, 1080, 80):
        d.line((0, y, 1920, y), fill="#0e192a")
    d.rectangle((0, 0, 1920, 9), fill=CYAN)
    text(d, (80, 40), "SIMJECTURE  /  SCIENTIFIC AI BENCHMARK", 24, CYAN, True)
    text(d, (1570, 44), "2026 · 10 · 01", 25, MUTED)
    fittext(d, (80, 96), s["title_" + lang], 1740, 64)
    d.line((80, 195, 1840, 195), fill="#2a3b52", width=2)
    text(
        d,
        (80, 1018),
        pick(
            lang, "Recorded diagnostic tasks · task pack 0.3.0", "已有诊断数据分析 · 任务包 0.3.0"
        ),
        23,
        MUTED,
    )
    text(d, (1385, 1018), f"STOCK SYNTHETIC VOICE   {index + 1:02d} / 12", 21, MUTED)
    return im, d


def metric(d, box, value, label, detail="", color=CYAN):
    card(d, box)
    x, y, r, b = box
    fittext(d, (x + 35, y + 24), value, r - x - 70, 94, color)
    para(d, (x + 35, y + 150), label, r - x - 70, 32, FG)
    if detail:
        para(d, (x + 35, b - 105), detail, r - x - 70, 24, MUTED)


def axes_finish(fig, ax, lang):
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="x", alpha=0.65)
    ax.set_axisbelow(True)
    for item in [ax.xaxis.label, ax.yaxis.label, *ax.get_xticklabels(), *ax.get_yticklabels()]:
        item.set_fontproperties(FONT)
    fig.tight_layout(pad=1.5)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, facecolor=CARD)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def paste_chart(im, chart, xy=(80, 240), size=(1760, 580)):
    chart = chart.resize(size, Image.Resampling.LANCZOS)
    im.paste(chart, xy)


def label(r):
    return model_name(r) + " / " + (r["effort"] or "default")


def selected(task, keys):
    rows = TASK[task]["rows"]
    return [next(r for r in rows if r["model"] == m and r["effort"] == e) for m, e in keys]


def rankchart(lang, mode, unfinished=False):
    rows = [
        r
        for r in TASK["rz-diagnostics"]["rows"]
        if r["passes"] and (mode == "time" or r["ranked_cost_per_attempt"] is not None)
    ]
    key = "median_verified_seconds" if mode == "time" else "ranked_cost_per_attempt"
    rows = sorted(rows, key=lambda r: r[key])[:10]
    if unfinished:
        rows += selected("rz-diagnostics", [("mimo-v2.6-flash", "high"), ("grok-4.7", "high")])
    fig, ax = plt.subplots(figsize=(17.6, 5.8))
    y = np.arange(len(rows))
    values = [
        r["cost_per_attempt"] if mode == "cost" else r[key] if r["passes"] else 0 for r in rows
    ]
    ax.barh(y, values, height=0.63, color=[model_colour(r) if r["passes"] else RED for r in rows])
    ax.set_yticks(y, [label(r) for r in rows])
    ax.invert_yaxis()
    for i, (r, v) in enumerate(zip(rows, values, strict=True)):
        val = (
            (
                f"{v:.1f} s"
                if mode == "time"
                else ("≈" if r["cost_coverage"] == "estimated" else "") + f"${v:.4f}"
            )
            if r["passes"]
            else (f"≥${r['cost_per_attempt']:.4f} · " if mode == "cost" else "")
            + pick(lang, "Unfinished", "未完成")
        )
        ax.text(
            v + max(values) * 0.018,
            i,
            val,
            va="center",
            fontsize=17,
            fontproperties=FONT,
            color=FG if r["passes"] else RED,
        )
    ax.set_xlim(0, max(values) * 1.26)
    ax.set_xlabel(
        pick(
            lang, "Verified finish time (seconds) · lower is better", "验证完成时间（秒）· 越低越好"
        )
        if mode == "time"
        else pick(
            lang,
            "API-equivalent USD per attempt · lower is better",
            "每次尝试的 API 等价美元成本 · 越低越好",
        ),
        fontproperties=FONT,
    )
    return axes_finish(fig, ax, lang)


def completion_chart(lang, phase):
    keys = [
        ("gpt-6.1-sol", "low"),
        ("gpt-6.1-sol", "high"),
        ("gpt-6-astra", "high"),
        ("mimo-v2.6-flash", "high"),
        ("mimo-v2.6-pro", "high"),
    ]
    rows = selected("csv-energy", keys)
    fig, ax = plt.subplots(figsize=(17.6, 5.8))
    y = np.arange(len(rows))
    h = 0.31
    ax.barh(
        y - h / 2,
        [r["numeric_passes"] for r in rows],
        height=h,
        facecolor="none",
        edgecolor=[model_colour(r) for r in rows],
        hatch="///",
        linewidth=2,
    )
    ax.barh(y + h / 2, [r["passes"] for r in rows], height=h, color=[model_colour(r) for r in rows])
    ax.set_yticks(y, [label(r) for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, 6.2)
    ax.set_xticks(range(6))
    for i, r in enumerate(rows):
        ax.text(
            r["numeric_passes"] + 0.07,
            i - h / 2,
            str(r["numeric_passes"]) + "/5",
            va="center",
            color=model_colour(r),
        )
        ax.text(
            r["passes"] + 0.07,
            i + h / 2,
            str(r["passes"]) + "/5",
            va="center",
            color=model_colour(r),
        )
    ax.legend(
        handles=[
            Patch(
                facecolor="none",
                edgecolor=FG,
                hatch="///",
                label=pick(lang, "Numerical checks", "数值检查"),
            ),
            Patch(facecolor=FG, label=pick(lang, "Full timed delivery", "完整按时交付")),
        ],
        loc="lower right",
        facecolor=CARD,
        labelcolor=FG,
        prop=FONT,
    )
    ax.set_xlabel(
        pick(
            lang,
            "CSV task · five graded attempts per shown configuration",
            "CSV 任务 · 图中每种配置均有五次有效尝试",
        ),
        fontproperties=FONT,
    )
    return axes_finish(fig, ax, lang)


def paretochart(lang, phase):
    rows = [
        r
        for r in TASK["rz-diagnostics"]["rows"]
        if r["passes"] and r["ranked_cost_per_attempt"] is not None
    ]
    fig, ax = plt.subplots(figsize=(17.6, 5.8))
    priority = ["deepseek-flash", "gpt-6-luna", "gpt-6.1-sol", "gpt-6-astra", "gemini-3.8-flash"]
    models = sorted(
        {r["family_label"] for r in rows},
        key=lambda name: (priority.index(name) if name in priority else len(priority), name),
    )
    for model in models:
        rr = [r for r in rows if r["family_label"] == model]
        ax.scatter(
            [r["cost_per_attempt"] for r in rr],
            [r["median_verified_seconds"] for r in rr],
            s=95,
            c=MODEL_COLOURS[model],
            marker=MARKERS[model],
            label=MODEL_NAMES[model],
            edgecolors=BG,
            zorder=3,
        )
    efforts = ["low", "medium", "high", "xhigh", "max", "ultra"]
    # Lines exclusively represent effort settings of the SAME model and agent.
    for family in sorted({r["family"] for r in rows}):
        rr = sorted(
            [r for r in rows if r["family"] == family and r["effort"] in efforts],
            key=lambda r: efforts.index(r["effort"]),
        )
        if len(rr) > 1:
            (line,) = ax.plot(
                [r["cost_per_attempt"] for r in rr],
                [r["median_verified_seconds"] for r in rr],
                "--",
                lw=1.5,
                color=model_colour(rr[0]),
                alpha=0.7,
            )
            line.set_gid("effort:" + family)
    frontier = [
        r
        for r in rows
        if not any(
            o["cost_per_attempt"] <= r["cost_per_attempt"]
            and o["median_verified_seconds"] <= r["median_verified_seconds"]
            and (
                o["cost_per_attempt"] < r["cost_per_attempt"]
                or o["median_verified_seconds"] < r["median_verified_seconds"]
            )
            for o in rows
        )
    ]
    # Do not join different models. Independent rings mark non-dominated points.
    for r in frontier:
        x, y = r["cost_per_attempt"], r["median_verified_seconds"]
        ax.scatter([x], [y], s=230, facecolors="none", edgecolors=FG, lw=2, zorder=5)
        ax.annotate(
            label(r) + f"\n${x:.4f} · {y:.1f} s",
            (x, y),
            xytext=(18, 12),
            textcoords="offset points",
            color=FG,
            fontproperties=FONT,
            fontsize=17,
        )
    ax.set_xscale("log")
    ax.set_ylim(930, 0)
    ax.set_xlim(0.007, max(r["cost_per_attempt"] for r in rows) * 1.5)
    ax.set_xlabel(
        pick(
            lang,
            "API-equivalent USD / attempt · log scale · cheaper ←",
            "API 等价美元 / 次 · 对数轴 · 更便宜 ←",
        ),
        fontproperties=FONT,
    )
    ax.set_ylabel(
        pick(lang, "Verified time (s) · faster ↑", "验证完成时间（秒）· 更快 ↑"),
        fontproperties=FONT,
    )
    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.015, 0.5),
        frameon=False,
        labelcolor=FG,
        prop=FontProperties(fname=REGULAR, size=14),
        title=pick(lang, "Model family", "模型"),
        title_fontproperties=FONT,
        labelspacing=0.45,
        handletextpad=0.55,
    )
    ax.text(
        0.01,
        35,
        pick(lang, "UPPER LEFT IS BETTER", "左上角更好"),
        color=CYAN,
        fontproperties=FONT,
        fontsize=20,
    )
    ax.grid(axis="both", alpha=0.5)
    return axes_finish(fig, ax, lang)


def render(lang, s, index, phase):
    im, d = base(lang, s, index, phase)
    k = s["kind"]
    if k == "intro":
        text(d, (100, 262), pick(lang, "AI FOR FUSION", "面向聚变研究的 AI"), 31, CYAN, True)
        fittext(
            d,
            (100, 326),
            pick(lang, "Can it deliver the analysis?", "它能交付可用的分析吗？"),
            1550,
            88,
        )
        para(
            d,
            (105, 469),
            pick(
                lang,
                "Recorded plasma data → coding agent → independent verification",
                "已有等离子体数据 → 编码代理 → 独立验证",
            ),
            1530,
            42,
            FG,
        )
        for box, v, caption in [
            ((100, 600, 635, 840), "42", pick(lang, "Configurations", "配置")),
            ((695, 600, 1230, 840), "252", pick(lang, "Scheduled attempts", "安排的尝试")),
            ((1290, 600, 1825, 840), "2", pick(lang, "Diagnostic tasks", "诊断任务")),
        ]:
            card(d, box)
            text(d, (box[0] + 30, box[1] + 15), v, 90, CYAN, True)
            text(d, (box[0] + 30, box[1] + 142), caption, 31, FG)
    elif k == "tasks":
        card(d, (80, 240, 850, 860))
        card(d, (890, 240, 1840, 860))
        text(d, (120, 272), "CSV  /  180 s", 54, CYAN, True)
        para(
            d,
            (120, 374),
            pick(
                lang,
                "Escaped radiation\nRadiation-operator energy removal\nSaved results + findings",
                "流出的辐射能量\n辐射算子移除的能量\n保存结果与解释",
            ),
            680,
            35,
            FG,
        )
        text(d, (930, 272), "RZ + HDF5  /  900 s", 54, AMBER, True)
        para(d, (930, 377), "64 × 4  &  128 × 4\n401 frames / case", 760, 38, FG)
        # Explicitly schematic grid. Rows are radial bands, columns axial bins.
        gx, gy = 930, 542
        for a in range(4):
            for r in range(16):
                d.rectangle(
                    (gx + a * 65, gy + r * 15, gx + (a + 1) * 65 - 3, gy + (r + 1) * 15 - 2),
                    fill=("#28596a" if (r + a) % 3 else "#45a99f"),
                )
        text(d, (1220, 563), "R ↑    Z →", 35, CYAN, True)
        para(
            d,
            (1220, 635),
            pick(
                lang,
                "Grid schematic\n4 axial cells\nNot a 3D field image",
                "网格示意\n轴向 4 个单元\n并非三维场数据图",
            ),
            530,
            28,
            MUTED,
        )
    elif k == "protocol":
        for box, v, caption, de in [
            (
                (80, 240, 635, 580),
                "252",
                pick(lang, "Scheduled attempts", "安排的尝试"),
                pick(lang, "42 configurations · 8 workers", "42 种配置 · 8 个工作进程"),
            ),
            (
                (660, 240, 1215, 580),
                "24",
                pick(lang, "No inference", "未进入推理"),
                pick(lang, "Availability only; excluded", "仅为不可用记录 · 排除评分"),
            ),
            (
                (1240, 240, 1840, 580),
                "228",
                pick(lang, "Graded attempts", "有效评分尝试"),
                pick(lang, "188 CSV + 40 RZ", "188 次 CSV + 40 次 RZ"),
            ),
        ]:
            metric(d, box, v, caption, de)
        card(d, (80, 620, 1840, 860))
        para(
            d,
            (120, 652),
            pick(
                lang,
                "Fresh workspace → reducer + results + findings → host rerun\nThree numerical holdouts · immutable inputs · verification within deadline",
                "新工作目录 → 分析器 + 结果 + 解释 → 验证程序重新运行\n三组额外数值检查 · 输入不可改写 · 验证计入截止时间",
            ),
            1660,
            34,
            FG,
        )
    elif k == "completion":
        if phase == 0:
            metric(
                d,
                (80, 245, 635, 780),
                "161 / 188",
                pick(lang, "Numerical checks passed", "数值检查通过"),
            )
            metric(
                d,
                (660, 245, 1215, 780),
                "100 / 188",
                pick(lang, "Full delivery passed", "完整交付通过"),
            )
            metric(
                d,
                (1240, 245, 1840, 780),
                "61",
                pick(lang, "Correct numbers, incomplete delivery", "数字正确，但交付未完成"),
                color=AMBER,
            )
        else:
            paste_chart(im, completion_chart(lang, phase))
            d = ImageDraw.Draw(im)
        text(
            d,
            (100, 843),
            pick(
                lang,
                "Findings: presence check only; no AI judge of scientific quality",
                "解释文字：只检查提交状态，没有 AI 科学质量裁判",
            ),
            30,
            AMBER,
        )
    elif k == "csv-results":
        rows = selected(
            "csv-energy",
            [
                ("deepseek-flash", "high"),
                ("gpt-6-luna", "medium"),
                ("gemini-3.8-flash-medium", "medium"),
            ],
        )
        for i, r in enumerate(rows):
            x = 80 + i * 590
            metric(
                d,
                (x, 245, x + 570, 795),
                f"{r['median_verified_seconds']:.1f} s",
                label(r),
                f"{r['passes']}/{r['trials']} "
                + pick(lang, "full passes · median of successes", "完成 · 成功尝试中位时间"),
                model_colour(r),
            )
        para(
            d,
            (100, 830),
            pick(
                lang,
                "5/5 is not certainty · 95% Wilson interval ≈ 57–100%",
                "五次全成功仍有不确定性 · 95% 威尔逊区间约 57–100%",
            ),
            1720,
            30,
            AMBER,
        )
    elif k == "rz-results":
        if phase == 0:
            metric(
                d,
                (80, 245, 635, 820),
                "34 / 40",
                pick(lang, "RZ full-contract passes", "RZ 完整交付通过"),
                pick(lang, "One trial per configuration", "每种配置只有一次尝试"),
            )
            metric(
                d,
                (660, 245, 1215, 820),
                "19 / 19",
                pick(lang, "Codex configurations passed", "Codex 配置通过"),
                pick(lang, "Observed; not general ability", "仅为本轮观察 · 非通用能力"),
            )
            metric(
                d,
                (1240, 245, 1840, 820),
                "114.1 s",
                pick(lang, "DeepSeek Flash", "DeepSeek Flash"),
                pick(lang, "Luna medium: 271.6 s", "Luna 中等推理：271.6 秒"),
                MODEL_COLOURS["deepseek-flash"],
            )
        else:
            paste_chart(im, rankchart(lang, "time"))
            d = ImageDraw.Draw(im)
        text(
            d,
            (100, 847),
            pick(
                lang,
                "Different task + different budget → no isolated causal comparison",
                "任务与预算同时改变 → 不能单独归因于时间增加",
            ),
            30,
            AMBER,
        )
    elif k == "adapters":
        if phase == 0:
            metric(
                d,
                (80, 245, 935, 800),
                "0 / 5",
                pick(lang, "MiMo Flash · CSV full delivery", "MiMo Flash · CSV 完整交付"),
                pick(lang, "Numerical checks: 4/5", "数值检查：4/5"),
                MODEL_COLOURS["mimo-v2.6-flash"],
            )
            metric(
                d,
                (965, 245, 1840, 800),
                "0 / 1",
                pick(lang, "Grok 4.7 · RZ full delivery", "Grok 4.7 · RZ 完整交付"),
                pick(
                    lang,
                    "All numerical checks passed; findings missing",
                    "全部数值通过 · 缺少解释文件",
                ),
                MODEL_COLOURS["grok-4.7"],
            )
        else:
            card(d, (80, 245, 1840, 840))
            for y, name, line, col in [
                (
                    290,
                    "DeepSeek",
                    pick(lang, "Native tool-message history", "原生工具消息历史"),
                    MODEL_COLOURS["deepseek-flash"],
                ),
                (
                    460,
                    "MiMo",
                    pick(
                        lang,
                        "Installed framework default history formatter",
                        "已安装框架默认的历史格式",
                    ),
                    MODEL_COLOURS["mimo-v2.6-flash"],
                ),
                (
                    630,
                    pick(lang, "Measurement", "测量对象"),
                    pick(
                        lang,
                        "Model + coding agent + tools + budget",
                        "模型 + 编码代理 + 工具 + 时间预算",
                    ),
                    FG,
                ),
            ]:
                text(d, (125, y), name, 44, col, True)
                para(d, (590, y + 5), line, 1140, 37, FG)
        text(
            d,
            (100, 848),
            pick(
                lang,
                "An observed configuration failure is not a universal incapability claim",
                "一次配置失败，不等于模型普遍没有能力",
            ),
            30,
            MUTED,
        )
    elif k == "ranks":
        paste_chart(im, rankchart(lang, "time" if phase == 0 else "cost", unfinished=True))
        d = ImageDraw.Draw(im)
        text(
            d,
            (100, 824),
            pick(
                lang,
                "RZ: top 10 completed + 2 unfinished examples · n=1 · full 42 rows online",
                "RZ：前 10 个已完成项 + 2 个未完成例子 · n=1 · 页面保留 42 项",
            ),
            25,
            MUTED,
        )
        if phase:
            text(
                d,
                (100, 858),
                pick(
                    lang,
                    "Red: unfinished · bars show recorded cost · ≥ means a lower bound",
                    "红色：未完成 · 费用条显示已记录的成本 · ≥ 表示下限",
                ),
                22,
                AMBER,
            )
    elif k == "pareto":
        paste_chart(im, paretochart(lang, phase))
        d = ImageDraw.Draw(im)
        text(
            d,
            (100, 843),
            pick(
                lang,
                "Colour: model   ·   White rings: frontier   ·   Dashed: same-model efforts   ·   RZ n=1",
                "颜色：模型   ·   白色外圈：前沿点   ·   虚线：同模型推理强度   ·   RZ 每项 n=1",
            ),
            30,
            MUTED,
        )
    elif k == "costs":
        for box, v, caption, de, col in [
            (
                (80, 245, 635, 800),
                "$",
                pick(lang, "Complete usage", "完整用量"),
                pick(lang, "Dated tariffs; cache-adjusted", "有日期的单价 · 考虑缓存"),
                CYAN,
            ),
            (
                (660, 245, 1215, 800),
                "≈",
                pick(lang, "Estimate", "估计"),
                pick(lang, "AGY cache semantics uncertain", "AGY 缓存语义有不确定性"),
                AMBER,
            ),
            (
                (1240, 245, 1840, 800),
                "≥",
                pick(lang, "Lower bound", "下限"),
                pick(lang, "Partial stream; excluded cost rank", "数据流不完整 · 不参加成本排名"),
                RED,
            ),
        ]:
            metric(d, box, v, caption, de, col)
        para(
            d,
            (100, 840),
            pick(
                lang,
                "Standard short-context API equivalents · not subscription invoices",
                "标准短上下文 API 等价估计 · 并非订阅账单",
            ),
            1720,
            30,
            MUTED,
        )
    elif k == "verifier":
        card(d, (80, 245, 1840, 815))
        entries = [
            ("0.1", pick(lang, "Equal-radius cell ordering", "相同半径单元排列顺序"), RED),
            (
                "0.2",
                pick(
                    lang,
                    "float32 multiplication before float64 promotion",
                    "先 float32 乘法，后转 float64",
                ),
                AMBER,
            ),
            (
                "0.3",
                pick(
                    lang,
                    "Explicit interpolation + promote before arithmetic",
                    "明确插值规则 + 运算之前提升精度",
                ),
                CYAN,
            ),
        ]
        for i, (v, line, col) in enumerate(entries):
            y = 285 + i * 175
            text(d, (125, y), v, 76, col, True)
            fittext(d, (390, y + 20), line, 1340, 43, FG, False)
        text(
            d,
            (100, 846),
            pick(
                lang,
                "Closed-form checks · permutation controls · independent summation",
                "解析对照 · 排列对照 · 独立求和检查",
            ),
            31,
            CYAN,
        )
    elif k == "outlook":
        if phase == 0:
            card(d, (80, 245, 1840, 845))
            text(d, (125, 286), pick(lang, "Measured here", "本轮测量"), 42, CYAN, True)
            para(
                d,
                (125, 370),
                pick(
                    lang,
                    "Reproducible analysis of recorded plasma diagnostics\nComplete delivery, elapsed time, and token-rate cost",
                    "已有等离子体诊断数据的可复现分析\n完整交付、耗时和按 token 单价估计的成本",
                ),
                1640,
                38,
                FG,
            )
            text(d, (125, 559), pick(lang, "Next benchmarks", "后续基准"), 42, AMBER, True)
            para(
                d,
                (125, 643),
                pick(
                    lang,
                    "Independent scientific tasks · repeated solver-backed trials\nNew simulations and hypothesis testing require separate evaluation",
                    "独立科学问题 · 重复的真实求解器任务\n新模拟与假设检验需要单独评估",
                ),
                1630,
                35,
                FG,
            )
        else:
            card(d, (80, 245, 1840, 845))
            text(d, (125, 284), "github.com/tomzhu0225/simjecture", 48, CYAN, True)
            text(d, (125, 369), "branch: feature/benchmark-leaderboard", 35, FG)
            para(
                d,
                (125, 458),
                pick(
                    lang,
                    "Source + sanitized grades + valuation receipts\nCustom models: workspace → Benchmarks → Run your model\nCommunity-controlled results remain separate",
                    "源代码 + 脱敏成绩 + 费用记录\n自定义模型：工作台 → 基准测试 → 测试模型\n社区自行测试与项目实测结果分开",
                ),
                1640,
                34,
                FG,
            )
            para(
                d,
                (125, 705),
                pick(
                    lang,
                    "Development feature; not bundled in published 0.5.3rc2\nSynthetic stock narration · original graphics · sources in companion files",
                    "开发分支功能，尚未打包进已发布的 0.5.3rc2\n合成通用声音 · 原创图形 · 来源见配套文件",
                ),
                1640,
                27,
                MUTED,
            )
    if phase == 1 and k in {"intro", "tasks", "protocol", "csv-results", "costs", "verifier"}:
        im, d = base(lang, s, index, phase)
        if k in {"intro", "protocol"}:
            stages = [
                pick(lang, "Data", "数据"),
                pick(lang, "Coding agent", "编码代理"),
                pick(lang, "Independent host", "独立验证"),
                pick(lang, "Evidence", "证据"),
            ]
            for i, name in enumerate(stages):
                x = 80 + i * 445
                card(d, (x, 325, x + 395, 605))
                fittext(d, (x + 27, 390), name, 340, 43, CYAN if i in [1, 2] else FG)
                text(d, (x + 30, 500), f"0{i + 1}", 53, MUTED, True)
                if i < 3:
                    text(d, (x + 407, 425), "→", 38, CYAN)
            para(
                d,
                (110, 705),
                pick(
                    lang,
                    "Immutable input → reproducible reducer → held-out checks → saved findings",
                    "不可改写的输入 → 可复现分析器 → 额外数值检查 → 已保存的解释",
                ),
                1690,
                35,
                FG,
            )
            para(
                d,
                (110, 780),
                pick(
                    lang,
                    "Tools and native prompts retained · the original deadline includes verification",
                    "保留工具与原生提示 · 验证计入原始截止时间",
                ),
                1690,
                30,
                MUTED,
            )
        elif k == "tasks":
            items = [
                ("01", pick(lang, "Inward kinetic energy", "向内运动的动能")),
                ("02", pick(lang, "Tracer compression", "示踪物质压缩")),
                ("03", pick(lang, "Event times + radiation windows", "事件时间与辐射窗口")),
                (
                    "04",
                    pick(lang, "Grid differences + numerical plot data", "网格差异与数值绘图数据"),
                ),
            ]
            for i, (n, line) in enumerate(items):
                y = 245 + i * 148
                card(d, (80, y, 1840, y + 130))
                text(d, (120, y + 24), n, 48, CYAN, True)
                fittext(d, (280, y + 32), line, 1510, 39, FG, False)
            text(
                d,
                (100, 853),
                pick(
                    lang,
                    "Analysis of recorded output; no new solver launch in this benchmark",
                    "分析已有输出 · 本轮基准没有启动新模拟",
                ),
                30,
                AMBER,
            )
        elif k == "csv-results":
            rr = selected(
                "csv-energy",
                [
                    ("deepseek-flash", "high"),
                    ("gpt-6-luna", "medium"),
                    ("gemini-3.8-flash-medium", "medium"),
                ],
            )
            fig, ax = plt.subplots(figsize=(17.6, 5.8))
            values = [r["median_verified_seconds"] for r in rr]
            y = np.arange(3)
            ax.barh(y, values, color=[model_colour(r) for r in rr], height=0.48)
            ax.invert_yaxis()
            ax.set_yticks(y, [label(r) for r in rr])
            ax.set_xlim(0, 220)
            for i, r in enumerate(rr):
                ax.text(
                    values[i] + 5,
                    i,
                    f"{values[i]:.1f} s · {r['passes']}/{r['trials']}",
                    va="center",
                    color=FG,
                    fontproperties=FONT,
                )
            ax.set_xlabel(
                pick(
                    lang,
                    "Median verified time among successes (s)",
                    "成功尝试的验证完成中位时间（秒）",
                ),
                fontproperties=FONT,
            )
            paste_chart(im, axes_finish(fig, ax, lang))
            d = ImageDraw.Draw(im)
            text(
                d,
                (100, 843),
                pick(
                    lang,
                    "Selected configurations · times condition on success · inspect failure counts",
                    "选定配置 · 时间仅概括成功尝试 · 同时查看失败次数",
                ),
                30,
                MUTED,
            )
        elif k == "costs":
            card(d, (80, 245, 1840, 835))
            text(
                d,
                (120, 283),
                pick(
                    lang,
                    "Usage × dated tariff → API-equivalent cost",
                    "实际用量 × 有日期的单价 → API 等价成本",
                ),
                45,
                CYAN,
                True,
            )
            para(
                d,
                (120, 405),
                pick(
                    lang,
                    "Uncached input · cached input · cache writes · output",
                    "非缓存输入 · 缓存输入 · 缓存写入 · 输出",
                ),
                1650,
                40,
                FG,
            )
            para(
                d,
                (120, 530),
                pick(
                    lang,
                    "Cumulative receipts: use the total once, not once per resume",
                    "累计凭据：累计值只计一次，不能每次继续工作都重新相加",
                ),
                1650,
                36,
                AMBER,
            )
            para(
                d,
                (120, 675),
                pick(
                    lang,
                    "Missing counters ≠ zero spending\nA terminal quota error cannot erase earlier usage",
                    "缺失计数 ≠ 零花费\n最后一次额度报错不能覆盖之前的用量",
                ),
                1630,
                34,
                FG,
            )
            text(
                d,
                (100, 850),
                pick(
                    lang,
                    "Standard short-context rates · cache-adjusted · not an invoice",
                    "标准短上下文单价 · 考虑缓存 · 并非实际账单",
                ),
                29,
                MUTED,
            )
        elif k == "verifier":
            for i, (value, title, detail) in enumerate(
                [
                    (
                        "01",
                        pick(lang, "Closed-form controls", "解析对照"),
                        pick(lang, "Volume and energy", "体积与能量"),
                    ),
                    (
                        "02",
                        pick(lang, "Permutation controls", "排列对照"),
                        pick(lang, "Equal-radius ordering", "相同半径单元顺序"),
                    ),
                    (
                        "03",
                        pick(lang, "Independent sums", "独立求和"),
                        pick(lang, "Float64 before arithmetic", "运算之前转为 float64"),
                    ),
                ]
            ):
                x = 80 + i * 590
                metric(d, (x, 245, x + 570, 800), value, title, detail)
            text(
                d,
                (100, 844),
                pick(
                    lang,
                    "Fresh 0.3 trials · qualification archive kept separate · no silent regrading",
                    "全新 0.3 尝试 · 资格测试单独保存 · 不悄悄重新评分",
                ),
                29,
                AMBER,
            )
    return im


def main():
    for lang in ["en", "zh"]:
        folder = OUT / lang / "frames"
        folder.mkdir(parents=True, exist_ok=True)
        for i, s in enumerate(DATA["scenes"]):
            for phase in [0, 1]:
                target = folder / f"{s['id']}-{phase}.png"
                buf = io.BytesIO()
                render(lang, s, i, phase).save(buf, format="PNG")
                value = buf.getvalue()
                if not target.exists() or target.read_bytes() != value:
                    target.write_bytes(value)
        print(f"{lang}: 24 original 1080p graphics", flush=True)


if __name__ == "__main__":
    main()
