"""Check a resident Conjecture 1 adapter against a saved numerical reload probe."""

import argparse
import json
import math
from pathlib import Path


def verify(probe, result):
    if result.get("adapter_active") is not True:
        raise ValueError("The response did not use an adapter")
    weights = result.get("model_identity", {}).get("adapter_files_sha256", {})
    if weights.get("adapter_model.safetensors") != probe["weights_sha256"]:
        raise ValueError("The served adapter weights differ from the release")
    if result.get("input_prompt_sha256") != probe["prompt_sha256"]:
        raise ValueError("The compiled input differs from the pinned reload probe")
    actual = result.get("prediction", {}).get("probabilities", {})
    expected = probe["expected_probabilities"]
    if set(actual) != set(expected):
        raise ValueError("Decision fields differ from the probe")
    errors = []
    for field, values in expected.items():
        if set(actual[field]) != set(values):
            raise ValueError("Decision options differ from the probe: " + field)
        for label, value in values.items():
            observed = actual[field][label]
            if (
                isinstance(observed, bool)
                or not isinstance(observed, (float, int))
                or not math.isfinite(observed)
            ):
                raise ValueError("Non-numeric or nonfinite option probability")
            errors.append(abs(observed - value))
    maximum = max(errors)
    if maximum > probe["maximum_probability_error"]:
        raise ValueError(f"Probability discrepancy {maximum} exceeds the saved tolerance")
    return dict(
        passed=True,
        fields=len(expected),
        option_probabilities=len(errors),
        maximum_probability_error=maximum,
        tolerance=probe["maximum_probability_error"],
        scope="Mechanical reload check only; scientific usefulness is a separate evaluation",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--auth-token-file", type=Path, required=True)
    parser.add_argument("--policy", default="conjecture1")
    parser.add_argument("--probe", type=Path, default=Path("examples/reload-probe.json"))
    args = parser.parse_args()
    from simjecture_monitor.attention_server import request

    probe = json.loads(args.probe.read_text())
    result = request(
        args.socket,
        dict(
            observation=probe["observation"],
            policy=args.policy,
            auth_token=args.auth_token_file.read_text().strip(),
        ),
        timeout=360,
    )
    if result.get("policy") != args.policy:
        raise ValueError("The server returned a different named policy")
    print(json.dumps(verify(probe, result), indent=2))


if __name__ == "__main__":
    main()
