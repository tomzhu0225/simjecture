"""Verify the published Kepler study without model calls or new simulations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def verify(root: Path = HERE / "record") -> dict:
    manifest = json.loads((root / "manifest.json").read_text())
    for name, digest in manifest["files"].items():
        path = root / name
        if path.resolve().is_relative_to(root.resolve()) is False:
            raise ValueError(f"Record path escapes archive: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Record hash mismatch: {name}")

    study = json.loads((root / "research.json").read_text())
    reviews = [json.loads(p.read_text()) for p in (root / "reviews").glob("*.json")]
    approved = [r for r in reviews if r.get("verdict", {}).get("decision") == "approved"]
    assert any(
        r["claim"] == "root" and r["verdict"]["disposition"] == "falsified" for r in approved
    )
    supported = [
        r for r in approved if r["claim"] != "root" and r["verdict"]["disposition"] == "supported"
    ]
    assert supported, "The published full-loop demo needs a supported repair"
    experiments = {p.stem: json.loads(p.read_text()) for p in (root / "experiments").glob("*.json")}
    verified_cases, counterexamples = 0, []
    for identifier, experiment in experiments.items():
        workspace = root / "experiments" / identifier / "workspace"
        required = set(experiment["binding"]["inputs"]) | set(experiment["outputs"])
        assert required <= set(experiment["artifacts"])
        for name, meta in experiment.get("artifacts", {}).items():
            relative = str(workspace.relative_to(root) / name)
            if name not in required and name.startswith(".cache/fontconfig/"):
                assert manifest["omitted_artifacts"]["files"][relative] == meta["sha256"]
                continue
            assert relative in manifest["files"], f"Unlisted scientific file: {relative}"
            assert hashlib.sha256((workspace / name).read_bytes()).hexdigest() == meta["sha256"]
        if experiment["status"] != "succeeded" or not (workspace / "trajectories.npz").exists():
            continue
        result = json.loads((workspace / "result.json").read_text())
        with np.load(workspace / "trajectories.npz", allow_pickle=False) as arrays:
            for case in result["cases"]:
                key = f"e{case['e']:g}_n{case['steps_per_period']}"
                t, q, exact = (arrays[key + suffix] for suffix in ("_t", "_q_kdk", "_q_exact"))
                energy = arrays[key + "_rel_energy"]
                assert np.isfinite(t).all() and np.isfinite(q).all() and np.isfinite(exact).all()
                assert np.isfinite(energy).all()
                assert q.shape == exact.shape == (case["sample_count"], 2)
                assert len(t) == 20 * case["steps_per_period"] + 1
                assert np.isclose(t[-1], 40 * np.pi, rtol=0, atol=1e-11)
                position_error = float(np.linalg.norm(q - exact, axis=1).max())
                energy_error = float(np.abs(energy).max())
                assert np.isclose(position_error, case["max_position_error_a"], rtol=1e-12)
                assert np.isclose(energy_error, case["max_rel_energy_error"], rtol=1e-12)
                if case["e"] == 0:
                    np.testing.assert_allclose(
                        exact, np.column_stack((np.cos(t), np.sin(t))), rtol=0, atol=1e-12
                    )
                if (
                    experiment.get("commitment") is None
                    and case["e"] in (0.0, 0.3, 0.6)
                    and case["steps_per_period"] in (64, 128, 256, 512)
                    and energy_error < 0.001
                    and position_error > 0.01
                ):
                    counterexamples.append(
                        {"e": case["e"], "steps_per_period": case["steps_per_period"]}
                    )
                verified_cases += 1
    assert counterexamples, "No recorded counterexample meets both parts of the implication"
    for review in supported:
        commitment = json.loads((root / "commitments" / (review["claim"] + ".json")).read_text())
        records = [experiments[i] for i in review["experiments"]]
        assert all(
            r["status"] == "succeeded"
            and r["commitment"] == commitment["id"]
            and r["created_at"] >= commitment["created_at"]
            for r in records
        )
        assert all(b in [r["binding"] for r in records] for b in commitment["bindings"])
    return {
        "verified_files": len(manifest["files"]),
        "verified_numerical_cases": verified_cases,
        "counterexamples": counterexamples,
        "completion_policy": study["completion_policy"],
        "accepted_root_disposition": "falsified",
        "supported_repairs": len(supported),
        "scope": "Record integrity and retained numerical checks; no new scientific review.",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
