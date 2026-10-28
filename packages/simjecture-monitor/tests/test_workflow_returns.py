"""Full episodes, not correlated polls, define the measured waiting comparison."""

import copy
import json

import pytest
from simjecture_monitor.events import put
from simjecture_monitor.sampling_trace import SamplingTrace, file_reference
from simjecture_monitor.workflow_returns import CHECKS, workflow_advantages, workflow_utility
from test_sampling_trace import model, observed, response, save


def export_episode(folder, plan, *, identity, role, context, decisions=0, starts=2, quality=1.0):
    measured = dict(
        verified_quality=quality,
        native_starts=starts,
        elapsed_seconds=200.0,
        required_feedback_misses=0,
        duplicate_wakeups=0,
        invalid_proposals=0,
    )
    episode = dict(
        source_kind="executed_parked_workflow",
        status="completed",
        id=identity,
        role=role,
        context=context,
        plan_sha256=plan["sha256"],
        lifecycle="parked_until_terminal_fallback_or_returned_attention/v1",
        checks=dict.fromkeys(CHECKS, True),
        measurements=measured,
        utility=workflow_utility(measured)["total"],
        automatic_alerts=0,
        requested_decisions=decisions,
        decision_ids=[],
        model_identity=None,
        temperature=None,
    )
    rows = []
    if decisions:
        trace = SamplingTrace(folder / identity / "monitor", seed=1)
        for i in range(decisions):
            packet = observed()
            result = response(trace, packet)
            save(trace, packet, result, index=i)
            row = json.loads(
                (trace.directory / trace.data["responses"][-1]["row"]["path"]).read_text()
            )
            original = trace.directory / row["decision_receipt"]["path"]
            dest = folder / (identity + f"-decision-{i}.json")
            dest.write_bytes(original.read_bytes())
            row["decision_receipt"] = file_reference(dest)
            rows.append(row)
            episode["decision_ids"].append(row["id"])
        trace.close()
        episode.update(
            model_identity=trace.data["model_identity"], temperature=trace.data["temperature"]
        )
    path = folder / (identity + "-episode.json")
    put(path, episode)
    return file_reference(path), rows


@pytest.fixture
def dataset(tmp_path):
    context = dict(
        configuration_sha256="a" * 64,
        worker_config_sha256="b" * 64,
        host_policy_sha256="c" * 64,
        criteria_sha256="d" * 64,
        environment_sha256="e" * 64,
        budget_seconds=650,
    )
    plan = dict(
        schema="parked-workflow-return-plan/v1",
        split="train",
        temperature=3.0,
        blocks=[
            dict(
                id="group",
                context=context,
                trials=[
                    dict(id=name, role=role)
                    for name, role in [
                        ("sample-a", "sampled"),
                        ("sample-b", "sampled"),
                        ("wait-a", "wait"),
                        ("wait-b", "wait"),
                    ]
                ],
            )
        ],
    )
    put(tmp_path / "PLAN.json", plan)
    planref = file_reference(tmp_path / "PLAN.json")
    manifest = dict(
        schema="parked-workflow-return-dataset/v1",
        plan=planref,
        episodes=[],
        model_identity=model().identity,
    )
    rows = []
    for name, role, count, starts in [
        ("sample-a", "sampled", 1, 3),
        ("sample-b", "sampled", 3, 4),
        ("wait-a", "wait", 0, 2),
        ("wait-b", "wait", 0, 2),
    ]:
        reference, part = export_episode(
            tmp_path,
            planref,
            identity=name,
            role=role,
            context=context,
            decisions=count,
            starts=starts,
        )
        manifest["episodes"].append(reference)
        rows += part
    put(tmp_path / "episodes.json", manifest)
    ref = file_reference(tmp_path / "episodes.json")
    for row in rows:
        row["episode_manifest"] = ref
    return rows


def rewrite_episode(tmp_path, rows, identity, transform):
    path = tmp_path / (identity + "-episode.json")
    data = json.loads(path.read_text())
    transform(data)
    put(path, data)
    manifest_path = tmp_path / "episodes.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["episodes"] = [
        file_reference(path) if r["path"] == path.name else r for r in manifest["episodes"]
    ]
    put(manifest_path, manifest)
    for row in rows:
        row["episode_manifest"] = file_reference(manifest_path)


