from __future__ import annotations

import asyncio
import base64
import hashlib
from pathlib import Path

import pytest
from PIL import Image

from conjecture_solver.mcp_server import BridgeConfig, CampaignMCPBridge, _sdk_result
from conjecture_solver.workspace_images import MAX_IMAGE_BYTES, read_workspace_image


def test_image_bridge_returns_pixels_and_hash_without_text_truncation(tmp_path: Path) -> None:
    path = tmp_path / "plot.png"
    Image.new("RGB", (64, 32), "red").save(path)

    class Kernel:
        def read_workspace_image(self, path: str):
            return read_workspace_image(tmp_path, path)

    bridge = CampaignMCPBridge(Kernel(), config=BridgeConfig(workspace=tmp_path))
    result = asyncio.run(bridge.call_tool("read_workspace_image", {"path": "plot.png"}))
    assert base64.b64decode(result["data"]) == path.read_bytes()
    assert result["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert (result["width"], result["height"]) == (64, 32)
    types = pytest.importorskip("mcp.types")
    wire = _sdk_result(types, result, image=True)
    assert [block.type for block in wire.content] == ["text", "image"]
    encoded_wire = wire.model_dump(by_alias=True)
    assert encoded_wire["content"][1]["mimeType"] == "image/png"
    assert wire.content[1].data == result["data"]
    assert "data" not in encoded_wire["structuredContent"]
    assert result["data"] not in wire.content[0].text


def test_image_paths_and_limits(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    Image.new("RGB", (2, 2)).save(tmp_path / "outside.png")
    (workspace / "alias.png").symlink_to(tmp_path / "outside.png")
    for path in ("../outside.png", "alias.png", str(tmp_path / "outside.png")):
        with pytest.raises(ValueError, match="escapes"):
            read_workspace_image(workspace, path)
    (workspace / "huge.png").write_bytes(b"x" * (MAX_IMAGE_BYTES + 1))
    with pytest.raises(ValueError, match="4 MiB"):
        read_workspace_image(workspace, "huge.png")
    (workspace / "text.png").write_text("not an image")
    with pytest.raises(OSError):
        read_workspace_image(workspace, "text.png")
