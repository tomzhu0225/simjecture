"""Fixed expert-attention control, with no anomaly classification or model call."""

from __future__ import annotations

from .attention_support import Choice


class RoutineHelpPolicy:
    """Request a source/context check at the first eligible parked opportunity.

    The normal host still checks current state, persistence, pending assistance,
    and actual dispatch limits. Citing a visible source does not establish that
    an anomaly exists or that a routine check has positive downstream value.
    """

    def predict(self, packet, view):
        aliases = [
            alias for alias, identifier in view.aliases.items() if identifier in view.included_ids
        ]
        if view.status != "ready" or not aliases:
            return Choice(
                action="observe",
                support_kind="none",
                question_ref=None,
                basis="unspecified",
                evidence=[],
            )
        return Choice(
            action="request_worker_help",
            support_kind="none",
            question_ref=None,
            basis="source",
            evidence=[aliases[0]],
        )
