"""CLI discovery and checks for optional scientific attention tooling."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

DOCUMENTATION = "https://drawingsword.com/simjecture/how-to/scientific-attention.html"


def catalogue_card():
    try:
        installed = importlib.util.find_spec("simjecture_monitor.tool") is not None
    except ModuleNotFoundError:
        installed = False
    return dict(
        id="conjecture-1",
        name="Conjecture 1",
        kind="attention",
        category="Workflow assistance",
        action="attention",
        installed=installed,
        state="installed" if installed else "available",
        readiness="unchecked",
        documentation_url=DOCUMENTATION,
        description="Optional scientific attention coprocessor. Record suggested wakeups in shadow "
        "mode or explicitly enable bounded director requests for a study. Connect a separately "
        "managed model service; ordinary studies do not load or run the model. Experimental: "
        "a repeatable workflow advantage has not been established.",
    )


def configure(parser):
    parser.add_argument("operation", choices=["status", "example-config", "check", "score"])
    parser.add_argument("--config", type=Path)
    parser.add_argument("--observation", type=Path)
    parser.add_argument("--output", type=Path)
    parser.set_defaults(handler=run)


def run(args):
    if args.operation == "status":
        print(json.dumps(catalogue_card(), indent=2))
        return 0
    try:
        from simjecture_monitor.tool import AttentionClient, AttentionConfig
    except ImportError as error:
        raise ValueError(
            "Install the optional client: uv pip install -e packages/simjecture-monitor"
        ) from error
    if args.operation == "example-config":
        value = AttentionConfig(
            socket="/absolute/path/attention.sock", auth_token_file="/absolute/path/attention.token"
        ).model_dump()
    else:
        if args.config is None:
            raise ValueError("Specify --config for the separately managed attention service")
        config = AttentionConfig.read(args.config)
        client = AttentionClient(config)
        if args.operation == "check":
            liveness = config.verify_liveness()
            value = client.health() | {"admission_liveness": liveness}
        else:
            if args.observation is None:
                raise ValueError("Specify --observation with a scientific-attention packet")
            value = client.score(json.loads(args.observation.read_text()))
    body = json.dumps(value, indent=2) + "\n"
    if args.output:
        with args.output.open("x") as stream:
            stream.write(body)
    else:
        print(body, end="")
    return 0