def test_all_polls_receive_the_episode_advantage_without_becoming_extra_episodes(dataset, tmp_path):
    values, audit = workflow_advantages(dataset, tmp_path)
    assert values[dataset[0]["id"]] == pytest.approx(-0.02)
    assert all(values[row["id"]] == pytest.approx(-0.04) for row in dataset[1:])
    assert len(audit["group"]["sampled_episodes"]) == 2
    assert [r["decisions"] for r in audit["group"]["sampled_episodes"]] == [1, 3]


def test_known_failed_workflow_is_retained_as_negative_return(dataset, tmp_path):
    def failure(e):
        e["measurements"]["verified_quality"] = 0.0
        e["utility"] = workflow_utility(e["measurements"])["total"]

    rewrite_episode(tmp_path, dataset, "sample-a", failure)
    values, _ = workflow_advantages(dataset, tmp_path)
    assert values[dataset[0]["id"]] == pytest.approx(-1.02)


def test_cannot_drop_a_poll_or_control_after_seeing_returns(dataset, tmp_path):
    with pytest.raises(ValueError, match="every sampled decision"):
        workflow_advantages(dataset[:-1], tmp_path)
    manifest = json.loads((tmp_path / "episodes.json").read_text())
    manifest["episodes"].pop()
    put(tmp_path / "episodes.json", manifest)
    for row in dataset:
        row["episode_manifest"] = file_reference(tmp_path / "episodes.json")
    with pytest.raises(ValueError, match="cohort is incomplete"):
        workflow_advantages(dataset, tmp_path)


@pytest.mark.parametrize(
    "change,match",
    [
        ("awake", "parked-worker lifecycle"),
        ("transport", "unconfirmed"),
        ("context", "prospective assignment"),
        ("utility", "measured components"),
        ("missing_response", "Missing or duplicate"),
    ],
)
def test_ineligible_episode_cannot_supply_reward(dataset, tmp_path, change, match):
    def mutate(e):
        if change == "awake":
            e["lifecycle"] = "immediate_worker_replay"
        elif change == "transport":
            e["checks"]["solver_outcomes_confirmed"] = False
        elif change == "context":
            e["context"]["host_policy_sha256"] = "f" * 64
        elif change == "utility":
            e["utility"] += 5
        else:
            e["requested_decisions"] += 1

    rewrite_episode(tmp_path, dataset, "sample-a", mutate)
    with pytest.raises(ValueError, match=match):
        workflow_advantages(dataset, tmp_path)


def test_hidden_future_input_or_commissioning_cannot_enter_optimizer(dataset, tmp_path):
    changed = copy.deepcopy(dataset)
    changed[0]["state"] += " The hidden answer is intervene."
    with pytest.raises(ValueError, match="actual parked-state"):
        workflow_advantages(changed, tmp_path)
    changed = copy.deepcopy(dataset)
    changed[0]["split"] = "commissioning"
    with pytest.raises(ValueError, match="complete training"):
        workflow_advantages(changed, tmp_path)


def test_zero_opportunity_episode_is_reported_without_fabricating_a_policy_sample(
    dataset, tmp_path
):
    kept = [r for r in dataset if r["episode_id"] != "sample-a"]

    def no_opportunity(e):
        e.update(decision_ids=[], requested_decisions=0, model_identity=None, temperature=None)

    rewrite_episode(tmp_path, kept, "sample-a", no_opportunity)
    values, audit = workflow_advantages(kept, tmp_path)
    assert len(values) == 3 and audit["group"]["sampled_episodes"][0]["decisions"] == 0


def test_suppressed_invalid_choices_are_not_assigned_a_fabricated_cost():
    measured = dict(
        verified_quality=1.0,
        native_starts=2,
        elapsed_seconds=200.0,
        required_feedback_misses=0,
        duplicate_wakeups=0,
        invalid_proposals=0,
    )
    before = workflow_utility(measured)
    after = workflow_utility(measured | dict(invalid_proposals=5))
    assert before == after
