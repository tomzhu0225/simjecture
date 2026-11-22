"""Check trusted reward attribution and observation boundaries without a solver."""

import json
import math

from research_decision.autonomous_reward import numerical_review
from research_decision.autonomous_tools import translate
from research_decision.evaluation import C_WEIGHTS, D_WEIGHTS, score


def main():
    task = {"initial_parameter_configuration": {"beta": 1, "angle_deg": 30, "deltaB_over_B0": .001}}
    experiment = dict(solver="MHD1D", parameters={"beta": 1, "angle_deg": 30, "amplitude": .001, "periods": .7, "cfl": .25},
                      scale=dict(mesh={"nx": [32, 64, 128]}, parallel_resources={"cpus": 1, "memory_mb": 512}))
    config, defaults = translate(experiment, task)
    assert not defaults and config["nx"] == [32, 64, 128]
    try:
        translate(dict(experiment, solver="unavailable solver"), task)
    except ValueError:
        pass
    else:
        raise AssertionError("Unsupported solver silently replaced")
    record = dict(events=[dict(kind="execution_submission", payload=dict(receipt={"id": "real"}, decision_id="chosen"))])
    def measurement(n, conservation=0):
        return dict(n=n, cfl=.25, angle_deg=30, beta=1, amplitude=.001, periods=.7,
                    measured_speed=math.cos(math.pi / 6) * (1 + 1 / n**2), max_conservation_residual=conservation,
                    min_density=.99, min_pressure=.4, max_sample_phase_increment=.1, phase_fit_max_residual=1e-6,
                    amplitude_ratio=.999, phase_sample_count=100, floor_corrections=0, source_corrections=0)
    outputs = {"real": {"measurements": [measurement(n) for n in [32, 64, 128]]}}
    review = numerical_review(record, outputs)
    assert review["spatial_convergence"] and review["terminal_validity"] == .7
    assert score(review["C_components"], C_WEIGHTS) == review["C"]
    assert score(review["D_components"], D_WEIGHTS) == review["D"]
    assert review["C_components"]["independent_replication_and_prediction"] == 0
    assert review["process_gains"][0]["causal_decision_ids"] == ["chosen"]
    # A duplicate parameter/grid measurement cannot farm another reward.
    duplicate = numerical_review(record, {"real": {"measurements": outputs["real"]["measurements"] * 2}})
    assert duplicate["process_gains"] == review["process_gains"]
    invalid = numerical_review(record, {"real": {"measurements": [measurement(64, conservation=.1)]}})
    assert invalid["terminal_validity"] == 0 and not invalid["process_gains"]
    # Even flawless diagnostic data without an actual decision/receipt link
    # cannot create a process gain attributable to an experiment choice.
    unbound = numerical_review({"events": []}, outputs)
    assert not unbound["process_gains"]
    print(json.dumps(dict(passed=7, model_calls=0, research_experiments=0, optimizer_updates=0)))


if __name__ == "__main__":
    main()
