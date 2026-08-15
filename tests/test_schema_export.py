from __future__ import annotations

import json

from conjecture_solver.schema_export import PUBLIC_MODELS, export_schemas


def test_schema_export_is_stable_and_checkable(tmp_path) -> None:
    assert not export_schemas(tmp_path)
    assert not export_schemas(tmp_path, check=True)
    assert {path.stem for path in tmp_path.glob("*.json")} == {
        f"{model.__name__}.schema" for model in PUBLIC_MODELS
    }
    one_schema = tmp_path / "HypothesisNode.schema.json"
    document = json.loads(one_schema.read_text())
    assert document["title"] == "HypothesisNode"
    one_schema.write_text("{}\n")
    assert str(one_schema) in export_schemas(tmp_path, check=True)

