"""Human-first projections of the durable typed claim ledger."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ..mvp_monitor import ClaimSummary, claim_status_marker

SCIENTIFIC_KIND = "scientific"


@dataclass(frozen=True)
class ClaimTreeRow:
    """One claim and its visual depth in a projected tree."""

    claim: ClaimSummary
    depth: int
    tree_prefix: str = ""
    orphaned: bool = False


def build_hypothesis_tree(claims: Iterable[ClaimSummary]) -> tuple[ClaimTreeRow, ...]:
    """Return only scientific claims in parent-before-child order.

    The durable ledger is normally a valid acyclic graph. The projection still
    retains malformed or legacy scientific records as top-level orphan rows so
    the human interface never hides them.
    """

    ordered = tuple(claim for claim in claims if _is_scientific(claim))
    by_id = {claim.id: claim for claim in ordered}
    children: dict[str, list[ClaimSummary]] = {}
    for claim in ordered:
        if claim.parent_id in by_id:
            children.setdefault(claim.parent_id, []).append(claim)

    roots = [claim for claim in ordered if claim.id == "claim_root"]
    roots.extend(
        claim
        for claim in ordered
        if claim.id != "claim_root"
        and (claim.relation == "root" or claim.parent_id not in by_id)
    )
    rows: list[ClaimTreeRow] = []
    visited: set[str] = set()

    def visit(
        claim: ClaimSummary,
        depth: int,
        *,
        prefix: str,
        connector: str,
        orphaned: bool,
    ) -> None:
        if claim.id in visited:
            return
        visited.add(claim.id)
        rows.append(
            ClaimTreeRow(
                claim=claim,
                depth=depth,
                tree_prefix=prefix + connector,
                orphaned=orphaned,
            )
        )
        child_prefix = prefix + ("│  " if connector == "├─ " else "   " if connector else "")
        child_claims = children.get(claim.id, [])
        for index, child in enumerate(child_claims):
            visit(
                child,
                depth + 1,
                prefix=child_prefix,
                connector="└─ " if index == len(child_claims) - 1 else "├─ ",
                orphaned=orphaned,
            )

    for root in roots:
        visit(
            root,
            0,
            prefix="",
            connector="",
            orphaned=root.id != "claim_root" and root.relation != "root",
        )
    for claim in ordered:
        if claim.id not in visited:
            visit(claim, 0, prefix="", connector="", orphaned=True)
    return tuple(rows)


def scientific_ancestor_id(
    claims: Iterable[ClaimSummary],
    claim_id: str,
) -> str | None:
    """Find the nearest scientific claim at or above ``claim_id``."""

    by_id = {claim.id: claim for claim in claims}
    current = by_id.get(claim_id)
    visited: set[str] = set()
    while current is not None and current.id not in visited:
        visited.add(current.id)
        if _is_scientific(current):
            return current.id
        current = by_id.get(current.parent_id or "")
    return None


def build_validation_tree(
    claims: Iterable[ClaimSummary],
    scientific_claim_id: str,
) -> tuple[ClaimTreeRow, ...]:
    """Project validation claims owned by one scientific hypothesis.

    Direct instrument, diagnostic, and control claims are included together
    with non-scientific ``succeeds`` descendants. Validation claims belonging
    to a daughter hypothesis remain with that daughter rather than its parent.
    """

    ordered = tuple(claims)
    candidates = tuple(
        claim
        for claim in ordered
        if not _is_scientific(claim)
        and scientific_ancestor_id(ordered, claim.id) == scientific_claim_id
    )
    by_id = {claim.id: claim for claim in candidates}
    children: dict[str, list[ClaimSummary]] = {}
    for claim in candidates:
        if claim.parent_id in by_id:
            children.setdefault(claim.parent_id, []).append(claim)
    roots = [claim for claim in candidates if claim.parent_id not in by_id]
    rows: list[ClaimTreeRow] = []
    visited: set[str] = set()

    def visit(claim: ClaimSummary, depth: int, *, prefix: str, connector: str) -> None:
        if claim.id in visited:
            return
        visited.add(claim.id)
        rows.append(
            ClaimTreeRow(
                claim=claim,
                depth=depth,
                tree_prefix=prefix + connector,
            )
        )
        child_prefix = prefix + ("│  " if connector == "├─ " else "   " if connector else "")
        child_claims = children.get(claim.id, [])
        for index, child in enumerate(child_claims):
            visit(
                child,
                depth + 1,
                prefix=child_prefix,
                connector="└─ " if index == len(child_claims) - 1 else "├─ ",
            )

    for root in roots:
        visit(root, 0, prefix="", connector="")
    for claim in candidates:
        if claim.id not in visited:
            rows.append(ClaimTreeRow(claim=claim, depth=0, orphaned=True))
    return tuple(rows)


def hypothesis_row_label(row: ClaimTreeRow, *, width: int = 68) -> str:
    claim = row.claim
    relation = "root" if claim.relation == "root" else (claim.relation or "scientific")
    flags = []
    if row.orphaned:
        flags.append("orphan")
    if claim.active:
        flags.append("current")
    suffix = f"  ({', '.join(flags)})" if flags else ""
    metadata = (
        f"{claim_status_marker(claim.status)} {relation:<9} {claim.status:<18} "
        f"E{claim.evidence_count}/C{claim.contract_count}  "
    )
    return row.tree_prefix + metadata + _ellipsize(claim.statement or claim.id, width) + suffix


def validation_row_label(row: ClaimTreeRow, *, width: int = 68) -> str:
    claim = row.claim
    kind = claim.kind or "unknown"
    flags = "  (current)" if claim.active else ""
    metadata = (
        f"{claim_status_marker(claim.status)} {kind:<11} {claim.status:<18} "
        f"E{claim.evidence_count}/C{claim.contract_count}  "
    )
    return row.tree_prefix + metadata + _ellipsize(claim.statement or claim.id, width) + flags


def audit_row_label(claim: ClaimSummary, *, width: int = 56) -> str:
    kind = claim.kind or "unknown"
    relation = claim.relation or "unrelated"
    return (
        f"{claim_status_marker(claim.status)} {kind:<11} {relation:<14} "
        f"{claim.id:<26} {_ellipsize(claim.statement, width)}"
    )


def _ellipsize(text: str, width: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= width:
        return compact
    if width <= 1:
        return "…"
    return compact[: width - 1].rstrip() + "…"


def _is_scientific(claim: ClaimSummary) -> bool:
    return claim.kind == SCIENTIFIC_KIND or (
        claim.id == "claim_root" and claim.relation == "root"
    )
