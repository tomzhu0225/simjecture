"""Small PPO-style LoRA continuation using measured real-worker episode returns."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path

import torch
from peft import LoraConfig, PeftModel, get_peft_model
from simjecture_monitor.events import put
from simjecture_monitor.model import MonitorModel
from simjecture_monitor.policy import ACTIONS


def logits(policy, packet):
    batch, positions, candidates, prompt_hash, view = policy.encode(packet)
    value = (
        policy.model(**batch, use_cache=False, logits_to_keep=positions)
        .logits[0, 0, candidates]
        .float()
        / policy.temperature
    )
    return value, prompt_hash, view


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    data = json.loads(args.data.read_text())
    episodes = data["episodes"]
    if len(episodes) < 4:
        raise ValueError("Require four complete sampled episodes before training")
    groups = {
        case: [e for e in episodes if e["case"] == case] for case in {e["case"] for e in episodes}
    }
    if any(len(group) < 2 for group in groups.values()):
        raise ValueError("Need two independent returns per task family")
    for episode in episodes:
        others = [e["reward"] for e in groups[episode["case"]] if e["id"] != episode["id"]]
        episode["advantage"] = episode["reward"] - sum(others) / len(others)
    if max(abs(e["advantage"]) for e in episodes) < 1e-8:
        raise ValueError("No return variation; no learning update is justified")
    torch.manual_seed(20261024)
    random.seed(20261024)
    started = time.time()
    status = dict(
        stage="loading",
        started_at=started,
        dataset_sha256=hashlib.sha256(args.data.read_bytes()).hexdigest(),
        episode_returns={e["id"]: e["reward"] for e in episodes},
    )
    put(args.output / "status.json", status)
    policy = MonitorModel(args.base)
    policy.model = get_peft_model(
        policy.model,
        LoraConfig(
            r=8,
            lora_alpha=16,
            lora_dropout=0.0,
            target_modules=["q_proj", "v_proj", "o_proj", "up_proj", "down_proj"],
            bias="none",
            task_type="CAUSAL_LM",
        ),
    )
    parameters = [p for p in policy.model.parameters() if p.requires_grad]
    if any("lora_" not in name for name, p in policy.model.named_parameters() if p.requires_grad):
        raise ValueError("Base weights must remain frozen")
    status.update(
        stage="checking_behavior", trainable_parameters=sum(p.numel() for p in parameters)
    )
    put(args.output / "status.json", status)
    maximum_error = 0
    with torch.inference_mode():
        for episode in episodes:
            for record in episode["decisions"]:
                values, prompt_hash, _ = logits(policy, record["packet"])
                if prompt_hash != record["prompt_sha256"]:
                    raise ValueError("Training prompt differs from logged behavior prompt")
                p = values.softmax(-1).cpu()
                reference = torch.tensor(
                    [record["reference_probabilities"][key] for key in ACTIONS]
                )
                reference /= reference.sum()
                maximum_error = max(maximum_error, float((p - reference).abs().max()))
    if maximum_error > 1e-3:
        raise ValueError(f"Initial policy does not reproduce behavior: {maximum_error}")
    status.update(stage="training", initial_probability_max_error=maximum_error)
    put(args.output / "status.json", status)
    policy.model.gradient_checkpointing_enable(
        gradient_checkpointing_kwargs={"use_reentrant": False}
    )
    policy.model.enable_input_require_grads()
    policy.model.train()
    optimizer = torch.optim.AdamW(parameters, lr=1e-5)
    history = []
    actions = list(ACTIONS)
    for epoch in range(2):
        order = list(episodes)
        random.shuffle(order)
        for episode in order:
            optimizer.zero_grad()
            statistics = []
            for record in episode["decisions"]:
                values, prompt_hash, _ = logits(policy, record["packet"])
                if prompt_hash != record["prompt_sha256"]:
                    raise ValueError("Prompt changed during optimization")
                logp = values.log_softmax(-1)
                index = actions.index(record["action"])
                old = torch.tensor(record["behavior_probability"], device="cuda").log()
                ratio = (logp[index] - old).exp()
                advantage = episode["advantage"]
                surrogate = torch.minimum(ratio * advantage, ratio.clamp(0.8, 1.2) * advantage)
                reference = torch.tensor(
                    [record["reference_probabilities"][key] for key in actions], device="cuda"
                )
                reference /= reference.sum()
                kl = (logp.exp() * (logp - reference.clamp_min(1e-8).log())).sum()
                loss = (-surrogate + 0.02 * kl) / len(episode["decisions"])
                if not torch.isfinite(loss):
                    raise ValueError("Nonfinite learning loss")
                loss.backward()
                statistics.append(
                    dict(
                        loss=float(loss.detach()),
                        kl=float(kl.detach()),
                        ratio=float(ratio.detach()),
                    )
                )
            norm = float(torch.nn.utils.clip_grad_norm_(parameters, 1.0))
            if not torch.isfinite(torch.tensor(norm)):
                raise ValueError("Nonfinite gradient")
            optimizer.step()
            history.append(
                dict(
                    epoch=epoch,
                    episode=episode["id"],
                    gradient_norm=norm,
                    advantage=episode["advantage"],
                    mean_kl=sum(r["kl"] for r in statistics) / len(statistics),
                    loss=sum(r["loss"] for r in statistics),
                )
            )
            status.update(
                optimizer_steps=len(history), last_update=history[-1], updated_at=time.time()
            )
            put(args.output / "status.json", status)
    if not any(row["gradient_norm"] > 0 for row in history):
        raise ValueError("No nonzero gradient was observed")
    adapter = args.output / "adapter"
    policy.model.save_pretrained(adapter)
    policy.tokenizer.save_pretrained(adapter)
    torch.save(
        dict(
            optimizer=optimizer.state_dict(),
            torch_rng=torch.get_rng_state(),
            cuda_rng=torch.cuda.get_rng_state_all(),
        ),
        args.output / "optimizer.pt",
    )
    policy.model.eval()
    probes = [episodes[0]["decisions"][0]["packet"], episodes[-1]["decisions"][-1]["packet"]]
    before = [policy.predict(packet) for packet in probes]
    policy.model = policy.model.unload()
    policy.model = PeftModel.from_pretrained(policy.model, adapter).eval()
    after = [policy.predict(packet) for packet in probes]
    reload_error = max(
        abs(a["probabilities"][key] - b["probabilities"][key])
        for a, b in zip(before, after, strict=True)
        for key in ACTIONS
    )
    if reload_error > 1e-5:
        raise ValueError("Saved adapter reload changed predictions")
    put(args.output / "history.json", history)
    put(
        args.output / "reload.json",
        dict(max_probability_error=reload_error, before=before, after=after),
    )
    status.update(
        stage="completed",
        ended_at=time.time(),
        elapsed_seconds=time.time() - started,
        reload_probability_error=reload_error,
        peak_cuda_bytes=torch.cuda.max_memory_allocated(),
        scope="Mechanics of learning from real returns; no RL superiority claim",
    )
    put(args.output / "status.json", status)


if __name__ == "__main__":
    main()
