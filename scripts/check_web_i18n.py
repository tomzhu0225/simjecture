"""Audit owned HTML/JS copy without dependencies or touching runtime content.

This is a conservative source-literal check, not a translation percentage. It
cannot infer whether arbitrary API data or a variable is UI copy. Browser tests
cover those render paths. Use --json for all three classified inventories.
"""

from __future__ import annotations

import argparse
import bisect
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src/conjecture_solver/web/static"
# These are names/units/identifiers, not English UI sentences. Keep this list
# narrow: a new human-facing sentence must not be hidden by an exclusion.
FIXED = {
    "English",
    "Simjecture",
    "SIMJECTURE",
    "GitHub",
    "GitHub ↗",
    "Linux",
    "SSH",
    "CPU",
    "GPU",
    "GPUs",
    "API",
    "JSON",
    "MCP",
    "DSH",
    "CAD",
    "Codex",
    "Codex GLM",
    "Codex / GLM",
    "Grok",
    "Grok CLI",
    "AGY",
    "Antigravity",
    "DeepSeek",
    "DeepSeek Flash",
    "DeepSeek V4 Pro",
    "OpenRouter",
    "GPT-OSS 120B",
    "WarpX · CPU",
    "WarpX · CUDA",
    "FLASH",
    "Conjecture 1",
    "Elmer",
    "FreeCAD",
    "Gmsh",
    "ITER pack",
    "SOLPS-ITER",
    "JOREK",
    "DINA-PS",
    "atoMEC",
    "Singularity-EOS",
    "M-ANEOS",
    "Frankfurt FEOS",
    "Optab",
    "FAC",
    "Lean",
    "LN",  # Lean tool-card monogram.
    "Math",
    "Ctrl+C",
    "Content-Type",
    "X-Simjecture-Token",
    "X-CSRF-Token",
    "POST",
    "GET",
    "use strict",
    "DOMContentLoaded",
    "Enter",
    "Escape",
    "ArrowRight",
    "Home",
    "End",
    "replaceState",
    "pushState",
    "zh-CN",
    "ArrowLeft",
    "SUMMARY",
    "LR",
    "UL",
    "TB",
    "viewBox",
    "strokeWidth",
    "clipPath",
    "userSpaceOnUse",
    "KB",
    "MB",
    "GB",
    "B",
    "PY",
    "FE",
    "MS",
    "LB",
    "IT",
    "SP",
    "JK",
    "DN",
    "WX",
    "FL",
    "AT",
    "ES",
    "OP",
    "FA",
    "RS",
    "C1",
    "noopener noreferrer",
    "noopener,noreferrer",
}
# Raw categories are also option values and filter keys. Their labels are
# localized explicitly with label(category); changing these literals is unsafe.
CATEGORIES = {
    "Workflow assistance",
    "CAD & simulation",
    "Analysis & data",
    "Fluids & MHD",
    "Plasma & fusion",
    "Materials & radiation",
    "Connected tools",
}


