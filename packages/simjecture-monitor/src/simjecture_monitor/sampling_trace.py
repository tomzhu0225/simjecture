"""Durable sampled decisions from the actual parked-worker observation loop."""

from __future__ import annotations

import hashlib
import math
import time
from pathlib import Path

from . import attention_support as protocol
from .action_distribution import DISTRIBUTIONS, INDEPENDENT, kind, replay
from .decision_interface import scientific_request
from .events import digest, put


def file_reference(path):
    return dict(path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


class SamplingTrace:
    def __init__(self, directory, *, seed, split="train", decision_distribution=INDEPENDENT):
        if type(seed) is not int:
            raise ValueError("Sampling requires an explicit integer seed")
        if split not in {"train", "commissioning"}:
            raise ValueError("Unknown sampling-data purpose")
        if decision_distribution not in DISTRIBUTIONS:
            raise ValueError("Unknown action distribution")
        self.directory = Path(directory)
        self.path = self.directory / "SAMPLING.json"
        if self.path.exists():
            raise ValueError("Refuse to overwrite an existing sampling trace")
        self.data = dict(
            schema="parked-workflow-sampling/v1",
            episode_id=self.directory.parent.name,
            seed=seed,
            split=split,
            decision_distribution=decision_distribution,
            created_at=time.time(),
            closed=False,
            requests=[],
            responses=[],
            model_identity=None,
            temperature=None,
        )
        self.save()

    def save(self):
        put(self.path, self.data)

    def request(self, packet, *, policy):
        if self.data["closed"] or packet.worker_state != "parked":
            raise ValueError("Sample only from a live parked-worker episode")
        index = len(self.data["requests"])
        seed = int(digest([self.data["seed"], index])[:16], 16)
        source = self.directory / f"sampling-request-{index:05d}.json"
        put(source, packet.model_dump())
        self.data["requests"].append(
            dict(
                index=index,
                seed=seed,
                policy=policy,
                packet_sha256=digest(packet.model_dump()),
                submitted=file_reference(source),
                requested_at=time.time(),
            )
        )
        self.save()
        return dict(sample=True, seed=seed, distribution=self.data["decision_distribution"])

    def record(self, packet, result, *, decision_path):
        if self.data["closed"]:
            raise ValueError("Cannot append a delayed response to a closed episode")
        behavior = result.get("behavior")
        if not behavior:
            raise ValueError("Missing sampled behavior; episode is not training eligible")
        if kind(behavior) != self.data["decision_distribution"]:
            raise ValueError("Behavior distribution differs from the assigned episode")
        requested = [r for r in self.data["requests"] if r["seed"] == behavior.get("seed")]
        if len(requested) != 1:
            raise ValueError("Response has no unique assigned sampling request")
        request = requested[0]
        if any(r["index"] == request["index"] for r in self.data["responses"]):
            raise ValueError("Sampling response already recorded")
        if request["policy"] != result.get("policy") or request["packet_sha256"] != digest(
            packet.model_dump()
        ):
            raise ValueError("Response policy or public observation differs from its request")
        temperature = behavior.get("temperature")
        if (
            not isinstance(temperature, (int, float))
            or isinstance(temperature, bool)
            or not math.isfinite(temperature)
            or temperature <= 0
        ):
            raise ValueError("Missing or invalid behavior temperature")
        if behavior.get("model_identity") != result.get("model_identity"):
            raise ValueError("Behavior model identity is not the served identity")
        if not result.get("model_identity"):
            raise ValueError("Missing served model identity")
        if self.data["model_identity"] is not None and (
            self.data["model_identity"] != result["model_identity"]
            or self.data["temperature"] != temperature
        ):
            raise ValueError("Behavior model or temperature changed within an episode")
        prediction = result["prediction"]
        if (
            behavior["prompt_sha256"] != result["input_prompt_sha256"]
            or behavior["prompt_sha256"] != prediction["prompt_sha256"]
            or behavior["probabilities"] != prediction["probabilities"]
        ):
            raise ValueError("Behavior does not match the scored model input")
        view = protocol.PackedView.model_validate(result["view"])
        row = scientific_request(packet, view)
        answers, logp = replay(behavior, row)
        if answers != behavior["sampled_answers"] or not math.isclose(
            logp, behavior["sampled_joint_log_probability"], abs_tol=1e-10, rel_tol=1e-10
        ):
            raise ValueError("Logged action is not the assigned categorical draw")
        row.update(
            id="decision-"
            + digest([self.data["episode_id"], request["index"], request["packet_sha256"]])[:20],
            split=self.data["split"],
            profile="parked-scientific-workflow/v1",
            episode_id=self.data["episode_id"],
            step_index=request["index"],
            targets={key: dict(label=value) for key, value in answers.items()},
            behavior=behavior,
            observation=packet.model_dump(),
            decision_receipt=file_reference(decision_path),
        )
        path = self.directory / f"sampled-row-{request['index']:05d}.json"
        put(path, row)
        self.data["responses"].append(dict(index=request["index"], row=file_reference(path)))
        self.data.update(model_identity=result["model_identity"], temperature=temperature)
        self.save()

    def close(self):
        self.data.update(closed=True, ended_at=time.time())
        self.save()
