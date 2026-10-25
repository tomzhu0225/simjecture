import importlib.util
import json
from pathlib import Path

from simjecture_monitor.events import digest, put


def test_replay_never_substitutes_after_resume_or_takes_treatment_arm(tmp_path):
    path = Path(__file__).parents[1] / "scripts/replay_generalization.py"
    spec = importlib.util.spec_from_file_location("replay_generalization", path)
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)
    jobs = [dict(root="observe", arm="observe"), dict(root="model", arm="model")]
    put(tmp_path / "DESIGN.json", dict(blocks=[dict(jobs=jobs)]))
    trial = tmp_path / "observe"
    (trial / "monitor").mkdir(parents=True)
    put(trial / "OUTCOME.json", dict(parking=[dict(started_at=100, ended_at=140)]))
    packets = []
    for observed in [109, 111, 126, 140, 145]:
        state = dict(host_state=dict(worker_parked=True), events=[dict(observed_at=observed)])
        packets.append(dict(state=state, packet_sha256=digest(state)))
    (trial / "monitor/observations.jsonl").write_text(
        "\n".join(json.dumps(p) for p in packets) + "\n"
    )
    selected = replay.select(tmp_path)
    assert len(selected) == 3
    assert [r.get("selected_at") for r in selected] == [111, 126, None]
    assert selected[2]["missing"] == "No observation in specified interval"
    assert selected[0]["packet"] == packets[1]
    assert selected[1]["packet"] == packets[2]
