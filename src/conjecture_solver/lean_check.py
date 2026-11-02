"""Bounded Lean checks with frozen sources and an explicit theorem axiom audit.

This driver runs inside Simjecture's capability sandbox. Direct host invocation
is cooperative execution, not a sandbox for hostile Lean metaprograms.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path

ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def runtime():
    configured = os.environ.get("SIMJECTURE_LEAN_ROOT")
    return (
        Path(configured)
        if configured
        else Path(__file__).resolve().parents[2] / ".runtime/lean-4.24.0"
    )


def check(source, theorems, *, output="lean-result", timeout=60, memory_mb=2048):
    """Check named theorems; failed checking leaves a claim undecided, never false."""
    if not theorems or any(not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9.]*", n) for n in theorems):
        raise ValueError("Supply explicit, simple fully qualified theorem names")
    if not 0 < timeout <= 600 or not 64 <= memory_mb <= 8192:
        raise ValueError("timeout must be in (0, 600], memory_mb in [64, 8192]")
    source = Path(source).resolve()
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=False)  # Never replace prior evidence.
    frozen = out / "Candidate.lean"
    frozen.write_bytes(source.read_bytes())
    root = runtime().resolve()
    lean = root / "toolchain/bin/lean"
    env = os.environ.copy()
    # No workspace modules or caller-controlled LEAN_PATH. Dependencies are installed read-only.
    library_paths = [root / "mathlib/.lake/build/lib/lean"]
    library_paths += sorted((root / "mathlib/.lake/packages").glob("*/.lake/build/lib/lean"))
    env["LEAN_PATH"] = ":".join(map(str, library_paths))
    text = frozen.read_text()
    started = time.monotonic()
    report = {
        "schema_version": "0.1.0",
        "status": "undecided",
        "checked": False,
        "source_sha256": digest(frozen),
        "theorems": list(theorems),
        "allowed_axioms": sorted(ALLOWED_AXIOMS),
        "axioms": {},
        "timeout_seconds": timeout,
        "memory_mb": memory_mb,
        "threads": 1,
        "scope": "Named Lean propositions only; no implementation or PDE convergence claim.",
        "execution_boundary": "Use the Simjecture capability sandbox for untrusted source.",
    }
    record = root / "share/build-record.json"
    if record.is_file():
        report["runtime"] = json.loads(record.read_text())
        report["runtime_record_sha256"] = digest(record)

    def finish():
        report["wall_seconds"] = time.monotonic() - started
        report["artifact_sha256"] = {
            p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()
        }
        (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        return report

    # A conservative authoring policy, not a parser or security boundary. The kernel
    # axiom audit below is what detects indirect sorry/custom-axiom dependencies.
    forbidden = re.search(
        r"\b(sorry|admit|axiom|unsafe|initialize|builtin_initialize|elab|macro|syntax|"
        r"run_cmd|run_tac)\b|#(eval|print|check|exit)|\bset_option\b",
        text,
    )
    imports = re.findall(r"^\s*import\s+([^\n]+)", text, re.M)
    bad_import = any(
        not re.fullmatch(r"(?:Mathlib|Std|Init)(?:\.[A-Za-z_0-9]+)*", item)
        for line in imports
        for item in line.split()
    )
    if forbidden or bad_import:
        report["status"] = "rejected_source"
        report["diagnostic"] = (
            "Use mathematical declarations, trusted imports, and complete proofs."
        )
        return finish()

    def run(name, args, extra_path=False):
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise subprocess.TimeoutExpired(args, timeout)
        run_env = env | ({"LEAN_PATH": str(out) + ":" + env["LEAN_PATH"]} if extra_path else {})
        report.setdefault("commands", []).append([str(lean), *args])
        with (out / f"{name}.log").open("w") as log:
            proc = subprocess.Popen(
                [str(lean), *args],
                cwd=out,
                env=run_env,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                return proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                raise

    try:
        report["lean_version"] = subprocess.check_output(
            [str(lean), "--version"], text=True, timeout=min(timeout, 10), env=env
        ).strip()
        flags = ["-j1", f"-M{memory_mb}", "-T200000", "-DwarningAsError=true"]
        code = run("compile", [*flags, "-o", "Candidate.olean", "Candidate.lean"])
        report["compile_returncode"] = code
        if code:
            return finish()
        # The driver authors this audit, outside the candidate. It checks declaration
        # kind and transitive axioms from the checked environment, not candidate prose.
        lines = ["import Candidate", "import Lean", "open Lean Elab Command"]
        for name in theorems:
            # Separate commands avoid a deeply nested generated `do` block when
            # auditing many declarations, without changing elaborator limits.
            lines += [
                "run_cmd do",
                f"  let n := `{name}",
                "  match (← getEnv).find? n with",
                "  | some (.thmInfo _) => pure ()",
                f'  | _ => throwError "Not a theorem: {name}"',
                "  let axioms ← collectAxioms n",
                f'  logInfo m!"SIMJECTURE_AXIOMS {name}: {{axioms.toList}}"',
            ]
        (out / "Audit.lean").write_text("\n".join(lines) + "\n")
        code = run("audit", [*flags, "Audit.lean"], extra_path=True)
        report["audit_returncode"] = code
        audit = (out / "audit.log").read_text()
        for name in theorems:
            matches = re.findall(r"SIMJECTURE_AXIOMS " + re.escape(name) + r": \[([^\]]*)\]", audit)
            if len(matches) == 1:
                report["axioms"][name] = [a.strip() for a in matches[0].split(",") if a.strip()]
        report["checked"] = (
            code == 0
            and set(report["axioms"]) == set(theorems)
            and all(set(a) <= ALLOWED_AXIOMS for a in report["axioms"].values())
        )
        report["status"] = "proved" if report["checked"] else "undecided"
    except subprocess.TimeoutExpired:
        report["status"] = "timeout"
    except OSError as error:
        report["status"] = "unavailable"
        report["diagnostic"] = str(error)
    return finish()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--theorem", action="append", required=True)
    parser.add_argument("--output", default="lean-result")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--memory-mb", type=int, default=2048)
    args = parser.parse_args()
    result = check(
        args.source,
        args.theorem,
        output=args.output,
        timeout=args.timeout,
        memory_mb=args.memory_mb,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
