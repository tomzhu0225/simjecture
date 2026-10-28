"""Private resident scoring for the scientific attention contract.

This service proposes attention only. The caller must admit against fresh host
state and record actual dispatch separately. No tools or repairs execute here.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import secrets
import socket
import time
from pathlib import Path

from . import attention_support as protocol
from .action_distribution import (
    CONTRACT,
    DISTRIBUTIONS,
    INDEPENDENT,
    choose,
    decoding_receipt,
    validate_support,
)
from .decision_interface import choice_from_answers, encode_request, scientific_request
from .events import put


def sampled_answers(probabilities, seed):
    return choose(probabilities, seed=seed)


class AttentionService:
    def __init__(
        self, model, *, adapter_loaded, maximum_tokens=4096, decision_distribution=INDEPENDENT
    ):
        self.model = model
        self.adapter_loaded = adapter_loaded
        self.maximum_tokens = maximum_tokens
        if decision_distribution not in DISTRIBUTIONS:
            raise ValueError("Unknown action distribution")
        self.decision_distribution = decision_distribution

    def predict(self, request):
        if request.get("distribution", self.decision_distribution) != self.decision_distribution:
            raise ValueError("Requested action distribution is not the served distribution")
        packet = protocol.Observation.model_validate(request["observation"])
        policy = request.get("policy", "adapted" if self.adapter_loaded else "base")
        if policy not in {"base", "adapted"} or policy == "adapted" and not self.adapter_loaded:
            raise ValueError("Requested weights are not available")
        policy_id = request.get("policy_id", "scientific-attention-" + policy)
        view = protocol.pack(
            packet, len, token_counter_id="assembly:characters", budget_tokens=1000000
        )
        row = scientific_request(packet, view)
        encoded = encode_request(row, self.model.tokenizer, maximum_tokens=1000000)
        view = view.model_copy(
            update=dict(
                input_tokens=len(encoded["input_ids"]),
                budget_tokens=self.maximum_tokens,
                token_counter_id="intern-decision:full-masked-chat:v0.2",
                status="ready"
                if len(encoded["input_ids"]) <= self.maximum_tokens
                else "insufficient_budget",
            )
        )
        result = dict(
            packet_id=packet.packet_id,
            policy=policy,
            view=view.model_dump(),
            input_prompt_sha256=encoded["prompt_sha256"],
            model_identity=self.model.identity,
            adapter_active=policy == "adapted",
        )
        if view.status != "ready":
            result["decision"] = protocol.Decision(
                schema_version=protocol.VERSION,
                packet_id=packet.packet_id,
                model_view_sha256=view.sha256,
                policy_id=policy_id,
                status="insufficient_input",
                action=None,
                support_kind="none",
                question_ref=None,
            ).model_dump()
            return result
        context = (
            self.model.model.disable_adapter()
            if policy == "base" and self.adapter_loaded
            else contextlib.nullcontext()
        )
        with context:
            prediction = self.model.predict(row)
        if prediction["prompt_sha256"] != encoded["prompt_sha256"]:
            raise ValueError("Prediction input does not match the recorded host input")
        result.update(
            prediction=prediction,
            adapter_active=policy == "adapted",
            greedy_answers=dict(prediction["answers"]),
        )
        answers = prediction["answers"]
        if self.decision_distribution == CONTRACT:
            validate_support(prediction["probabilities"], row)
            answers, _ = choose(prediction["probabilities"], distribution=CONTRACT)
        result["decoding"] = decoding_receipt(
            prediction["probabilities"], self.decision_distribution
        )
        if request.get("sample"):
            if type(request.get("seed")) is not int:
                raise ValueError("Sampled decisions require an explicit integer seed")
            answers, logp = choose(
                prediction["probabilities"],
                seed=request["seed"],
                distribution=self.decision_distribution,
            )
            result["behavior"] = dict(
                prompt_sha256=prediction["prompt_sha256"],
                probabilities=prediction["probabilities"],
                sampled_answers=answers,
                sampled_joint_log_probability=logp,
                seed=request["seed"],
                temperature=getattr(self.model, "temperature", 1.0),
                model_identity=self.model.identity,
                adapter_active=policy == "adapted",
                distribution=self.decision_distribution,
                decoding=result["decoding"],
            )
        result["decision_answers"] = answers
        try:
            choice = choice_from_answers(answers)
            decision = protocol.bind_choice(packet, view, choice, policy_id=policy_id)
        except ValueError as error:
            result["choice_error"] = str(error)
            decision = protocol.Decision(
                schema_version=protocol.VERSION,
                packet_id=packet.packet_id,
                model_view_sha256=view.sha256,
                policy_id=policy_id,
                status="inference_error",
                action=None,
                support_kind="none",
                question_ref=None,
            )
        result["decision"] = decision.model_dump()
        return result


def request(path, payload, *, timeout=30):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(str(path))
        client.sendall((json.dumps(payload, allow_nan=False) + "\n").encode())
        stream = client.makefile("rb")
        raw = stream.readline(2_000_001)
        if not raw or len(raw) > 2_000_000:
            raise ValueError("Missing or oversized attention response")
        result = json.loads(raw)
        if "error" in result:
            raise RuntimeError(result["error"])
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--adapter")
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--maximum-tokens", type=int, default=4096)
    parser.add_argument("--wall-seconds", type=int, default=14400)
    parser.add_argument("--idle-seconds", type=int, default=1800)
    parser.add_argument("--auth-token-file", type=Path)
    parser.add_argument("--kernel-profile", choices=("fla-prefill",))
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--decision-distribution", choices=DISTRIBUTIONS, default=INDEPENDENT)
    args = parser.parse_args()
    if not math.isfinite(args.temperature) or args.temperature <= 0:
        parser.error("--temperature must be finite and positive")
    auth_token = args.auth_token_file.read_text().strip() if args.auth_token_file else None
    if auth_token is not None and len(auth_token) < 32:
        raise ValueError("The optional forwarding credential must have at least 32 characters")
    if args.socket.exists():
        raise ValueError("Refuse to replace an existing server socket")
    from .decision_model import DecisionModel

    model = DecisionModel(
        args.checkpoint,
        adapter=args.adapter,
        max_tokens=args.maximum_tokens,
        kernel_profile=args.kernel_profile,
    )
    model.temperature = args.temperature
    service = AttentionService(
        model,
        adapter_loaded=bool(args.adapter),
        maximum_tokens=args.maximum_tokens,
        decision_distribution=args.decision_distribution,
    )
    started = time.time()
    status = dict(
        stage="ready",
        started_at=started,
        model_identity=model.identity,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        policies=["base", "adapted"] if args.adapter else ["base"],
        temperature=args.temperature,
        decision_distribution=args.decision_distribution,
        requests=0,
    )
    serve(
        service,
        socket_path=args.socket,
        status_path=args.status,
        auth_token=auth_token,
        wall_seconds=args.wall_seconds,
        idle_seconds=args.idle_seconds,
        status=status,
    )


def serve(service, *, socket_path, status_path, auth_token, wall_seconds, idle_seconds, status):
    """Serve one model call at a time, including adapter selection and receipt binding."""
    started = last = time.time()
    count = 0
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(socket_path))
        socket_path.chmod(0o600)
        server.listen(4)
        server.settimeout(1.0)
        put(status_path, status)
        try:
            while time.time() - started < wall_seconds and time.time() - last < idle_seconds:
                try:
                    client, _ = server.accept()
                except TimeoutError:
                    continue
                with client:
                    client.settimeout(30)
                    try:
                        raw = client.makefile("rb").readline(2_000_001)
                        if not raw or len(raw) > 2_000_000:
                            raise ValueError("Invalid request size")
                        value = json.loads(raw)
                        if auth_token is not None and not secrets.compare_digest(
                            str(value.pop("auth_token", "")), auth_token
                        ):
                            raise ValueError("Unauthorized attention request")
                        result = (
                            {"status": status}
                            if value.get("operation") == "health"
                            else service.predict(value)
                        )
                    except Exception as error:
                        result = {"error": type(error).__name__ + ": " + str(error)}
                    with contextlib.suppress(BrokenPipeError, TimeoutError):
                        client.sendall((json.dumps(result, allow_nan=False) + "\n").encode())
                count += 1
                last = time.time()
                status.update(requests=count, updated_at=last)
                put(status_path, status)
        finally:
            socket_path.unlink(missing_ok=True)
            status.update(stage="stopped", ended_at=time.time())
            put(status_path, status)


if __name__ == "__main__":
    main()
