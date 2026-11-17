"""Select complete, provenance-preserving decisions that fit the qualified context."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from transformers import AutoTokenizer

    from .storage import write_json
    from .train_adapter import model_inputs

    tokenizer = AutoTokenizer.from_pretrained(args.base, local_files_only=True)
    cfg = json.loads(args.config.read_bytes())
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(
        json.loads((args.config.parent.parent / "schemas/advice.schema.json").read_bytes())
    )
    eligible = []
    lengths = []
    for line in args.data.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        prompt, target = model_inputs(tokenizer, row)
        schema_errors = list(validator.iter_errors(row["teacher_public_decision"]))
        experiments = row["teacher_public_decision"].get("experiments", [])
        administrative = bool(experiments) and all(
            "no physical evolution" in str(e.get("physical_model", "")).lower()
            or "no numerical calculation"
            in str(e.get("scale", {}).get("expected_numerical_error", "")).lower()
            for e in experiments
        )
        fits = (
            len(prompt) <= cfg["input_tokens_initial"]
            and len(target) <= cfg["output_tokens_initial"]
            and not schema_errors
            and not administrative
        )
        lengths.append(
            dict(
                collection_id=row["collection_id"],
                decision_index=row["decision_index"],
                input_tokens=len(prompt),
                target_tokens=len(target),
                eligible=fits,
                schema_error=schema_errors[0].message if schema_errors else None,
                administrative_only=administrative,
            )
        )
        if fits:
            eligible.append(row)
    if not eligible:
        raise ValueError("No complete reviewed decision fits; no silent truncation is permitted")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in eligible), encoding="utf-8"
    )
    report = dict(
        original_decisions=len(lengths),
        eligible_decisions=len(eligible),
        eligible_trajectories=len({r["collection_id"] for r in eligible}),
        lengths=lengths,
        truncation=False,
        excluded_scientific_studies_from_C_D=0,
        original_dataset_retained=True,
    )
    write_json(args.output.with_suffix(".preflight.json"), report)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
