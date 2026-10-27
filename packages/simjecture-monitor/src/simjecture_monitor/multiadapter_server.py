"""Private named-adapter serving for frozen, equal-hardware workflow comparisons."""

from __future__ import annotations

import argparse
import copy
import hashlib
import math
import re
import time
from pathlib import Path

from .attention_server import AttentionService, serve


class MultiAdapterService(AttentionService):
    """serve() serializes selection, inference, and identity binding."""

    def __init__(self, model, adapters, identities, *, maximum_tokens=8192):
        super().__init__(model, adapter_loaded=True, maximum_tokens=maximum_tokens)
        if not adapters or set(adapters) != set(identities) or "base" in adapters:
            raise ValueError("Named adapter policies and identities must agree")
        self.adapters = dict(adapters)
        self.identities = copy.deepcopy(identities)

    def predict(self, request):
        policy = request.get("policy")
        if policy == "base":
            return super().predict(request)
        if policy not in self.adapters:
            raise ValueError("Unknown named adapter policy")
        previous = self.model.model.active_adapter
        identity = self.model.identity
        try:
            self.model.model.set_adapter(self.adapters[policy])
            self.model.identity = self.identities[policy]
            mapped = request | dict(
                policy="adapted",
                policy_id=request.get("policy_id", "scientific-attention-" + policy),
            )
            result = super().predict(mapped)
            result["policy"] = policy
            return result
        finally:
            self.model.model.set_adapter(previous)
            self.model.identity = identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--adapter", action="append", required=True, help="policy=adapter_path")
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--auth-token-file", type=Path, required=True)
    parser.add_argument("--maximum-tokens", type=int, default=8192)
    parser.add_argument("--wall-seconds", type=int, required=True)
    parser.add_argument("--idle-seconds", type=int, default=1800)
    parser.add_argument("--temperature", type=float, default=1.0)
    args = parser.parse_args()
    if not math.isfinite(args.temperature) or args.temperature <= 0:
        parser.error("--temperature must be finite and positive")
    if args.socket.exists():
        raise ValueError("Refuse to replace an existing server socket")
    token = args.auth_token_file.read_text().strip()
    if len(token) < 32:
        raise ValueError("Require a private forwarding credential")
    paths = {}
    for specification in args.adapter:
        name, separator, path = specification.partition("=")
        if not separator or not re.fullmatch(r"[a-z][a-z0-9_]{0,40}", name):
            raise ValueError("Use a named policy and explicit adapter path")
        if name == "base" or name in paths:
            raise ValueError("Duplicate or reserved policy name")
        paths[name] = Path(path)
    from .decision_model import DecisionModel

    first = next(iter(paths))
    model = DecisionModel(
        args.checkpoint,
        adapter=str(paths[first]),
        max_tokens=args.maximum_tokens,
        kernel_profile="fla-prefill",
    )
    model.temperature = args.temperature
    adapters, identities = {}, {}
    for name, path in paths.items():
        adapter_name = "default" if name == first else name
        if name != first:
            model.model.load_adapter(path, adapter_name=adapter_name, is_trainable=False)
        adapters[name] = adapter_name
        identity = copy.deepcopy(model.identity)
        identity["adapter_files_sha256"] = {}
        for filename in ["adapter_config.json", "adapter_model.safetensors"]:
            with (path / filename).open("rb") as stream:
                identity["adapter_files_sha256"][filename] = hashlib.file_digest(
                    stream, "sha256"
                ).hexdigest()
        identities[name] = identity
    model.model.eval()
    service = MultiAdapterService(model, adapters, identities, maximum_tokens=args.maximum_tokens)
    status = dict(
        stage="ready",
        started_at=time.time(),
        model_identities=identities,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        policies=["base", *paths],
        temperature=args.temperature,
        requests=0,
    )
    serve(
        service,
        socket_path=args.socket,
        status_path=args.status,
        auth_token=token,
        wall_seconds=args.wall_seconds,
        idle_seconds=args.idle_seconds,
        status=status,
    )


if __name__ == "__main__":
    main()
