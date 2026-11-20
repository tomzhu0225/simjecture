"""Preregistered numerical pilot rewards; no GPT judgment or hidden test data.

These checks concern a smooth 1D ideal-MHD training problem only. They do not
certify discoveries, independent replication or the final C/D outcome.
"""

import math
from collections import defaultdict

from .collect import bound_actions
from .contracts import fingerprint
from .rloo import scientific_return

RULES = {
    "version": "mhd-numerical-pilot-v1",
    "integrity": "finite data, positive rho/p, conservation residual <=1e-9, phase increments <pi/2, >=20 samples, >=0.25 periods",
    "linear_check": "amplitude <=0.001; measured speed vs cos(angle) in rho0=B0=mu0=1 units; relative tolerance0.005",
    "spatial_check": "three distinct grids at identical physical parameters/CFL/periods; decreasing phase-speed errors with empirical order between1.5 and2.6",
    "temporal_check": "three distinct CFLs at fixed grid/physical parameters; self differences decrease; this is a consistency check, not independent replication",
    "terminal_features": "0.35 accurate resolved linear propagation +0.35 spatial convergence +0.15 temporal consistency +0.15 controlled second physical condition",
    "process": "deduplicate physical/grid/CFL configurations; each trusted observation0.12, accurate linear run0.20; cap sum at1; actual causal advice IDs only",
    "claims": "only executed measurements/convergence in the tested scope; no discovery or independent-replication credit",
    "student_observation": "never includes these points, target speeds, rewards or reference comparisons",
}


def numerical_review(record, outputs):
    decision_for_receipt = {
        e["payload"]["receipt"]["id"]: e["payload"]["decision_id"]
        for e in record["events"] if e["kind"] == "execution_submission"
    }
    measurements, gains, seen = [], [], set()
    for identifier, document in outputs.items():
        amount = 0.0
        for values in document.get("measurements", []):
            signature = fingerprint({k: values[k] for k in (
                "n", "cfl", "angle_deg", "beta", "amplitude", "periods"
            )})
            if signature in seen:
                continue
            seen.add(signature)
            finite = all(isinstance(values.get(k), (int, float)) and math.isfinite(values[k]) for k in (
                "measured_speed", "max_conservation_residual", "min_density", "min_pressure",
                "max_sample_phase_increment", "phase_fit_max_residual", "amplitude_ratio"
            ))
            trusted = finite and (
                values["min_density"] > 0 and values["min_pressure"] > 0
                and values["max_conservation_residual"] <= 1e-9
                and values["max_sample_phase_increment"] < math.pi / 2
                and values["phase_sample_count"] >= 20 and values["periods"] >= .25
                and values["floor_corrections"] == values["source_corrections"] == 0
            )
            if not trusted:
                continue
            expected = math.cos(math.radians(values["angle_deg"]))
            error = abs(values["measured_speed"] / expected - 1)
            accurate = values["amplitude"] <= .001 and error <= .005
            measurements.append(dict(values, receipt_id=identifier, linear_error=error, accurate=accurate))
            amount += .20 if accurate else .12
        if amount and identifier in decision_for_receipt:
            gains.append(dict(evidence_id="execution:" + identifier, verified=True,
                              value=min(1.0, amount), causal_decision_ids=[decision_for_receipt[identifier]]))
    spatial_groups, temporal_groups = defaultdict(list), defaultdict(list)
    for values in measurements:
        if values["amplitude"] <= .001:
            common = tuple(values[k] for k in ("angle_deg", "beta", "amplitude", "periods"))
            spatial_groups[common + (values["cfl"],)].append(values)
            temporal_groups[common + (values["n"],)].append(values)
    spatial = []
    for group in spatial_groups.values():
        ordered = sorted({v["n"]: v for v in group}.values(), key=lambda v: v["n"])
        for a, b, c in zip(ordered, ordered[1:], ordered[2:]):
            if a["linear_error"] > b["linear_error"] > c["linear_error"] > 1e-12:
                orders = [math.log(x["linear_error"] / y["linear_error"]) / math.log(y["n"] / x["n"])
                          for x, y in [(a, b), (b, c)]]
                if all(1.5 <= p <= 2.6 for p in orders):
                    spatial.append(dict(receipt_ids=sorted({v["receipt_id"] for v in [a, b, c]}), orders=orders))
    temporal = []
    for group in temporal_groups.values():
        ordered = sorted({v["cfl"]: v for v in group}.values(), key=lambda v: -v["cfl"])
        for a, b, c in zip(ordered, ordered[1:], ordered[2:]):
            large = abs(a["measured_speed"] - b["measured_speed"])
            small = abs(b["measured_speed"] - c["measured_speed"])
            if large > small > 1e-12:
                temporal.append(dict(receipt_ids=sorted({v["receipt_id"] for v in [a, b, c]}),
                                     speed_differences=[large, small]))
    accurate = [v for v in measurements if v["accurate"]]
    conditions = {(v["angle_deg"], v["beta"]) for v in accurate}
    validity = .35 * bool(accurate) + .35 * bool(spatial) + .15 * bool(temporal) + .15 * (len(conditions) >= 2)
    # Provisional diagnostics preserve the prescribed maxima. No independent
    # verification has occurred, so the entire 35-point C component stays zero.
    C_components = dict(truth_or_valid_evidence=40 * validity, independent_replication_and_prediction=0,
                        numerical_validity_scope_uncertainty=25 * bool(measurements) * (.4 + .4 * bool(spatial) + .2 * bool(temporal)))
    D_components = dict(experiment_choice_discrimination=30 * (.5 * bool(spatial) + .25 * bool(temporal) + .25 * (len(conditions) >= 2)),
                        parameters_resolution_scale=25 * bool(accurate), evidence_adaptation=0,
                        series_and_budget=20 * bool(measurements))
    return dict(
        evaluator="deterministic_numerical_verifier_v1", rules_sha256=fingerprint(RULES),
        provisional_only=True, terminal_validity=validity, process_gains=gains, unsupported_claims=0,
        measurements=measurements, spatial_convergence=spatial, temporal_consistency=temporal,
        C_components=C_components, D_components=D_components,
        C=sum(C_components.values()), D=sum(D_components.values()),
        independent_replication=False, scientific_discovery_claimed=False,
    )


def export_trajectory(record, task, review):
    if task["split"] != "train":
        raise ValueError("Only training tasks can enter autonomous RLOO")
    actions = []
    for event, audits, receipts in bound_actions(record):
        action = dict(event["payload"]["raw_reply"])
        action.update(
            student_executed_components=sorted({c for audit in audits for c in audit["retained_student_components"]}),
            decision_ids=[audit["decision_id"] for audit in audits], receipt_ids=receipts,
        )
        actions.append(action)
    audits = [e["payload"] for e in record["events"] if e["kind"] == "decision_audit"]
    metadata = scientific_return(process_gains=review["process_gains"],
                                 terminal_validity=review["terminal_validity"],
                                 unsupported_claims=0, audits=audits)
    return dict(
        task_id=task["task_id"], split="train", trajectory_id=record["study_id"],
        initial_state_sha256=record["initial_state_sha256"],
        old_policy_sha256=record["pinned_policy_sha256"], budget_seconds=task["total_wall_seconds"],
        actions=actions, closeout=record["closeout"], receipts=record["receipts"], audits=audits,
        return_metadata=metadata, **{"return": metadata["value"]},
        reward_provenance=dict(evaluator=review["evaluator"], rules_sha256=review["rules_sha256"],
                               GPT_review_used=False, final_C_D_review_pending=True),
    )
