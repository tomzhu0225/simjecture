from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from conjecture_solver.cli import build_parser
from conjecture_solver.domains import installed_domain_plugins
from conjecture_solver.domains.base import DomainPlugin, DomainPluginRegistry
from conjecture_solver.domains.kinetic_sufficiency import (
    KineticSufficiencyDiscoveryPackage,
    KineticSufficiencyDomainPlugin,
    KineticSufficiencyHypothesisInput,
    default_kinetic_sufficiency_hypothesis_input,
    solve_kinetic_sufficiency,
)


def test_builtin_registry_exposes_the_bounded_analytic_plugin() -> None:
    registry = installed_domain_plugins()
    assert registry.names == ("kinetic-sufficiency",)
    assert all(isinstance(plugin, DomainPlugin) for plugin in registry.plugins)
    assert {plugin.metadata.hypothesis_schema for plugin in registry.plugins} == {
        "KineticSufficiencyHypothesisInput"
    }


def test_generic_cli_builds_the_installed_domain_subcommand() -> None:
    parser = build_parser()
    kinetic = parser.parse_args(
        ["solve", "kinetic-sufficiency", "hypothesis.json", "--ledger", "run.sqlite3"]
    )
    assert kinetic.domain_plugin == "kinetic-sufficiency"
    assert kinetic.ledger == "run.sqlite3"


def test_kinetic_domain_runs_headlessly_replays_and_verifies(tmp_path: Path) -> None:
    plugin = KineticSufficiencyDomainPlugin()
    hypothesis_path = tmp_path / "hypothesis.json"
    plugin.write_template(argparse.Namespace(output=str(hypothesis_path)))
    args = argparse.Namespace(
        hypothesis=str(hypothesis_path),
        campaign_id="checkpoint22_second_domain",
        ledger=str(tmp_path / "ledger.sqlite3"),
        output=str(tmp_path / "output"),
    )
    first = plugin.solve(args)
    event_count = _event_count(Path(args.ledger))
    second = plugin.solve(args)

    assert first == second
    assert first.disposition == "refuted_within_model"
    assert first.metrics["qualified"] is True
    assert first.metrics["moments_match"] is True
    assert _event_count(Path(args.ledger)) == event_count == 6
    package = KineticSufficiencyDiscoveryPackage.read_verified(first.package_path)
    assert package.verify_hash()
    assert package.package_hash == first.package_hash
    registry_match = installed_domain_plugins().recognize_package(
        json.loads(Path(first.package_path).read_text())
    )
    assert registry_match is not None
    assert registry_match.metadata.name == "kinetic-sufficiency"


def test_kinetic_domain_accepts_a_fresh_bounded_hypothesis() -> None:
    template = default_kinetic_sufficiency_hypothesis_input()
    formal = template.hypothesis.formal_predicate
    assert formal is not None
    relaxed_tolerance = 0.4
    hypothesis = template.hypothesis.model_copy(
        update={
            "id": "hypothesis_fresh_relaxed_kinetic_sufficiency",
            "statement": (
                "The first three moments predict the dominant growth rate within 0.4 "
                "for the declared Gaussian-mixture pair."
            ),
            "machine_predicate": (
                "equal(n, mean_v, variance) implies "
                "abs(gamma_left-gamma_right) <= 0.4"
            ),
            "formal_predicate": formal.model_copy(
                update={"maximum_outcome_difference": relaxed_tolerance}
            ),
            "evidence_contract": template.hypothesis.evidence_contract.model_copy(
                update={"primary_tolerance": relaxed_tolerance}
            ),
        }
    )
    fresh = KineticSufficiencyHypothesisInput.model_validate(
        {**template.model_dump(mode="json"), "hypothesis": hypothesis.model_dump(mode="json")}
    )
    result = solve_kinetic_sufficiency(fresh)
    assert result.qualified
    assert not result.witness.falsifies


def test_kinetic_domain_rejects_an_unmatched_pair_before_execution() -> None:
    payload = default_kinetic_sufficiency_hypothesis_input().model_dump(mode="json")
    payload["right_distribution"]["components"][0]["drift"] = -0.8
    with pytest.raises(ValueError, match="input_pair_matches_declared_coordinates"):
        KineticSufficiencyHypothesisInput.model_validate(payload)


def test_domain_package_tampering_is_detected(tmp_path: Path) -> None:
    plugin = KineticSufficiencyDomainPlugin()
    hypothesis_path = tmp_path / "hypothesis.json"
    plugin.write_template(argparse.Namespace(output=str(hypothesis_path)))
    summary = plugin.solve(
        argparse.Namespace(
            hypothesis=str(hypothesis_path),
            campaign_id="checkpoint22_tamper",
            ledger=str(tmp_path / "ledger.sqlite3"),
            output=str(tmp_path / "output"),
        )
    )
    payload = json.loads(Path(summary.package_path).read_text())
    payload["claim"]["statement"] = "tampered"
    Path(summary.package_path).write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="package hash"):
        plugin.read_verified_package(summary.package_path)


def test_registry_rejects_duplicate_plugin_names() -> None:
    plugin = KineticSufficiencyDomainPlugin()
    with pytest.raises(ValueError, match="must be unique"):
        DomainPluginRegistry((plugin, plugin))


def _event_count(path: Path) -> int:
    import sqlite3

    with sqlite3.connect(path) as connection:
        row = connection.execute("SELECT count(*) FROM campaign_events").fetchone()
    assert row is not None
    return int(row[0])
