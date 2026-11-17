"""Build validation schemas for the five requested research data categories."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def obj(properties, required=None):
    return dict(
        type="object",
        properties=properties,
        required=list(properties) if required is None else required,
        additionalProperties=False,
    )


def array(items):
    return dict(type="array", items=items)


def main():
    string = dict(type="string", minLength=1)
    number = dict(type="number")
    nonnegative = dict(type="number", minimum=0)
    evidence = obj(
        dict(
            evidence_id=string,
            receipt_ids=array(string),
            measured_values=dict(type="object"),
            uncertainty=dict(type="object"),
            scope=string,
            observed_at=number,
        )
    )
    receipt = obj(
        dict(
            receipt_id=string,
            task_id=string,
            study_id=string,
            decision_id=string,
            input_sha256=string,
            output_sha256=string,
            solver=string,
            solver_version=string,
            source_sha256=string,
            seed=dict(type="integer"),
            started_at=number,
            finished_at=number,
            status=dict(enum=["succeeded", "failed", "cancelled", "timed_out", "partial"]),
            cost=obj(
                dict(
                    wall_seconds=nonnegative,
                    cpu_core_seconds=nonnegative,
                    gpu_seconds=nonnegative,
                    npu_seconds=nonnegative,
                    peak_memory_bytes=nonnegative,
                )
            ),
            diagnostics=dict(type="object"),
            artifact_hashes=dict(type="object"),
        )
    )
    model = obj(dict(name=string, equations=string, assumptions=array(string), validity_scope=string))
    state = obj(
        dict(
            schema_version=dict(const="research-decision/1"),
            task_contract=dict(type="object"),
            hypotheses=array(string),
            physical_models=array(model),
            available_resources=dict(type="object"),
            completed_receipts=array(receipt),
            verified_evidence=array(evidence),
            necessary_history=array(
                obj(dict(decision_id=string, executed_plan=dict(type="object"), evidence_ids=array(string)))
            ),
            remaining_wall_seconds=nonnegative,
            observed_at=number,
        )
    )
    scale = obj(
        dict(
            spatial_dimensions=dict(type="integer", minimum=0, maximum=3),
            mesh=dict(type="object"),
            particles=dict(type="object"),
            time_integration=dict(type="object"),
            parallel_resources=dict(type="object"),
            estimated_wall_seconds=nonnegative,
            expected_numerical_error=string,
            refinement_condition=string,
        )
    )
    experiment = obj(
        dict(
            experiment_id=string,
            scientific_question=string,
            competing_hypotheses=array(string),
            solver=string,
            physical_model=string,
            parameters=dict(type="object"),
            initial_boundary_conditions=dict(type="object"),
            scale=scale,
            diagnostics=array(string),
            success_or_falsification_criteria=array(string),
            dependencies=array(string),
            evidence_ids=array(string),
        )
    )
    advice = obj(
        dict(
            action=dict(enum=["propose_experiments", "reorganize", "request_evidence", "closeout"]),
            experiments=array(experiment),
            organization=string,
            parameter_justification=string,
            model_hierarchy=string,
            budget_allocation=dict(type="object"),
            public_justification=string,
            change_of_mind_conditions=array(string),
            requested_evidence_ids=array(string),
        )
    )
    conclusion = obj(
        dict(
            supported=array(string),
            falsified=array(string),
            unresolved=array(string),
            scope=string,
            evidence_ids=array(string),
            termination_reason=string,
            include_in_C=dict(const=True),
            include_in_D=dict(const=True),
        )
    )
    sft = obj(
        dict(
            collection_id=string,
            task_id=string,
            split=dict(const="train"),
            teacher=dict(const="gpt-6.1-sol"),
            observation=state,
            teacher_public_decision=advice,
            receipt_ids=array(string),
            trajectory_id=string,
            decision_index=dict(type="integer", minimum=0),
            quality_review_receipt=string,
        )
    )
    audit = obj(
        dict(
            study_id=string,
            decision_id=string,
            observation_sha256=string,
            original_advice=dict(anyOf=[advice, dict(type="null")]),
            executed_plan=dict(type="object"),
            component_sources=obj(
                {
                    key: dict(enum=["student", "modified", "host", "unused"])
                    for key in [
                        "experiment_selection",
                        "organization",
                        "parameters",
                        "model_hierarchy",
                        "scale",
                    ]
                }
            ),
            override_reasons=dict(type="object"),
            host_model=dict(const="gpt-6.1-sol"),
            student_positive_credit_eligible=dict(type="boolean"),
            retained_student_components=array(string),
            scale_default=string,
        )
    )
    reward = obj(
        dict(
            decision_id=string,
            verified_evidence_ids=array(string),
            process_reward=number,
            terminal_reward=number,
            student_credit=number,
            credit_basis=string,
        )
    )
    trajectory = obj(
        dict(
            trajectory_id=string,
            task_id=string,
            split=dict(const="train"),
            policy_sha256=string,
            initial_state_sha256=string,
            observations=array(state),
            audits=array(audit),
            receipts=array(receipt),
            rewards=array(reward),
            closeout=conclusion,
        )
    )
    score = obj(
        dict(
            task_id=string,
            study_id=string,
            blind_arm_id=string,
            termination_reason=string,
            closeout=conclusion,
            C=dict(type="object"),
            D=dict(type="object"),
            replication_receipt_ids=array(string),
            prediction_receipt_ids=array(string),
            novelty_auxiliary=dict(type="object"),
            reviewer_session_id=string,
            source_evidence_ids=array(string),
        )
    )
    schemas = {
        "research_state": state,
        "advice": advice,
        "execution_receipt": receipt,
        "decision_audit": audit,
        "sft_sample": sft,
        "rl_trajectory": trajectory,
        "phase_conclusion": conclusion,
        "score": score,
        "evidence": evidence,
    }
    for name, schema in schemas.items():
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": name, **schema}
        destination = ROOT / "schemas" / f"{name}.schema.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(schemas)} schemas")


if __name__ == "__main__":
    main()