# Tokenize comments and JS literals before looking for prose. Templates are
# included in full, so the report also catches English surrounding ${values}.
def literals(source: str):
    """Read literals, ignoring comments/regex and balancing template expressions.

    This deliberately does not evaluate JS or parse research/HTML strings as
    executable code. Offsets remain offsets into the original source.
    """
    embedded = []

    def quoted(pos):
        quote = source[pos]
        pos += 1
        while pos < len(source):
            if source[pos] == "\\":
                pos += 2
            elif source[pos] == quote:
                return pos + 1
            else:
                pos += 1
        return len(source)

    def regex_end(pos):
        pos += 1
        bracket = False
        while pos < len(source):
            char = source[pos]
            if char == "\\":
                pos += 2
                continue
            if char == "[":
                bracket = True
            elif char == "]":
                bracket = False
            elif char == "/" and not bracket:
                pos += 1
                while pos < len(source) and source[pos].isalpha():
                    pos += 1
                return pos
            pos += 1
        return pos

    def template(pos):
        start, parts = pos, []
        pos += 1
        while pos < len(source):
            char = source[pos]
            if char == "\\":
                parts.append(source[pos : pos + 2])
                pos += 2
            elif char == "`":
                return pos + 1, "".join(parts)
            elif source.startswith("${", pos):
                depth, pos = 1, pos + 2
                while pos < len(source) and depth:
                    if source[pos] in "\"'":
                        literal_start = pos
                        pos = quoted(pos)
                        embedded.append((literal_start, pos, source[literal_start + 1 : pos - 1]))
                        continue
                    if source[pos] == "`":
                        literal_start = pos
                        pos, value = template(pos)
                        embedded.append((literal_start, pos, value))
                        continue
                    if source[pos] == "{":
                        depth += 1
                    elif source[pos] == "}":
                        depth -= 1
                    pos += 1
                parts.append("{value}")
            else:
                parts.append(char)
                pos += 1
        return pos, source[start + 1 :]

    pos, previous = 0, ""
    while pos < len(source):
        if source.startswith("//", pos):
            newline = source.find("\n", pos)
            pos = newline if newline >= 0 else len(source)
        elif source.startswith("/*", pos):
            end = source.find("*/", pos + 2)
            pos = end + 2 if end >= 0 else len(source)
        elif source[pos] in "\"'`":
            start = pos
            if source[pos] == "`":
                pos, value = template(pos)
            else:
                pos = quoted(pos)
                value = source[start + 1 : pos - 1]
            yield start, pos, value
            yield from sorted(embedded)
            embedded.clear()
            previous = "literal"
        elif source[pos] == "/" and (
            previous in {"", "(", "=", ",", ":", "[", "!", "|", "&", "?", "return"}
        ):
            pos = regex_end(pos)
        elif source[pos].isalpha() or source[pos] in "_$":
            start = pos
            pos += 1
            while pos < len(source) and (source[pos].isalnum() or source[pos] in "_$"):
                pos += 1
            previous = source[start:pos]
        else:
            if not source[pos].isspace():
                previous = source[pos]
            pos += 1


def technical(value: str) -> str | None:
    if value in FIXED:
        return "fixed name, unit, protocol or code identifier"
    if value in {"GPT-", "GPT ", "Gemini ", "MiMo ", "Grok ", "Claude "}:
        return "model name normalization prefix"
    if value in {"RESULTS_INDEX.md", "STUDY_LEDGER.md", "research/RESULTS.md"}:
        return "durable research record filename"
    if value == "(prefers-color-scheme: dark)":
        return "CSS media query"
    if re.fullmatch(r"\{value\} (?:KB|MB|GB|min)", value):
        return "numeric telemetry with fixed units"
    if value in {"quiet load-more-runs", "quiet stop-run", "quiet classify-run"}:
        return "DOM event delegation class markers"
    if value in {" effort", " pareto", " · CUDA"}:
        return "CSS suffix or fixed runtime variant"
    if value.startswith("Simjecture · {value}") or value == "GPU {value}":
        return "product/runtime names and hardware IDs"
    if value in {"enables evidence for", "Qualifies instruments for {value}"}:
        return "raw derived-graph relation/statement; displayed labels are localized"
    if value in CATEGORIES:
        return "raw category/filter value; its displayed label is localized"
    if not re.search(r"[A-Za-z]{2}", value):
        return "no English prose"
    if re.fullmatch(r"[a-z0-9_./:@#?=+*\-]+", value):
        return "identifier, enum, route, path or configuration value"
    if value.startswith(("/", "http:", "https:", "ssh ", "archive/*", "**/")):
        return "path, URL, glob or command"
    if re.fullmatch(r"(?:[\d.]+|\$\{[^}]+\}) ?(?:[BKMGT]B|CPU|GPU|s|h|m|min|%)(?:.*)?", value):
        return "numeric telemetry with fixed units"
    if value.startswith(
        ("var(", "hsl(", "url(", "translate(", "(max-width:", ":scope", ".", "[", "#")
    ):
        return "CSS, SVG geometry or DOM selector"
    return None


