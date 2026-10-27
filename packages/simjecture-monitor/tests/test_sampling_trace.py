"""Sampling records preserve actual parked observations and cannot invent coverage."""

import copy
import json

import pytest
from simjecture_monitor.attention_server import AttentionService
from simjecture_monitor.events import put
from simjecture_monitor.sampling_trace import SamplingTrace
from test_attention_server import Provider
from test_workflow_attention import packet, raw


def observed():
    return packet(raw())


def model():
    value = Provider(
        dict(
            route="observe",
            question_ref="none",
            basis="unspecified",
            evidence_primary="none",
            evidence_secondary="none",
        )
    )
    value.temperature = 3.0
    return value


def response(trace, observation):
    request = trace.request(observation, policy="adapted")
    return AttentionService(model(), adapter_loaded=True, maximum_tokens=100000).predict(
        dict(observation=observation.model_dump(), policy="adapted", **request)
    )


def save(trace, observation, result, index=0):
    path = trace.directory / f"attention-{index:05d}.json"
    put(
        path,
        dict(
            submitted=observation.model_dump(), result=result, admission=dict(disposition="observe")
        ),
    )
    trace.record(observation, result, decision_path=path)


def test_actual_sampled_rows_and_unanswered_requests_remain_distinguishable(tmp_path):
    trace = SamplingTrace(tmp_path / "episode/monitor", seed=21)
    observation = observed()
    first = response(trace, observation)
    save(trace, observation, first)
    second = trace.request(observation, policy="adapted")
    assert first["behavior"]["seed"] != second["seed"]
    trace.close()
    data = json.loads(trace.path.read_text())
    assert data["closed"] and len(data["requests"]) == 2 and len(data["responses"]) == 1
    row = json.loads((trace.directory / data["responses"][0]["row"]["path"]).read_text())
    assert row["observation"]["worker_state"] == "parked"
    assert row["behavior"]["temperature"] == 3.0
    assert row["behavior"]["probabilities"] == first["prediction"]["probabilities"]
    assert row["targets"] == {
        key: dict(label=value) for key, value in first["behavior"]["sampled_answers"].items()
    }
    with pytest.raises(ValueError, match="closed"):
        save(trace, observation, first, 1)


def test_active_worker_is_not_a_training_opportunity(tmp_path):
    trace = SamplingTrace(tmp_path / "episode/monitor", seed=21)
    with pytest.raises(ValueError, match="parked-worker"):
        trace.request(observed().model_copy(update=dict(worker_state="active")), policy="adapted")
    assert trace.data["requests"] == []


@pytest.mark.parametrize(
    "change,match",
    [
        ("seed", "assigned sampling"),
        ("policy", "Response policy"),
        ("prompt", "scored model input"),
        ("answers", "categorical draw"),
        ("temperature", "invalid behavior temperature"),
        ("missing", "Missing sampled behavior"),
    ],
)
def test_unbound_responses_cannot_become_training_data(tmp_path, change, match):
    trace = SamplingTrace(tmp_path / "episode/monitor", seed=21)
    observation = observed()
    result = response(trace, observation)
    if change == "seed":
        result["behavior"]["seed"] += 1
    elif change == "policy":
        result["policy"] = "another"
    elif change == "prompt":
        result["behavior"]["prompt_sha256"] = "0" * 64
    elif change == "answers":
        result["behavior"]["sampled_answers"]["route"] = "director"
    elif change == "temperature":
        result["behavior"]["temperature"] = -1.0
    else:
        del result["behavior"]
    with pytest.raises(ValueError, match=match):
        save(trace, observation, result)
    assert trace.data["responses"] == []


def test_model_cannot_change_mid_episode_and_commissioning_is_not_train(tmp_path):
    trace = SamplingTrace(tmp_path / "episode/monitor", seed=21, split="commissioning")
    observation = observed()
    first = response(trace, observation)
    save(trace, observation, first)
    row = json.loads((trace.directory / trace.data["responses"][0]["row"]["path"]).read_text())
    assert row["split"] == "commissioning"
    second = copy.deepcopy(response(trace, observation))
    second["model_identity"]["adapter_sha256"] = "changed"
    second["behavior"]["model_identity"]["adapter_sha256"] = "changed"
    with pytest.raises(ValueError, match="changed within an episode"):
        save(trace, observation, second, 1)
