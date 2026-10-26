"""Supervised or measured-return masked-decision LoRA training.

Inputs use the upstream state/questions/targets interface. Reinforcement records
also require exact behavior distributions and hashed actual-continuation receipts.
Scripted curriculum preferences cannot stand in for executed rewards.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from collections import defaultdict
from pathlib import Path

from simjecture_monitor.decision_interface import encode_request, training_symbols
from simjecture_monitor.events import put


def read_data(path):
    with path.open() as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    if not rows or len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Training rows must have distinct identities and cannot be empty")
    if any(row.get("split") not in (None, "train") for row in rows):
        raise ValueError("Evaluation/development rows cannot enter the optimizer")
    return rows


def measured_advantages(rows, root):
    groups = defaultdict(list)
    for row in rows:
        receipt = row["outcome_receipt"]
        path = (root / receipt["path"]).resolve()
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != receipt["sha256"]:
            raise ValueError("Outcome receipt changed")
        outcome = json.loads(raw)
        if (
            outcome.get("source_kind") != "executed_worker_continuation"
            or outcome.get("status") != "completed"
            or outcome.get("prompt_sha256") != row["behavior"]["prompt_sha256"]
            or outcome.get("sampled_answers") != {k: v["label"] for k, v in row["targets"].items()}
            or not outcome.get("verification_sha256")
        ):
            raise ValueError(
                "Require a verified continuation bound to this actual sampled decision"
            )
        value = outcome["utility"]
        if not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError("Measured utility must be finite")
        groups[row["return_group"]].append((row, float(value)))
    result = {}
    for group in groups.values():
        if len(group) < 2:
            raise ValueError("Require at least two measured returns per comparison group")
        total = sum(value for _, value in group)
        for row, value in group:
            result[row["id"]] = value - (total - value) / (len(group) - 1)
    if max(map(abs, result.values())) < 1e-8:
        raise ValueError("No measured return variation; skip the RL update")
    return result


def require_behavior_weights(rows, base, adapter):
    """Nearby probabilities cannot stand in for the exact recorded adapter."""
    config = hashlib.sha256((Path(base) / "config.json").read_bytes()).hexdigest()
    files = {}
    if adapter is not None:
        for name in ["adapter_config.json", "adapter_model.safetensors"]:
            with (Path(adapter) / name).open("rb") as stream:
                files[name] = hashlib.file_digest(stream, "sha256").hexdigest()
    for row in rows:
        behavior = row["behavior"]
        identity = behavior.get("model_identity", {})
        expected = identity.get("adapter_files_sha256", {})
        if behavior.get("adapter_active") is False:
            expected = {}
        if identity.get("checkpoint_config_sha256") != config or expected != files:
            raise ValueError(
                "Initial base configuration or adapter differs from logged behavior weights"
            )


def episode_normalization(rows, audit):
    episodes = [episode for group in audit.values() for episode in group["sampled_episodes"]]
    if not episodes or sum(episode["decisions"] for episode in episodes) != len(rows):
        raise ValueError("Episode normalization requires the complete sampled decision count")
    return dict(
        unit="sampled_episode",
        sampled_episodes=len(episodes),
        decision_rows=len(rows),
        row_to_episode_scale=len(rows) / len(episodes),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("sft", "policy-gradient"), default="sft")
    parser.add_argument("--initial-adapter", type=Path)
    parser.add_argument("--steps", type=int, default=384)
    parser.add_argument("--accumulation", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--rank", type=int, default=16)
    parser.add_argument("--maximum-tokens", type=int, default=4096)
    parser.add_argument("--checkpoint-every", type=int, default=64)
    parser.add_argument("--seed", type=int, default=20261025)
    parser.add_argument("--wall-seconds", type=int, default=5400)
    parser.add_argument("--kernel-profile", choices=("fla-prefill",))
    parser.add_argument("--kl-coefficient", type=float, default=0.02)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument(
        "--advantage-baseline",
        choices=("leave-one-out", "measured-wait", "workflow-wait"),
        default="leave-one-out",
    )
    args = parser.parse_args()
    if (
        min(
            args.steps,
            args.accumulation,
            args.rank,
            args.maximum_tokens,
            args.checkpoint_every,
            args.wall_seconds,
            args.learning_rate,
            args.temperature,
        )
        <= 0
    ):
        raise ValueError("Training limits and rates must be positive")
    rows = read_data(args.data)
    advantage_audit = None
    normalization = dict(unit="training_row", row_to_episode_scale=1.0)
    if args.advantage_baseline in {"measured-wait", "workflow-wait"}:
        if args.mode != "policy-gradient":
            raise ValueError("A measured wait baseline applies only to policy-gradient updates")
        if args.advantage_baseline == "workflow-wait":
            from simjecture_monitor.workflow_returns import workflow_advantages

            advantages, advantage_audit = workflow_advantages(rows, args.data.parent)
            normalization = episode_normalization(rows, advantage_audit)
        else:
            from simjecture_monitor.measured_wait import wait_controlled_advantages

            advantages, advantage_audit = wait_controlled_advantages(rows, args.data.parent)
    else:
        advantages = (
            measured_advantages(rows, args.data.parent) if args.mode == "policy-gradient" else {}
        )
    if args.mode == "policy-gradient" and args.steps * args.accumulation > 2 * len(rows):
        raise ValueError("Measured-return updates allow at most two passes over logged behavior")
    if args.mode == "policy-gradient" and any(
        row["behavior"].get("temperature", args.temperature) != args.temperature for row in rows
    ):
        raise ValueError("Training temperature must match every logged behavior distribution")
    if args.mode == "policy-gradient":
        require_behavior_weights(rows, args.base, args.initial_adapter)
    args.output.mkdir(parents=True, exist_ok=False)
    if advantage_audit is not None:
        put(args.output / (args.advantage_baseline + "-advantages.json"), advantage_audit)
    import torch
    from peft import LoraConfig, PeftModel, get_peft_model
    from simjecture_monitor.decision_model import DecisionModel

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    started = time.time()
    status = dict(
        stage="loading",
        started_at=started,
        rows=len(rows),
        loss_normalization=normalization,
        arguments={
            key: str(value) if isinstance(value, Path) else value
            for key, value in vars(args).items()
        },
        dataset_sha256=hashlib.sha256(args.data.read_bytes()).hexdigest(),
        source_sha256={
            "trainer": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
    )
    put(args.output / "status.json", status)
    policy = DecisionModel(
        args.base, max_tokens=args.maximum_tokens, kernel_profile=args.kernel_profile
    )
    policy.temperature = args.temperature
    encoded = [
        encode_request(row, policy.tokenizer, maximum_tokens=args.maximum_tokens) for row in rows
    ]
    symbols = [training_symbols(row, item) for row, item in zip(rows, encoded, strict=True)]
    status["input_tokens"] = dict(
        minimum=min(len(e["input_ids"]) for e in encoded),
        maximum=max(len(e["input_ids"]) for e in encoded),
    )
    put(
        args.output / "inputs.json",
        [
            dict(
                id=row["id"],
                prompt_sha256=item["prompt_sha256"],
                input_tokens=len(item["input_ids"]),
            )
            for row, item in zip(rows, encoded, strict=True)
        ],
    )
    if args.initial_adapter:
        policy.model = PeftModel.from_pretrained(
            policy.model, args.initial_adapter, is_trainable=True
        )
    else:
        policy.model = get_peft_model(
            policy.model,
            LoraConfig(
                r=args.rank,
                lora_alpha=2 * args.rank,
                lora_dropout=0.0,
                bias="none",
                task_type="CAUSAL_LM",
                target_modules=(
                    r"model\.language_model\.layers\.\d+\.(self_attn|linear_attn|mlp)\."
                    r"(q_proj|k_proj|v_proj|o_proj|in_proj_qkv|in_proj_z|in_proj_a|in_proj_b|"
                    r"out_proj|gate_proj|up_proj|down_proj)"
                ),
            ),
        )
    parameters = [p for p in policy.model.parameters() if p.requires_grad]
    trainable = [name for name, p in policy.model.named_parameters() if p.requires_grad]
    if not parameters or any(
        "lora_" not in name or "language_model" not in name for name in trainable
    ):
        raise ValueError("Only language-backbone LoRA parameters may be trainable")
    status.update(stage="training", trainable_parameters=sum(p.numel() for p in parameters))
    put(args.output / "trainable-modules.json", trainable)
    if args.mode == "policy-gradient":
        maximum_error = 0
        policy.model.eval()
        for row in rows:
            prediction = policy.predict(row)
            if prediction["prompt_sha256"] != row["behavior"]["prompt_sha256"]:
                raise ValueError("Behavior prompt mismatch")
            for field, values in prediction["probabilities"].items():
                old = row["behavior"]["probabilities"][field]
                if set(old) != set(values) or abs(sum(old.values()) - 1) > 1e-5:
                    raise ValueError("Behavior probability support mismatch")
                maximum_error = max(maximum_error, max(abs(old[k] - v) for k, v in values.items()))
        if maximum_error > 0.002:
            raise ValueError(f"Initial checkpoint does not reproduce behavior: {maximum_error}")
        status["behavior_probability_max_error"] = maximum_error
    policy.model.gradient_checkpointing_enable(
        gradient_checkpointing_kwargs={"use_reentrant": False}
    )
    policy.model.enable_input_require_grads()
    policy.model.train()
    optimizer = torch.optim.AdamW(parameters, lr=args.learning_rate)
    order, cursor, history = [], 0, []
    deadline = started + args.wall_seconds

    def save(name):
        policy.model.save_pretrained(args.output / name)
        policy.tokenizer.save_pretrained(args.output / name)
        torch.save(
            dict(
                optimizer=optimizer.state_dict(),
                torch_rng=torch.get_rng_state(),
                cuda_rng=torch.cuda.get_rng_state_all(),
                python_rng=random.getstate(),
            ),
            args.output / (name + "-optimizer.pt"),
        )

    for step in range(args.steps):
        if time.time() >= deadline or (args.output / "STOP").exists():
            status["stop_reason"] = "wall_or_operator_limit"
            break
        optimizer.zero_grad()
        losses, kls = [], []
        step_started = time.time()
        for _ in range(args.accumulation):
            if cursor >= len(order):
                order = list(range(len(rows)))
                random.shuffle(order)
                cursor = 0
            index = order[cursor]
            cursor += 1
            row, item = rows[index], encoded[index]
            ids = torch.tensor([item["input_ids"]], device="cuda")
            positions = torch.tensor(item["positions"], device="cuda")
            values = (
                policy.model(input_ids=ids, use_cache=False, logits_to_keep=positions)
                .logits[0]
                .float()
            )
            if args.mode == "sft":
                loss = torch.nn.functional.cross_entropy(
                    values, torch.tensor(symbols[index], device="cuda")
                )
                kl = values.new_zeros(())
            else:
                current_logp, old_logp, kl = values.new_zeros(()), 0.0, values.new_zeros(())
                for position, (field, labels) in enumerate(item["labels"].items()):
                    logp = (
                        values[position, item["symbol_ids"][: len(labels)]] / policy.temperature
                    ).log_softmax(-1)
                    selected = labels.index(str(row["targets"][field]["label"]))
                    old = row["behavior"]["probabilities"][field]
                    current_logp = current_logp + logp[selected]
                    old_logp += math.log(old[labels[selected]])
                    reference = torch.tensor([old[k] for k in labels], device="cuda")
                    kl = kl + (logp.exp() * (logp - reference.clamp_min(1e-12).log())).sum()
                ratio = (current_logp - old_logp).exp()
                advantage = advantages[row["id"]]
                loss = (
                    -torch.minimum(ratio * advantage, ratio.clamp(0.8, 1.2) * advantage)
                    + args.kl_coefficient * kl
                )
            loss = loss * normalization["row_to_episode_scale"]
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite training loss")
            (loss / args.accumulation).backward()
            losses.append(float(loss.detach()))
            kls.append(float(kl.detach()))
        norm = float(torch.nn.utils.clip_grad_norm_(parameters, 1.0))
        if not math.isfinite(norm):
            raise ValueError("Nonfinite training gradient")
        optimizer.step()
        record = dict(
            step=step + 1,
            loss=sum(losses) / len(losses),
            kl=sum(kls) / len(kls),
            gradient_norm=norm,
            seconds=time.time() - step_started,
        )
        history.append(record)
        with (args.output / "history.jsonl").open("a") as stream:
            stream.write(json.dumps(record) + "\n")
        status.update(
            optimizer_steps=step + 1,
            last_update=record,
            updated_at=time.time(),
            peak_cuda_bytes=torch.cuda.max_memory_allocated(),
        )
        put(args.output / "status.json", status)
        print(json.dumps(record), flush=True)
        if (step + 1) % args.checkpoint_every == 0:
            save(f"step-{step + 1:05d}")
    if not history or not any(row["gradient_norm"] > 0 for row in history):
        raise ValueError("No nonzero optimizer update")
    save("adapter")
    policy.model.eval()
    probes = rows[:2]
    before = [policy.predict(row) for row in probes]
    policy.model = policy.model.unload()
    policy.model = PeftModel.from_pretrained(policy.model, args.output / "adapter").eval()
    after = [policy.predict(row) for row in probes]
    error = max(
        abs(a["probabilities"][f][k] - b["probabilities"][f][k])
        for a, b in zip(before, after, strict=True)
        for f in a["probabilities"]
        for k in a["probabilities"][f]
    )
    put(args.output / "reload.json", dict(max_probability_error=error, before=before, after=after))
    if error > 1e-5:
        raise ValueError("Saved adapter does not reproduce in-memory predictions")
    status.update(
        stage="completed",
        ended_at=time.time(),
        elapsed_seconds=time.time() - started,
        reload_probability_max_error=error,
        scope="Training mechanics; downstream scientific advantage requires separate evaluation",
    )
    put(args.output / "status.json", status)


if __name__ == "__main__":
    main()
