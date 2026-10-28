import json

import pytest
from simjecture_monitor.adapter_export import export_adapter, file_hash


def fixture_adapter(tmp_path):
    adapter = tmp_path / "original"
    adapter.mkdir()
    config = {
        "peft_type": "LORA",
        "base_model_name_or_path": "/old/runtime/model-cache",
        "revision": None,
        "r": 16,
        "lora_alpha": 32,
        "target_modules": ["q_proj", "v_proj"],
    }
    (adapter / "adapter_config.json").write_text(json.dumps(config))
    # The exporter preserves bytes; tensor correctness is a separate loader check.
    (adapter / "adapter_model.safetensors").write_bytes(b"evaluated-weight-file\x00\xff")
    arguments = dict(
        base_model="example/decision-model",
        revision="a" * 40,
        expected_weights_sha256=file_hash(adapter / "adapter_model.safetensors"),
        expected_config_sha256=file_hash(adapter / "adapter_config.json"),
    )
    return adapter, config, arguments


def test_portable_export_preserves_original_and_all_nonlocation_configuration(tmp_path):
    adapter, config, arguments = fixture_adapter(tmp_path)
    output = tmp_path / "export"
    manifest = export_adapter(adapter, output, **arguments)
    exported = json.loads((output / "adapter_config.json").read_text())
    assert exported == config | {
        "base_model_name_or_path": arguments["base_model"],
        "revision": arguments["revision"],
    }
    assert json.loads((adapter / "adapter_config.json").read_text()) == config
    assert (output / "adapter_model.safetensors").read_bytes() == (
        adapter / "adapter_model.safetensors"
    ).read_bytes()
    assert (
        manifest["files"]["adapter_model.safetensors"]["sha256"]
        == arguments["expected_weights_sha256"]
    )
    assert manifest["validation"]["runtime_reload_verified"] is False


def test_wrong_evaluated_identity_does_not_create_an_export(tmp_path):
    adapter, _, arguments = fixture_adapter(tmp_path)
    (adapter / "adapter_model.safetensors").write_bytes(b"a different checkpoint")
    with pytest.raises(ValueError, match="identity mismatch"):
        export_adapter(adapter, tmp_path / "export", **arguments)
    assert not (tmp_path / "export").exists()


def test_mutable_base_or_existing_output_is_rejected(tmp_path):
    adapter, _, arguments = fixture_adapter(tmp_path)
    with pytest.raises(ValueError, match="immutable"):
        export_adapter(adapter, tmp_path / "export", **(arguments | {"revision": "main"}))
    output = tmp_path / "export"
    output.mkdir()
    marker = output / "keep.txt"
    marker.write_text("previous export")
    with pytest.raises(FileExistsError):
        export_adapter(adapter, output, **arguments)
    assert marker.read_text() == "previous export"