class HTMLCopy(HTMLParser):
    def __init__(self, filename: str, emit):
        super().__init__(convert_charrefs=True)
        self.filename, self.emit = filename, emit
        self.stack: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for name in ["placeholder", "title", "aria-label", "aria-valuetext", "label", "alt"]:
            if attrs.get(name):
                self.emit(
                    self.filename,
                    self.getpos()[0],
                    attrs[name],
                    "localized" if attrs.get("data-i18n-" + name) else None,
                    f"HTML {name}",
                )
        if tag not in {"input", "img", "br", "hr", "meta", "link", "source", "wbr"}:
            self.stack.append((tag, attrs))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()

    def handle_data(self, value):
        if not value.strip() or any(tag in {"script", "style"} for tag, _ in self.stack):
            return
        marker = any(attrs.get("data-i18n") for _, attrs in self.stack)
        raw = any(tag in {"code", "pre"} for tag, _ in self.stack)
        self.emit(
            self.filename,
            self.getpos()[0],
            re.sub(r"\s+", " ", value).strip(),
            "localized" if marker else "technical" if raw else None,
            "raw code example" if raw else "HTML text",
        )


def technical_ranges(source):
    """Explicitly reviewed non-UI blocks, independent of JavaScript formatting."""
    ranges = []
    active = None
    for marker in re.finditer(
        r"^\s*// i18n-technical-(start|end)(?:: ([^\n]+))?$", source, re.M
    ):
        kind, reason = marker.groups()
        if kind == "start":
            if active is not None or not reason:
                raise ValueError("i18n technical blocks need a reason and cannot nest")
            active = (marker.end(), reason)
        else:
            if active is None:
                raise ValueError("i18n technical block ends without a start")
            ranges.append((active[0], marker.start(), active[1]))
            active = None
    if active is not None:
        raise ValueError("i18n technical block has no end")
    return ranges


