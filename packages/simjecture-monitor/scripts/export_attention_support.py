"""Export separate v0.2 schemas and scripted examples; never modify v0.1."""

import argparse
import json
from pathlib import Path

from simjecture_monitor import attention_support as protocol
from simjecture_monitor.synthetic_attention import make_observation, scripted_preference


def exports():
    result = {f"schemas/{name}.schema.json": schema for name, schema in protocol.schemas().items()}
    for name in ("lookup_needed", "lookup_active", "lookup_recent_no_match"):
        packet = make_observation(20261025, name)
        view = protocol.pack(
            packet, len, token_counter_id="assembly:characters", budget_tokens=1_000_000
        )
        choice = scripted_preference(packet, view)
        result[f"examples/{name}/observation.json"] = packet.model_dump()
        result[f"examples/{name}/model-input.txt"] = view.text
        result[f"examples/{name}/choice.json"] = choice.model_dump()
        result[f"examples/{name}/decision.json"] = protocol.bind_choice(
            packet, view, choice, policy_id="scripted-example-not-model-prediction"
        ).model_dump()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = exports()
    for name, value in result.items():
        path = args.output / name
        if args.check:
            stored = path.read_text() if isinstance(value, str) else json.loads(path.read_text())
            if stored != value:
                raise ValueError("Contract export differs: " + name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value if isinstance(value, str) else json.dumps(value, indent=2) + "\n")
    print(f"{len(result)} exports {'verified' if args.check else 'written'}")


if __name__ == "__main__":
    main()
