"""Regression tests for the lightweight public MCP argument validator."""

from __future__ import annotations

import pytest

from conjecture_solver.mcp_schemas import validate_tool_arguments


@pytest.mark.parametrize("artifact", [{}, {"path": "input.json"}, {"sha256": "a" * 64}])
def test_artifact_inputs_require_both_path_and_hash(artifact):
    with pytest.raises(ValueError, match=r"input_artifacts\[0\].*missing required"):
        validate_tool_arguments(
            "run_python",
            {"argv": ["measure.py"], "input_artifacts": [artifact], "operation_id": "run-1"},
        )


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_timeouts_are_rejected(timeout):
    with pytest.raises(ValueError):
        validate_tool_arguments(
            "run_python",
            {"argv": ["measure.py"], "timeout_seconds": timeout, "operation_id": "run-1"},
        )


@pytest.mark.parametrize("timeout", [1, 0.5, 86400])
def test_valid_timeout_and_complete_artifact_remain_accepted(timeout):
    arguments = {
        "argv": ["measure.py"], "operation_id": "run-1", "timeout_seconds": timeout,
        "input_artifacts": [{"path": "input.json", "sha256": "a" * 64}],
    }
    assert validate_tool_arguments("run_python", arguments) == arguments