def audit():
    records = []
    css_classes = set()
    for path in STATIC.rglob("*.css"):
        if "vendor" in path.parts:
            continue
        css_classes.update(re.findall(r"\.([a-zA-Z_][\w-]*)", path.read_text()))

    def emit(file, line, value, category=None, reason=""):
        if not re.search(r"[A-Za-z]{2}", value):
            return
        exclusion = technical(value)
        tokens = value.replace("{value}", "").split()
        if tokens and all(token in css_classes or token == "quiet" for token in tokens):
            exclusion = "CSS class names"
        if re.fullmatch(r"[\w./?:=&${}\-*]+", value) and "{value}" in value:
            exclusion = "templated identifier, route, storage key or path"
        if (
            category is None
            and reason.startswith("HTML")
            and exclusion == "identifier, enum, route, path or configuration value"
            and re.fullmatch(r"[a-z][a-z_-]*", value)
        ):
            category, reason = "unresolved", "HTML display copy"
        if file == "app.js" and value == "Searching for a counterexample.":
            category = "localized"
            reason = "raw loop fallback localized by explicit known() boundary"
        if value.startswith("panels."):
            category = "localized"
            reason = "parameterized sidebar message key"
        records.append(
            dict(
                file=file,
                line=line,
                text=value,
                category=category or ("technical" if exclusion else "unresolved"),
                reason=reason if category else exclusion or reason,
            )
        )

    for path in sorted(STATIC.rglob("*")):
        if "vendor" in path.parts or path.suffix not in {".html", ".js"}:
            continue
        source = path.read_text(encoding="utf-8")
        if path.name in {"i18n.js", "i18n-messages.js"}:
            # Catalog completeness and all referenced keys are tested separately.
            continue
        if path.suffix == ".html":
            HTMLCopy(path.name, emit).feed(source)
            continue
        line_starts = [0] + [m.end() for m in re.finditer("\n", source)]
        excluded_ranges = technical_ranges(source)
        functions = [
            (m.start(), m.group(1))
            for m in re.finditer(r"^(?:async )?function (\w+)\(", source, re.M)
        ]
        for start, end, value in literals(source):
            value = value.replace(r"\n", "\n").replace(r"\"", '"').replace(r"\'", "'")
            before, after = source[max(0, start - 150) : start], source[end : end + 30]
            line = bisect.bisect_right(line_starts, start)
            active = [name for offset, name in functions if offset < start]
            function = active[-1] if active else ""
            if path.name == "markdown.js":
                emit(
                    path.name,
                    line,
                    value,
                    "technical",
                    "scientific Markdown formatter; no owned UI copy",
                )
            elif re.fullmatch(
                r"(?:ui|workspace|monitor|panels|status|time|benchmarks|tools)\.[\w.\-]+", value
            ):
                emit(path.name, line, value, "localized", "message key")
            elif any(left <= start < right for left, right, _ in excluded_ranges):
                reason = next(
                    reason for left, right, reason in excluded_ranges if left <= start < right
                )
                emit(path.name, line, value, "technical", reason)
            elif path.name == "workspace.js" and source.rfind(
                "const toolSetupGuides =", 0, start
            ) > source.rfind("function ", 0, start):
                emit(
                    path.name,
                    line,
                    value,
                    "technical",
                    "agent setup instructions, not interface copy",
                )
            elif path.name == "workspace.js" and function in {
                "setupGuideText",
                "setupPrompt",
                "prepareToolStudy",
            }:
                emit(
                    path.name,
                    line,
                    value,
                    "technical",
                    "agent request/instructions; preserve research input",
                )
            elif re.search(r"\bprompt\s*:\s*$", before) or re.search(r"\.value\s*=\s*$", before):
                emit(path.name, line, value, "technical", "form/request data, not a display label")
            elif (
                path.name == "workspace.js"
                and value == "This computer"
                and 'label:$("machine-label-input").value ||' in before
            ):
                emit(path.name, line, value, "technical", "default machine name in request")
            elif path.name == "workspace.js" and re.search(r"stage_detail:\s*$", before):
                emit(path.name, line, value, "technical", "raw installer stage; display localized")
            elif re.match(r"\s*:", after) and re.search(r"(?:\{|,)\s*$", before):
                emit(path.name, line, value, "technical", "object key")
            elif re.search(
                r"(?:querySelector(?:All)?|getElementById|closest|matches|addEventListener|removeEventListener|classList\.\w+|getAttribute|removeAttribute|setAttribute|localStorage\.\w+|createElement(?:NS)?)\(\s*$",
                before,
            ):
                emit(
                    path.name,
                    line,
                    value,
                    "technical",
                    "DOM, event, storage or attribute identifier",
                )
            elif re.search(r"(?:className|\.style\.\w+|dataset\.\w+)\s*=\s*$", before):
                emit(path.name, line, value, "technical", "class, CSS or data identifier")
            elif value.lstrip().startswith("<"):
                HTMLCopy(path.name, emit).feed(value)
            elif "{value}" in value and not re.search(r"[A-Za-z]{2}", value.replace("{value}", "")):
                emit(path.name, line, value, "technical", "composed entirely of runtime data")
            else:
                direct_copy = re.search(
                    r"(?:\.(?:textContent|placeholder|title|ariaLabel)\s*=\s*|"
                    r"\b(?:button|field|toast|showToast)\(\s*|"
                    r"\b(?:el|node|paragraph)\(\s*[\"'][\w-]+[\"']\s*,\s*|"
                    r"\belement\(\s*[\"'][\w-]+[\"']\s*,\s*"
                    r"(?:null|[\"'][\w -]+[\"'])\s*,\s*|"
                    r"\.setAttribute\(\s*[\"'](?:aria-label|aria-valuetext|title|placeholder|alt)"
                    r"[\"']\s*,\s*|new Option\(\s*)$",
                    before,
                )
                # A bare word beside a translated expression is still display
                # copy. Do not apply this heuristic to routes or other tokens.
                translated_fallback = re.fullmatch(r"[A-Za-z][A-Za-z _-]+", value) and re.search(
                    r"(?:SimjectureI18n\.label\([^;\n]*\)\s*\|\||"
                    r"SimjectureI18n\.t\([^;\n]*\)\s*:)\s*$", before
                )
                # Attributes, element tag names and CSS class arguments are
                # handled above; a lowercase word in a text sink is still UI.
                category = (
                    "unresolved" if (direct_copy or translated_fallback) and value not in FIXED
                    else None
                )
                emit(
                    path.name,
                    line,
                    value,
                    category,
                    reason="JS display copy" if category else "JS literal: inspect display context",
                )
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="include all classified records")
    parser.add_argument("--check", action="store_true", help="fail if unresolved literals remain")
    args = parser.parse_args()
    records = audit()
    counts = dict(Counter(row["category"] for row in records))
    if args.json:
        print(json.dumps(dict(counts=counts, records=records), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(counts, sort_keys=True))
        for row in records:
            if row["category"] == "unresolved":
                print(f"{row['file']}:{row['line']}: {row['text']!r}")
    return int(args.check and bool(counts.get("unresolved")))


if __name__ == "__main__":
    raise SystemExit(main())
