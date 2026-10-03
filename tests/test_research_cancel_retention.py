"""Exercise real cancellation across the executor and declared-output staging."""

import json
import tempfile
import time
import uuid
from pathlib import Path

import pytest

from conjecture_solver.execution import probe_execution_backend
from conjecture_solver.research_service import ResearchService


def test_cancel_retains_native_partial_artifacts(tmp_path):
    if not probe_execution_backend("bubblewrap")["available"]:
        pytest.skip("Requires real Bubblewrap namespaces")
    token = uuid.uuid4().hex
    service = ResearchService.create(
        tmp_path / "study", "Cancellation retains evidence.", wall_seconds=60
    )
    (service.work / "slow.py").write_text(
        "from pathlib import Path\nimport json,time\n"
        f"Path('partial.json').write_text(json.dumps({{'token': {token!r}}}))\n"
        "time.sleep(45)\nPath('final.json').write_text('{}')\n"
    )
    receipt = service.run("slow.py", outputs=["partial.json", "final.json"], timeout=50)
    deadline = time.time() + 10
    ready = False
    while time.time() < deadline:
        for p in Path(tempfile.gettempdir()).glob("simjecture-declared-work-*/work/partial.json"):
            try:
                ready = json.loads(p.read_text()).get("token") == token
            except (OSError, ValueError):
                continue
            if ready:
                break
        if ready:
            break
        time.sleep(0.05)
    assert ready, "Real numerical child did not create its partial output"
    service.cancel_active()
    while time.time() < deadline:
        record = service._read("experiments", receipt["id"])
        if record.get("artifacts", {}).get("partial.json"):
            break
        time.sleep(0.05)
    assert record["status"] == "cancelled"
    assert record["execution"]["cancelled"] is True
    output = service.root / "experiments" / receipt["id"] / "workspace"
    assert json.loads((output / "partial.json").read_text())["token"] == token
    assert not (output / "final.json").exists()
