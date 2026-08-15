from __future__ import annotations

from conjecture_solver.mvp_monitor import ClaimSummary
from conjecture_solver.tui.claim_views import (
    audit_row_label,
    build_hypothesis_tree,
    build_validation_tree,
    hypothesis_row_label,
    scientific_ancestor_id,
    validation_row_label,
)


def _summary(
    claim_id: str,
    *,
    kind: str | None = "scientific",
    relation: str = "root",
    parent_id: str | None = None,
    statement: str | None = None,
) -> ClaimSummary:
    return ClaimSummary(
        id=claim_id,
        status="open",
        kind=kind,
        relation=relation,
        parent_id=parent_id,
        statement=statement or f"Statement for {claim_id}.",
    )


def test_typed_claims_project_into_scientific_and_validation_trees() -> None:
    claims = (
        _summary("claim_root"),
        _summary(
            "claim_child",
            relation="refines",
            parent_id="claim_root",
        ),
        _summary(
            "claim_alternate",
            relation="alternate",
            parent_id="claim_root",
        ),
        _summary(
            "claim_instrument",
            kind="instrument",
            relation="instrument_of",
            parent_id="claim_root",
        ),
        _summary(
            "claim_instrument_v2",
            kind="instrument",
            relation="succeeds",
            parent_id="claim_instrument",
        ),
        _summary(
            "claim_diagnostic",
            kind="diagnostic",
            relation="diagnostic_of",
            parent_id="claim_child",
        ),
    )

    hypotheses = build_hypothesis_tree(claims)
    assert [row.claim.id for row in hypotheses] == [
        "claim_root",
        "claim_child",
        "claim_alternate",
    ]
    assert [row.depth for row in hypotheses] == [0, 1, 1]
    assert [row.tree_prefix for row in hypotheses] == ["", "├─ ", "└─ "]
    root_validation = build_validation_tree(claims, "claim_root")
    assert [row.claim.id for row in root_validation] == [
        "claim_instrument",
        "claim_instrument_v2",
    ]
    assert [row.depth for row in root_validation] == [0, 1]
    assert [row.tree_prefix for row in root_validation] == ["", "└─ "]
    child_validation = build_validation_tree(claims, "claim_child")
    assert [row.claim.id for row in child_validation] == ["claim_diagnostic"]
    assert scientific_ancestor_id(claims, "claim_instrument_v2") == "claim_root"
    assert scientific_ancestor_id(claims, "claim_diagnostic") == "claim_child"


def test_hypothesis_projection_retains_orphans_and_legacy_root() -> None:
    claims = (
        _summary("claim_root", kind=None),
        _summary(
            "claim_orphan",
            relation="refines",
            parent_id="claim_missing",
        ),
    )
    rows = build_hypothesis_tree(claims)
    assert [row.claim.id for row in rows] == ["claim_root", "claim_orphan"]
    assert rows[0].orphaned is False
    assert rows[1].orphaned is True


def test_claim_labels_preserve_scientific_bracket_notation() -> None:
    hypothesis = _summary(
        "claim_root",
        statement="Density [cm^-3] remains inside interval [a,b].",
    )
    validation = _summary(
        "claim_control",
        kind="control",
        relation="control_for",
        parent_id="claim_root",
        statement="The [bold] control is literal text.",
    )
    hypothesis_label = hypothesis_row_label(build_hypothesis_tree((hypothesis,))[0])
    validation_label = validation_row_label(
        build_validation_tree((hypothesis, validation), "claim_root")[0]
    )
    assert "[cm^-3]" in hypothesis_label
    assert "[bold]" in validation_label
    assert "claim_control" in audit_row_label(validation)
