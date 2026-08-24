"""Small, deliberately boring schemas for the Simjecture MCP bridge.

The DSH MCP client consumes a conservative JSON-Schema subset.  In particular,
it does not need (and should not be exposed to) the large Pydantic unions used by
the model-facing MVP loop.  This module therefore keeps the wire schemas as
plain dictionaries and performs the authoritative validation in Python before
an action reaches :class:`CampaignKernel`.

Keeping the schema vocabulary here also makes it possible to inspect the tool
catalog without importing the optional MCP SDK or the campaign kernel.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

# DSH's MCP bridge intentionally supports this small intersection of JSON
# Schema implementations.  Do not add descriptions, defaults, $defs, nullable
# type arrays, minLength, or pattern constraints to the advertised schemas.
ALLOWED_SCHEMA_KEYS = frozenset(
    {
        "object",
        "properties",
        "required",
        "additionalProperties",
        "type",
        "enum",
        "const",
        "items",
        "oneOf",
    }
)


def _string() -> dict[str, Any]:
    return {"type": "string"}


def _integer() -> dict[str, Any]:
    return {"type": "integer"}


def _boolean() -> dict[str, Any]:
    return {"type": "boolean"}


def _array(item: Mapping[str, Any]) -> dict[str, Any]:
    return {"type": "array", "items": dict(item)}


def _object(properties: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {key: dict(value) for key, value in (properties or {}).items()},
        "additionalProperties": False,
    }


def _free_object() -> dict[str, Any]:
    return {"type": "object", "additionalProperties": True}


def _nullable_string() -> dict[str, Any]:
    return {"oneOf": [_string(), {"const": None}]}


_RESEARCH_NOTE = {"research_note": _string()}
_ACTIVE_CLAIM = {"active_claim_id": _nullable_string()}
_OPERATION_ID = {"operation_id": _string()}


CLAIM_KINDS = ["scientific", "instrument", "diagnostic", "control"]
CLAIM_RELATIONS = [
    "repairs",
    "refines",
    "alternate",
    "diagnostic_of",
    "instrument_of",
    "control_for",
    "succeeds",
]
CLAIM_STATUSES = [
    "supported",
    "weakened",
    "falsified",
    "superseded",
    "unresolved",
    "instrument_limited",
]
CAPABILITY_STAGES = ["workbench", "evidence"]

# These calls change durable campaign state.  Every one carries an explicit
# caller-owned id so a DSH retry can replay the same operation safely.
MUTATING_TOOLS = frozenset(
    {
        "register_claim",
        "register_evidence_contract",
        "link_claim_evidence",
        "close_claim",
        "materialize_skill",
        "search_literature",
        "write_workspace_file",
        "run_python",
        "run_workbench_capability",
        "run_evidence_capability",
        "cancel_job",
        "record_adjudication",
        "finalize_campaign",
    }
)


_VALIDATION_CHECK = _object(
    {
        "aspect": _nullable_string(),
        "json_path": _string(),
        "expected_value": {
            "oneOf": [
                _string(),
                _integer(),
                {"type": "number"},
                _boolean(),
                {"const": None},
            ]
        },
    }
)
_EXECUTION_BINDING = _object(
    {
        "capability": _string(),
        "program_path": _string(),
        "program_sha256": _nullable_string(),
        "commissioning_argv": _array(_string()),
        "allowed_scientific_argv": _array(_array(_string())),
    }
)
_REPAIR_CONTEXT = _object(
    {
        "counterexample_paths": _array(_string()),
        "accommodation": _string(),
        "semantic_change": _string(),
        "falsification_condition": _string(),
    }
)
_JUDGE_VERDICT = _object(
    {
        "claim_id": _string(),
        "contract_version": _integer(),
        "decision": {"enum": ["sufficient", "insufficient"]},
        "rationale": _string(),
        "evidence_gaps": _array(_string()),
        "next_test": _nullable_string(),
    }
)


# Only these keys are sent over the wire.  Descriptions live in TOOL_DESCRIPTIONS
# because descriptions are not part of the DSH-compatible schema subset.
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "snapshot": _object({}),
    "register_claim": _object(
        {
            "claim_id": _string(),
            "statement": _string(),
            "kind": {"enum": CLAIM_KINDS},
            "relation": {"enum": CLAIM_RELATIONS},
            "parent_id": _string(),
            "rationale": _string(),
            "repair": {"oneOf": [_REPAIR_CONTEXT, {"const": None}]},
            **_OPERATION_ID,
            **_RESEARCH_NOTE,
        }
    ),
    "register_evidence_contract": _object(
        {
            "claim_id": _string(),
            "observable": _string(),
            "expected_outcomes": _string(),
            "decision_rule": _string(),
            "required_observation": _string(),
            "uncertainty_criterion": _string(),
            "inconclusive_conditions": _string(),
            "validation_checks": _array(_VALIDATION_CHECK),
            "execution_binding": {"oneOf": [_EXECUTION_BINDING, {"const": None}]},
            "additional_execution_bindings": _array(_EXECUTION_BINDING),
            **_OPERATION_ID,
            **_RESEARCH_NOTE,
        }
    ),
    "link_claim_evidence": _object(
        {
            "claim_id": _string(),
            "path": _string(),
            "note": _string(),
            "observation_sufficient": _boolean(),
            "observation_note": _string(),
            "commissioning_claim_id": _nullable_string(),
            **_OPERATION_ID,
            **_RESEARCH_NOTE,
        }
    ),
    "close_claim": _object(
        {
            "claim_id": _string(),
            "status": {"enum": CLAIM_STATUSES},
            "reason": _string(),
            **_OPERATION_ID,
            **_RESEARCH_NOTE,
        }
    ),
    "claims": _object(
        {
            "view": {"enum": ["summary", "role", "full"]},
            "claim_ids": _array(_string()),
            "parent_id": _nullable_string(),
            "offset": _integer(),
            "limit": _integer(),
        }
    ),
    "list_skills": _object({}),
    "read_skill": _object(
        {
            "skill": _string(),
            "path": _nullable_string(),
            **_RESEARCH_NOTE,
        }
    ),
    "materialize_skill": _object(
        {
            "skill": _string(),
            "source_path": _string(),
            "destination_path": _string(),
            **_OPERATION_ID,
            **_RESEARCH_NOTE,
        }
    ),
    "search_literature": _object(
        {
            "query": _string(),
            "purpose": _string(),
            "max_results": _integer(),
            **_OPERATION_ID,
            **_RESEARCH_NOTE,
        }
    ),
    "read_workspace_file": _object(
        {
            "path": _string(),
            "start_line": _integer(),
            "line_count": _integer(),
            **_RESEARCH_NOTE,
        }
    ),
    "write_workspace_file": _object(
        {
            "path": _string(),
            "content": _string(),
            **_OPERATION_ID,
            **_RESEARCH_NOTE,
        }
    ),
    "list_workspace_files": _object(
        {
            "path": _string(),
            **_RESEARCH_NOTE,
        }
    ),
    "run_python": _object(
        {
            "argv": _array(_string()),
            **_OPERATION_ID,
            **_ACTIVE_CLAIM,
            "timeout_seconds": {"oneOf": [_integer(), {"type": "number"}]},
            **_RESEARCH_NOTE,
        }
    ),
    "run_workbench_capability": _object(
        {
            "capability": _string(),
            "argv": _array(_string()),
            **_OPERATION_ID,
            **_ACTIVE_CLAIM,
            "timeout_seconds": {"oneOf": [_integer(), {"type": "number"}]},
            **_RESEARCH_NOTE,
        }
    ),
    "run_evidence_capability": _object(
        {
            "capability": _string(),
            "argv": _array(_string()),
            **_OPERATION_ID,
            "active_claim_id": _string(),
            "timeout_seconds": {"oneOf": [_integer(), {"type": "number"}]},
            **_RESEARCH_NOTE,
        }
    ),
    "job_status": _object({"job_id": _string(), "report": _boolean()}),
    "cancel_job": _object({"job_id": _string(), **_OPERATION_ID}),
    # These two endpoints are hidden from the researcher agent by the DSH
    # scoped tool restriction. The composite simjecture_adjudicate tool alone
    # uses them around a fresh, tool-free judge subagent.
    "prepare_adjudication": _object(
        {
            "operation_id": _string(),
            "claim_id": _string(),
            "contract_version": _integer(),
            "case_for_sufficiency": _string(),
        }
    ),
    "record_adjudication": _object(
        {
            "operation_id": _string(),
            "claim_id": _string(),
            "contract_version": _integer(),
            "case_for_sufficiency": _string(),
            "case_sha256": _string(),
            "verdict": _JUDGE_VERDICT,
            "model": _string(),
            "route": _string(),
            "judge_run_id": _string(),
            "usage": _free_object(),
        }
    ),
    "finalize_campaign": _object(
        {
            "operation_id": _string(),
            "final_answer": _string(),
        }
    ),
}


TOOL_REQUIRED: dict[str, tuple[str, ...]] = {
    "register_claim": (
        "operation_id",
        "claim_id",
        "statement",
        "kind",
        "relation",
        "parent_id",
        "rationale",
    ),
    "register_evidence_contract": (
        "operation_id",
        "claim_id",
        "observable",
        "expected_outcomes",
        "decision_rule",
        "required_observation",
        "uncertainty_criterion",
        "inconclusive_conditions",
    ),
    "link_claim_evidence": (
        "operation_id",
        "claim_id",
        "path",
        "note",
        "observation_sufficient",
        "observation_note",
    ),
    "close_claim": ("operation_id", "claim_id", "status", "reason"),
    "read_skill": ("skill",),
    "materialize_skill": ("operation_id", "skill", "source_path", "destination_path"),
    "search_literature": ("operation_id", "query", "purpose"),
    "read_workspace_file": ("path",),
    "write_workspace_file": ("operation_id", "path", "content"),
    "list_workspace_files": (),
    "run_python": ("operation_id", "argv"),
    "run_workbench_capability": ("operation_id", "capability", "argv"),
    "run_evidence_capability": (
        "operation_id",
        "capability",
        "argv",
        "active_claim_id",
    ),
    "job_status": ("job_id",),
    "cancel_job": ("operation_id", "job_id"),
    "prepare_adjudication": (
        "operation_id",
        "claim_id",
        "contract_version",
        "case_for_sufficiency",
    ),
    "record_adjudication": (
        "operation_id",
        "claim_id",
        "contract_version",
        "case_for_sufficiency",
        "case_sha256",
        "verdict",
        "model",
        "route",
        "judge_run_id",
    ),
    "finalize_campaign": ("operation_id", "final_answer"),
}

# Keep the required list in the advertised schema as well as in the Python
# validator.  The duplicate declaration is deliberate: DSH can reject a
# malformed call before crossing the process boundary, while Python still
# validates calls made directly in tests or by another MCP client.
for _tool_name, _required in TOOL_REQUIRED.items():
    TOOL_SCHEMAS[_tool_name]["required"] = list(_required)
for _tool_name in TOOL_SCHEMAS:
    TOOL_SCHEMAS[_tool_name].setdefault("required", [])


TOOL_DESCRIPTIONS: dict[str, str] = {
    "snapshot": "Read the bounded durable campaign snapshot and lifecycle state.",
    "claims": (
        "Read a bounded claim-ledger projection. The default summary is paged; "
        "use view=role with explicit claim_ids for executable contracts and "
        "evidence, or view=full only for bounded diagnosis. Claims are not "
        "evidence until linked artifacts satisfy a contract."
    ),
    "register_claim": "Register a stable scientific, instrument, diagnostic, or control claim.",
    "register_evidence_contract": (
        "Register a prospective evidence contract before linking an observation."
    ),
    "link_claim_evidence": (
        "Link one workspace artifact to a claim and record sufficiency/provenance."
    ),
    "close_claim": "Close a claim with an explicit disposition and reason.",
    "list_skills": "List immutable host-installed scientific skills.",
    "read_skill": "Read bounded immutable guidance from one installed skill.",
    "materialize_skill": (
        "Copy an immutable skill resource into the workspace as non-evidence guidance."
    ),
    "search_literature": (
        "Search public literature metadata; search results are never campaign evidence."
    ),
    "read_workspace_file": (
        "Read one bounded text file or a start_line/line_count window from the "
        "campaign workspace. Use this instead of executing code merely to print files."
    ),
    "write_workspace_file": "Write one bounded text file in the campaign workspace.",
    "list_workspace_files": (
        "List bounded workspace paths without exposing a generic filesystem tool."
    ),
    "run_python": (
        "Start one sandboxed Python job under a caller-chosen operation id and "
        "return its durable job id. Reuse replays; conflicting reuse is rejected."
    ),
    "run_workbench_capability": (
        "Start one non-evidentiary capability workbench job under a unique operation id."
    ),
    "run_evidence_capability": (
        "Start one prospectively contracted evidence capability job under a unique operation id."
    ),
    "job_status": (
        "Read one scientific job. Omit report (or set it true) for bounded "
        "terminal diagnostics; harness pollers may set report=false for the "
        "small lifecycle state."
    ),
    "cancel_job": "Request cancellation of one scientific job.",
    "prepare_adjudication": (
        "Internal DSH endpoint: freeze a bounded prospective evidence case for an isolated judge."
    ),
    "record_adjudication": (
        "Internal DSH endpoint: commit the structured verdict returned by the isolated judge."
    ),
    "finalize_campaign": (
        "Write the terminal auditable report after every scientific finish gate passes."
    ),
}


def tool_definitions() -> tuple[dict[str, Any], ...]:
    """Return fresh MCP tool definition dictionaries.

    A fresh copy prevents an SDK or caller from mutating the module-level
    catalog, which would otherwise make a later DSH reconnect advertise a
    different schema.
    """

    return tuple(
        {
            "name": name,
            "description": TOOL_DESCRIPTIONS[name],
            "inputSchema": deepcopy(TOOL_SCHEMAS[name]),
        }
        for name in TOOL_SCHEMAS
    )


def _schema_error(path: str, message: str) -> ValueError:
    return ValueError(f"invalid MCP schema at {path}: {message}")


def validate_schema_subset(schema: Mapping[str, Any], *, path: str = "$schema") -> None:
    """Reject schema vocabulary outside the DSH compatibility subset."""

    if not isinstance(schema, Mapping):
        raise _schema_error(path, "schema must be an object")
    unknown = set(schema) - ALLOWED_SCHEMA_KEYS
    if unknown:
        raise _schema_error(path, f"unsupported keyword(s): {sorted(unknown)}")
    schema_type = schema.get("type")
    if schema_type is not None and schema_type not in {
        "object",
        "array",
        "string",
        "integer",
        "number",
        "boolean",
    }:
        raise _schema_error(path, f"unsupported type {schema_type!r}")
    if "required" in schema:
        required = schema["required"]
        if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
            raise _schema_error(f"{path}.required", "must be a list of strings")
    if "properties" in schema:
        properties = schema["properties"]
        if not isinstance(properties, Mapping):
            raise _schema_error(f"{path}.properties", "must be an object")
        for name, child in properties.items():
            if not isinstance(name, str):
                raise _schema_error(f"{path}.properties", "property names must be strings")
            validate_schema_subset(child, path=f"{path}.properties.{name}")
    if "items" in schema:
        validate_schema_subset(schema["items"], path=f"{path}.items")
    if "oneOf" in schema:
        choices = schema["oneOf"]
        if not isinstance(choices, list) or not choices:
            raise _schema_error(f"{path}.oneOf", "must be a non-empty list")
        for index, child in enumerate(choices):
            validate_schema_subset(child, path=f"{path}.oneOf[{index}]")
    if "enum" in schema and not isinstance(schema["enum"], list):
        raise _schema_error(f"{path}.enum", "must be a list")


def validate_catalog() -> None:
    """Validate every advertised schema at import/test time."""

    for name, schema in TOOL_SCHEMAS.items():
        validate_schema_subset(schema, path=f"tools.{name}.inputSchema")
        if schema.get("type") != "object":
            raise _schema_error(f"tools.{name}", "tool input schema must be an object")
        properties = schema.get("properties", {})
        required = set(TOOL_REQUIRED.get(name, ()))
        if not required.issubset(properties):
            missing = sorted(required - set(properties))
            raise _schema_error(
                f"tools.{name}",
                f"required property missing from schema: {missing}",
            )
        if name in MUTATING_TOOLS and "operation_id" not in required:
            raise _schema_error(
                f"tools.{name}",
                "mutating tool must require operation_id",
            )


def _matches_type(value: Any, schema_type: str) -> bool:
    if schema_type == "object":
        return isinstance(value, Mapping)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    return True


def _validate_shape(value: Any, schema: Mapping[str, Any], *, path: str) -> None:
    if "oneOf" in schema:
        errors: list[str] = []
        for choice in schema["oneOf"]:
            try:
                _validate_shape(value, choice, path=path)
                return
            except ValueError as error:
                errors.append(str(error))
        raise ValueError(f"{path} does not match oneOf: {errors[0] if errors else 'no choices'}")
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{path} must equal {schema['const']!r}")
    schema_type = schema.get("type")
    if schema_type is not None and not _matches_type(value, schema_type):
        raise ValueError(f"{path} must have type {schema_type}")
    enum = schema.get("enum")
    if enum is not None and value not in enum:
        raise ValueError(f"{path} must be one of {enum!r}")
    if schema_type == "object":
        properties = schema.get("properties", {})
        unknown = set(value) - set(properties)
        if schema.get("additionalProperties") is False and unknown:
            raise ValueError(f"{path} contains unsupported field(s): {sorted(unknown)}")
        for key, child in properties.items():
            if key in value:
                _validate_shape(value[key], child, path=f"{path}.{key}")
    elif schema_type == "array" and "items" in schema:
        for index, item in enumerate(value):
            _validate_shape(item, schema["items"], path=f"{path}[{index}]")


def _validate_input_bounds(name: str, value: Any, *, field: str = "arguments") -> None:
    """Apply limits that are intentionally absent from the advertised schema."""

    if isinstance(value, str):
        if len(value) > 16_384:
            raise ValueError(f"{name}.{field} exceeds the 16,384-character input limit")
        if "argv[" in field and ("\x00" in value or len(value) > 4_096):
            raise ValueError(f"{name}.argv contains an invalid argument")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_input_bounds(name, item, field=f"{field}[{index}]")
        return
    if not isinstance(value, Mapping):
        return
    for key, child in value.items():
        child_field = f"{field}.{key}"
        if key in {"path", "source_path", "destination_path", "program_path"}:
            if not isinstance(child, str) or not child or "\x00" in child:
                raise ValueError(f"{name}.{key} must be a non-empty path without NUL")
            from pathlib import PurePosixPath

            path = PurePosixPath(child)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"{name}.{key} must stay within the relative workspace")
        if key == "timeout_seconds" and (child <= 0 or child > 86_400):
            raise ValueError(f"{name}.timeout_seconds must lie in (0, 86400]")
        if key == "start_line" and (child < 1 or child > 10_000_000):
            raise ValueError(f"{name}.start_line must lie in [1, 10000000]")
        if key == "line_count" and (child < 1 or child > 400):
            raise ValueError(f"{name}.line_count must lie in [1, 400]")
        if key == "operation_id" and (
            not isinstance(child, str) or not child or len(child) > 256 or "\x00" in child
        ):
            raise ValueError(f"{name}.operation_id must contain 1 to 256 non-NUL characters")
        if (key == "argv" or key.endswith("_argv")) and (
            not isinstance(child, list) or not child or len(child) > 256
        ):
            raise ValueError(f"{name}.{key} must contain 1 to 256 arguments")
        _validate_input_bounds(name, child, field=child_field)


def validate_tool_arguments(name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and copy one tool call before dispatching it to the kernel.

    This intentionally complements rather than replaces the campaign's typed
    Pydantic validation.  The bridge rejects malformed JSON shapes and unsafe
    obvious inputs early, while the kernel remains authoritative for scientific
    and lifecycle invariants.
    """

    if name not in TOOL_SCHEMAS:
        raise ValueError(f"unknown scientific MCP tool {name!r}")
    if not isinstance(arguments, Mapping):
        raise ValueError("tool arguments must be a JSON object")
    copied = dict(arguments)
    required = TOOL_REQUIRED.get(name, ())
    missing = [field for field in required if field not in copied]
    if missing:
        raise ValueError(f"missing required argument(s): {', '.join(missing)}")
    _validate_shape(copied, TOOL_SCHEMAS[name], path=f"{name}.arguments")
    _validate_input_bounds(name, copied)
    return copied


validate_catalog()

# Public aliases used by lightweight integrations and tests.
MCP_TOOL_SCHEMAS = TOOL_SCHEMAS
MCP_TOOL_DEFINITIONS = tool_definitions
