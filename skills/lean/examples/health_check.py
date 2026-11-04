"""Installation check: proof, false statement, placeholder, and non-theorem."""

import json
from pathlib import Path

from lean_check import ALLOWED_AXIOMS, check

cases = {
    "valid_proof": "import Mathlib.Tactic.Ring\ntheorem sample (x : ℚ) : x + 0 = x := by ring\n",
    "false_claim_unproved": "theorem sample : (1 : Nat) = 2 := by decide\n",
    "placeholder_rejected": "theorem sample : False := by sorry\n",
    "definition_rejected": "def sample : Nat := 42\n",
    "native_axiom_rejected": (
        "import Std.Tactic\ntheorem sample : (1 : Nat) = 1 := by native_decide\n"
    ),
}
checks = {}
for name, source in cases.items():
    path = Path(name + ".lean")
    path.write_text(source)
    result = check(path, ["sample"], output=name, timeout=25)
    if name == "valid_proof":
        checks[name] = result["checked"]
    elif name == "placeholder_rejected":
        checks[name] = result["status"] == "rejected_source"
    elif name == "false_claim_unproved":
        checks[name] = result["status"] == "undecided" and result.get("compile_returncode") == 1
    elif name == "definition_rejected":
        checks[name] = (
            result.get("compile_returncode") == 0
            and result.get("audit_returncode") == 1
            and "Not a theorem" in (Path(name) / "audit.log").read_text()
        )
    else:
        checks[name] = (
            result.get("compile_returncode") == 0
            and result.get("audit_returncode") == 0
            and bool(set(result.get("axioms", {}).get("sample", [])) - ALLOWED_AXIOMS)
        )
Path("lean_health.json").write_text(json.dumps({"checks": checks}, indent=2))
assert all(checks.values()), checks
