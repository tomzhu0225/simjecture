"""Two-NPU LoRA SFT and one-update-per-live-group trajectory RLOO.

This module is an experiment entry point. Importing it does not load torch or
start training. Live Simjecture workers write closed four-trajectory groups to
the configured inbox and use the separate policy service during collection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import time
from pathlib import Path

from .rloo import validate_group


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["sft", "rloo"])
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--initial", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--resume", type=Path)
    return parser.parse_args()


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_checkpoint(path, revision):
    manifest = json.loads((path / "manifest.json").read_bytes())
    for name, expected in manifest.items():
        target = (path / name).resolve()
        if not target.is_relative_to(path.resolve()) or digest(target) != expected:
            raise ValueError("Immutable checkpoint checksum verification failed")
    state = json.loads((path / "state.json").read_bytes())
    if state.get("base_revision") != revision:
        raise ValueError("Checkpoint belongs to a different base revision")
    return state


def model_inputs(tokenizer, record):
    observation = record["observation"]
    prompt = policy_prompt_ids(tokenizer, observation)
    target = tokenizer.encode(
        json.dumps(record["teacher_public_decision"], ensure_ascii=False), add_special_tokens=False
    )
    target.append(tokenizer.eos_token_id)
    return prompt, target


def policy_prompt_ids(tokenizer, observation):
    messages = [
        dict(role="system", content=policy_system_prompt()),
        dict(role="user", content=json.dumps(observation, ensure_ascii=False, sort_keys=True)),
    ]
    encoded = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True, enable_thinking=False, return_dict=True
    )
    from collections.abc import Mapping

    prompt = encoded["input_ids"] if isinstance(encoded, Mapping) else encoded
    if hasattr(prompt, "tolist"):
        prompt = prompt.tolist()
    if prompt and isinstance(prompt[0], list):
        if len(prompt) != 1:
            raise ValueError("A decision has exactly one conditioning state")
        prompt = prompt[0]
    if not isinstance(prompt, list) or len(prompt) < 10 or not all(isinstance(x, int) for x in prompt):
        raise ValueError("Chat template did not produce a nonempty flat token sequence")
    return prompt


def policy_system_prompt():
    schema = (Path(__file__).resolve().parents[1] / "schemas/advice.schema.json").read_text(encoding="utf-8")
    return (
        "Advise scientific experiment selection, organization, parameters, model hierarchy and scale from "
        "the supplied public state and real receipts only. Output exactly one JSON object, no Markdown or "
        "extra text. Include every required field, keep public justifications concise, respect actual "
        "capacity and remaining wall time, and reserve time for verification. Do not generate solver code.\n"
        + schema
    )


def log_probability(model, prompt, response, *, temperature, torch, device, per_token=False):
    if not prompt or not response:
        raise ValueError("An action must contain both a conditioning state and sampled tokens")
    tokens = torch.tensor([prompt + response[:-1]], device=device, dtype=torch.long)
    output = model(
        input_ids=tokens,
        attention_mask=torch.ones_like(tokens),
        use_cache=False,
        logits_to_keep=len(response),
    )
    if output.logits.shape[1] != len(response):
        raise ValueError("The pinned model must implement response-only logits_to_keep")
    labels = torch.tensor(response, device=device, dtype=torch.long)
    # Chunk the 248320-way vocabulary reduction to limit temporary FP32 memory.
    chunks = []
    for offset in range(0, len(response), 128):
        logits = output.logits[0, offset : offset + 128].float() / temperature
        chunks.append(
            -torch.nn.functional.cross_entropy(logits, labels[offset : offset + 128], reduction="none")
        )
    values = torch.cat(chunks)
    return values if per_token else values.sum()


def activate(model, name):
    model.set_adapter(name)
    for key, parameter in model.named_parameters():
        parameter.requires_grad_(name == "default" and ".default." in key and "lora_" in key)


def synchronize_gradients(parameters, torch, dist, *, average):
    for parameter in parameters:
        if parameter.grad is None:
            parameter.grad = torch.zeros_like(parameter)
        dist.all_reduce(parameter.grad, op=dist.ReduceOp.SUM)
        if average:
            parameter.grad.div_(dist.get_world_size())


def move_optimizer(optimizer, device):
    for state in optimizer.state.values():
        for key, value in state.items():
            # Non-capturable AdamW keeps its scalar step counter on the CPU.
            if hasattr(value, "to") and key != "step":
                state[key] = value.to(device)


def handoff_to_rollouts(model, optimizer, torch, dist):
    optimizer.zero_grad(set_to_none=True)
    move_optimizer(optimizer, "cpu")
    model.to("cpu")
    import gc

    gc.collect()
    torch.npu.empty_cache()
    dist.barrier()


def checkpoint(model, optimizer, output, label, state, rank, torch, dist):
    destination = output / label
    staging = output / ("." + label + ".partial")
    if rank == 0:
        if destination.exists():
            raise FileExistsError("A saved checkpoint cannot be overwritten")
        if staging.exists():
            if not staging.resolve().is_relative_to(output.resolve()):
                raise ValueError("Staging checkpoint escaped its owned output directory")
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        model.save_pretrained(staging, selected_adapters=["default"], safe_serialization=True)
        (staging / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
        torch.save(optimizer.state_dict(), staging / "optimizer.pt")
    dist.barrier()
    torch.save(
        dict(
            python_rng=random.getstate(),
            torch_rng=torch.get_rng_state(),
            npu_rng=torch.npu.get_rng_state(),
        ),
        staging / f"rank-{rank}.pt",
    )
    dist.barrier()
    if rank == 0:
        files = {p.name: digest(p) for p in staging.iterdir() if p.is_file()}
        (staging / "manifest.json").write_text(json.dumps(files, indent=2), encoding="utf-8")
        os.replace(staging, destination)
        retain_recent_checkpoints(output)
    dist.barrier()
    return destination


def retain_recent_checkpoints(output):
    root = output.resolve()
    checkpoints = sorted(path for path in root.glob("rloo-update-*") if path.is_dir())
    pinned_file = root / "retain.json"
    pinned = set(json.loads(pinned_file.read_bytes())) if pinned_file.exists() else set()
    keep = {path.name for path in checkpoints[-2:]} | pinned
    history = root / "pruned-manifests"
    for candidate in checkpoints:
        if candidate.name in keep:
            continue
        target = candidate.resolve()
        if target.parent != root or candidate.is_symlink():
            raise ValueError("Checkpoint retention target escapes the owned output directory")
        history.mkdir(exist_ok=True)
        (history / (candidate.name + ".json")).write_bytes((candidate / "manifest.json").read_bytes())
        shutil.rmtree(target)


def train_sft(args, cfg, model, tokenizer, optimizer, parameters, rank, torch, dist, device):
    from .contracts import reject_private_fields

    rows = [json.loads(line) for line in args.data.read_text(encoding="utf-8").splitlines() if line.strip()]
    allowed = {
        json.loads(line)["task_id"]
        for line in (args.config.parent.parent / "tasks/train.jsonl").read_text(encoding="utf-8").splitlines()
    }
    if not rows or any(row["split"] != "train" or row["teacher"] != "gpt-6.1-sol" for row in rows):
        raise ValueError("SFT accepts only actual GPT-6.1 Sol demonstrations on train tasks")
    for row in rows:
        if row["task_id"] not in allowed:
            raise ValueError("Supervised task is outside the frozen training split")
        if not row["quality_review_receipt"]:
            raise ValueError("SFT demonstration lacks its independent review receipt")
        reject_private_fields(row["observation"])
    accumulation = cfg["sft"]["gradient_accumulation"]
    start_epoch = 0
    optimizer_updates = 0
    if args.resume:
        start_epoch = json.loads((args.resume / "state.json").read_bytes())["completed_epochs"]
        optimizer_updates = json.loads((args.resume / "state.json").read_bytes()).get("optimizer_updates", 0)
    for epoch in range(start_epoch, cfg["sft"]["epochs_initial"]):
        order = list(range(len(rows)))
        random.Random(20261116 + epoch).shuffle(order)
        width = dist.get_world_size() * accumulation
        # Padding uses real examples and is recorded in metadata. It keeps all
        # ranks at the same optimizer boundary for small final batches.
        padded = order + [order[i % len(order)] for i in range((-len(order)) % width)]
        shard = padded[rank :: dist.get_world_size()]
        optimizer.zero_grad(set_to_none=True)
        model.train()
        for index, row_index in enumerate(shard, 1):
            prompt, response = model_inputs(tokenizer, rows[row_index])
            if len(prompt) > cfg["input_tokens_initial"] or len(response) > cfg["output_tokens_initial"]:
                raise ValueError(
                    "Training data exceeds registered context capacity; rebuild the state explicitly"
                )
            logp = log_probability(model, prompt, response, temperature=1, torch=torch, device=device)
            (-logp / (len(response) * accumulation)).backward()
            if index % accumulation == 0:
                synchronize_gradients(parameters, torch, dist, average=True)
                torch.nn.utils.clip_grad_norm_(parameters, 1.0)
                optimizer.step()
                optimizer_updates += 1
                optimizer.zero_grad(set_to_none=True)
                if rank == 0:
                    from .storage import write_json

                    write_json(
                        args.output / "progress.json",
                        dict(
                            stage="sft",
                            optimizer_updates=optimizer_updates,
                            epoch=epoch + 1,
                            decisions_seen=index * dist.get_world_size(),
                            training_decisions=len(rows),
                        ),
                    )
        checkpoint(
            model,
            optimizer,
            args.output,
            f"sft-epoch-{epoch + 1}",
            dict(
                completed_epochs=epoch + 1,
                optimizer_updates=optimizer_updates,
                training_decisions=len(rows),
                training_data_sha256=digest(args.data),
                padding_decisions=len(padded) - len(rows),
                base_revision=cfg["base_revision"],
                stage="sft",
            ),
            rank,
            torch,
            dist,
        )


def train_rloo(args, cfg, model, optimizer, parameters, rank, torch, dist, device):
    if args.initial is None:
        raise ValueError("Online RLOO requires the frozen SFT checkpoint")
    model.load_adapter(args.initial, adapter_name="reference", is_trainable=False)
    activate(model, "default")
    args.data.mkdir(parents=True, exist_ok=True)
    consumed = set()
    update = 0
    optimizer_steps = 0
    policy_path = args.resume or args.initial
    allowed = {
        json.loads(line)["task_id"]
        for line in (args.config.parent.parent / "tasks/train.jsonl").read_text(encoding="utf-8").splitlines()
    }
    if args.resume:
        state = json.loads((args.resume / "state.json").read_bytes())
        consumed = set(state["consumed_group_ids"])
        update = state["completed_updates"]
        optimizer_steps = state.get("optimizer_steps", update)
    while True:
        from .storage import write_json

        handoff_to_rollouts(model, optimizer, torch, dist)
        request_id = f"rollout-{update:06d}"
        if rank == 0:
            write_json(
                args.data / "rollout-request.json",
                dict(
                    request_id=request_id,
                    completed_updates=update,
                    policy_path=str(policy_path),
                    policy_sha256=digest(policy_path / "adapter_model.safetensors"),
                    consumed_group_ids=sorted(consumed),
                    model_offloaded=True,
                    evaluate_before_next_group=update > 0 and update % 20 == 0,
                ),
            )
        packet = [None]
        while packet[0] is None:
            if rank == 0:
                if (args.data / "stop.json").exists():
                    packet[0] = {"stop": True}
                elif (args.data / (request_id + "-actors-stopped.json")).exists():
                    available = sorted(
                        path for path in args.data.glob("group-*.json") if path.stem not in consumed
                    )
                    if available:
                        packet[0] = {
                            "path": str(available[0]),
                            "group": json.loads(available[0].read_bytes()),
                        }
            dist.broadcast_object_list(packet, src=0, device=device)
            if packet[0] is None:
                time.sleep(2)
        if packet[0].get("stop"):
            break
        group = packet[0]["group"]
        trajectories = group["trajectories"]
        validate_group(trajectories)
        current_sha = digest(policy_path / "adapter_model.safetensors")
        if any(t["old_policy_sha256"] != current_sha for t in trajectories):
            raise ValueError("Live trajectories were generated by a stale policy checkpoint")
        if any(t["split"] != "train" for t in trajectories):
            raise ValueError("Development and test data cannot enter RL")
        if any(t["task_id"] not in allowed for t in trajectories):
            raise ValueError("RL task is outside the frozen training split")
        # The external service is stopped before updates and is reloaded with
        # the new immutable adapter afterward. Its device memory is released
        # during long CPU simulation trajectories, avoiding actor/trainer OOM.
        model.to(device)
        move_optimizer(optimizer, device)
        optimizer.zero_grad(set_to_none=True)
        # Keep gradient checkpointing active, while removing stochastic dropout
        # for exact behavior-policy replay during on-policy optimization.
        model.train()
        for module in model.modules():
            if isinstance(module, torch.nn.Dropout):
                module.p = 0.0
        kl_by_trajectory = {}
        ratio_by_trajectory = {}
        token_weights = {}
        token_diagnostics = {}
        for trajectory_index in range(rank, len(trajectories), dist.get_world_size()):
            trajectory = trajectories[trajectory_index]
            if not math_isfinite(trajectory["return"]):
                raise ValueError("Nonfinite scientific return")
            sequence_kl = 0.0
            rollout_log_ratio = 0.0
            weights_for_trajectory = []
            for action_index, action in enumerate(trajectory["actions"]):
                if action["policy_sha256"] != current_sha:
                    raise ValueError("Action policy provenance differs from the group checkpoint")
                with torch.no_grad():
                    activate(model, "reference")
                    reference = log_probability(
                        model,
                        action["input_ids"],
                        action["response_ids"],
                        temperature=action["temperature"],
                        torch=torch,
                        device=device,
                    )
                    activate(model, "default")
                    current = log_probability(
                        model,
                        action["input_ids"],
                        action["response_ids"],
                        temperature=action["temperature"],
                        torch=torch,
                        device=device,
                        per_token=True,
                    )
                behavior = torch.tensor(action["behavior_token_logprobs"], device=device)
                if behavior.shape != current.shape:
                    raise ValueError("Behavior token probabilities are incomplete")
                correction = torch.exp((current - behavior).clamp(-20, 20)).clamp(max=2).detach()
                token_weights[(trajectory_index, action_index)] = correction
                weights_for_trajectory.extend(correction.cpu().tolist())
                rollout_log_ratio += float(current.sum()) - action["behavior_logprob"]
                sequence_kl += float(current.sum() - reference)
            kl_by_trajectory[trajectory_index] = sequence_kl
            ratio_by_trajectory[trajectory_index] = rollout_log_ratio
            total = sum(weights_for_trajectory)
            token_diagnostics[trajectory_index] = dict(
                tokens=len(weights_for_trajectory),
                clipped_fraction=sum(w >= 2 for w in weights_for_trajectory)
                / max(1, len(weights_for_trajectory)),
                ESS=total**2 / max(1e-20, sum(w * w for w in weights_for_trajectory)),
            )
        all_kl = []
        for source_rank in range(dist.get_world_size()):
            values = [
                (kl_by_trajectory, ratio_by_trajectory, token_diagnostics) if rank == source_rank else None
            ]
            dist.broadcast_object_list(values, src=source_rank, device=device)
            all_kl.append(values[0])
        merged = {key: value for record, ratios, stats in all_kl for key, value in record.items()}
        log_ratios = {key: value for record, ratios, stats in all_kl for key, value in ratios.items()}
        token_stats = {key: value for record, ratios, stats in all_kl for key, value in stats.items()}
        shaped = [
            t["return"] - cfg["rloo"]["kl_beta_initial"] * merged[i] for i, t in enumerate(trajectories)
        ]
        from .rloo import action_advantages, leave_one_out, rollout_importance

        advantages = leave_one_out(shaped)
        importance = [rollout_importance(log_ratios[i]) for i in range(len(trajectories))]
        per_action = [action_advantages(t, advantages[i]) for i, t in enumerate(trajectories)]
        for trajectory_index in range(rank, len(trajectories), dist.get_world_size()):
            for action_index, action in enumerate(trajectories[trajectory_index]["actions"]):
                if not action["student_executed_components"]:
                    continue
                logp = log_probability(
                    model,
                    action["input_ids"],
                    action["response_ids"],
                    temperature=action["temperature"],
                    torch=torch,
                    device=device,
                    per_token=True,
                )
                (
                    -per_action[trajectory_index][action_index]
                    * (token_weights[(trajectory_index, action_index)] * logp).sum()
                    / len(trajectories)
                ).backward()
        eligible_actions = sum(
            bool(a["student_executed_components"]) for t in trajectories for a in t["actions"]
        )
        if eligible_actions:
            synchronize_gradients(parameters, torch, dist, average=False)
            torch.nn.utils.clip_grad_norm_(parameters, cfg["rloo"]["gradient_clip_norm"])
            optimizer.step()
            optimizer_steps += 1
        optimizer.zero_grad(set_to_none=True)
        update += 1
        consumed.add(Path(packet[0]["path"]).stem)
        policy_path = checkpoint(
            model,
            optimizer,
            args.output,
            f"rloo-update-{update:06d}",
            dict(
                completed_updates=update,
                optimizer_steps=optimizer_steps,
                eligible_actions=eligible_actions,
                consumed_group_ids=sorted(consumed),
                stage="rloo",
                base_revision=cfg["base_revision"],
                selection="external_C_D_development_monitor",
                rollout_log_ratios=log_ratios,
                rollout_importance=importance,
                loss_rollout_correction="tokenwise_truncated_IS; conditional surrogate with clipping bias",
                token_correction_diagnostics=token_stats,
                action_advantages=per_action,
                rollout_effective_sample_size=sum(importance) ** 2 / sum(value**2 for value in importance),
            ),
            rank,
            torch,
            dist,
        )


def math_isfinite(value):
    import math

    return isinstance(value, (int, float)) and math.isfinite(value)


def main():
    args = parse_args()
    cfg = json.loads(args.config.read_bytes())
    if cfg["base_model"] != "Qwen/Qwen3.5-9B":
        raise ValueError("This study admits Qwen3.5-9B as its sole base model")
    verification = json.loads((args.base / "verified-manifest.json").read_bytes())
    if verification["revision"] != cfg["base_revision"]:
        raise ValueError("Model revision mismatch")
    import torch
    import torch.distributed as dist
    import torch_npu  # noqa: F401
    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import AutoModelForImageTextToText, AutoTokenizer

    torch.__future__.set_swap_module_params_on_conversion(True)
    for candidate in {args.initial, args.resume} - {None}:
        verify_checkpoint(candidate, cfg["base_revision"])

    rank = int(os.environ["RANK"])
    local_rank = int(os.environ["LOCAL_RANK"])
    if int(os.environ["WORLD_SIZE"]) != 2:
        raise ValueError("The prepared hardware contract uses two NPUs")
    torch.npu.set_device(local_rank)
    device = torch.device(f"npu:{local_rank}")
    dist.init_process_group("hccl")
    random.seed(20261116 + rank)
    torch.manual_seed(20261116)
    base = AutoModelForImageTextToText.from_pretrained(
        args.base, torch_dtype=torch.bfloat16, local_files_only=True, attn_implementation="sdpa"
    )
    for parameter in base.parameters():
        parameter.requires_grad_(False)
    targets = [
        name
        for name, module in base.named_modules()
        if "language_model" in name
        and name.rsplit(".", 1)[-1] in cfg["lora"]["target_modules"]
        and isinstance(module, torch.nn.Linear)
    ]
    if not any("linear_attn" in name for name in targets) or not any("self_attn" in name for name in targets):
        raise ValueError("LoRA must cover both Gated DeltaNet and full attention modules")
    adapter = args.resume or args.initial
    if adapter:
        model = PeftModel.from_pretrained(base, adapter, is_trainable=True)
    else:
        lora = cfg["lora"]
        model = get_peft_model(
            base,
            LoraConfig(
                r=lora["r"],
                lora_alpha=lora["alpha"],
                lora_dropout=lora["dropout"],
                target_modules=targets,
                task_type="CAUSAL_LM",
            ),
        )
    model.to(device)
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    activate(model, "default")
    parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    stage_cfg = cfg["sft"] if args.stage == "sft" else cfg["rloo"]
    optimizer = torch.optim.AdamW(parameters, lr=stage_cfg["learning_rate"], weight_decay=0)
    if args.resume:
        state = torch.load(args.resume / f"rank-{rank}.pt", map_location="cpu", weights_only=False)
        optimizer.load_state_dict(
            torch.load(args.resume / "optimizer.pt", map_location="cpu", weights_only=False)
        )
        random.setstate(state["python_rng"])
        torch.set_rng_state(state["torch_rng"])
        torch.npu.set_rng_state(state["npu_rng"])
    args.output.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(args.base, local_files_only=True)
    if args.stage == "sft":
        train_sft(args, cfg, model, tokenizer, optimizer, parameters, rank, torch, dist, device)
    else:
        train_rloo(args, cfg, model, optimizer, parameters, rank, torch, dist, device)
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
