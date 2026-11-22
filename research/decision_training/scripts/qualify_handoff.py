"""Synthetic NPU rollout/replay, nonzero-state persistence and CPU handoff.

No physical task, scientific evidence, teacher call, optimizer step or training
sample is created. The fixture uses arbitrary token IDs, separate diagnostics.
"""

import gc
import json
import os
import random
import time
from pathlib import Path


def main():
    import torch
    import torch.distributed as dist
    import torch_npu  # noqa: F401
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForImageTextToText

    from research_decision.train_adapter import (
        checkpoint,
        handoff_to_rollouts,
        log_probability,
        move_optimizer,
    )

    root = Path("/srv/simjecture-decision")
    rank = int(os.environ["RANK"])
    torch.npu.set_device(rank)
    device = torch.device(f"npu:{rank}")
    dist.init_process_group("hccl")
    torch.__future__.set_swap_module_params_on_conversion(True)
    torch.manual_seed(20261116)
    base = AutoModelForImageTextToText.from_pretrained(
        root / "models/Qwen3.5-9B",
        torch_dtype=torch.bfloat16,
        local_files_only=True,
        attn_implementation="sdpa",
    )
    for p in base.parameters():
        p.requires_grad_(False)
    cfg = json.loads((root / "config/training.json").read_bytes())
    targets = [
        n
        for n, m in base.named_modules()
        if "language_model" in n
        and n.rsplit(".", 1)[-1] in cfg["lora"]["target_modules"]
        and isinstance(m, torch.nn.Linear)
    ]
    model = (
        get_peft_model(
            base,
            LoraConfig(r=64, lora_alpha=128, lora_dropout=0, target_modules=targets, task_type="CAUSAL_LM"),
        )
        .to(device)
        .eval()
    )
    parameters = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(parameters, lr=5e-6)
    # Exercise nonzero Adam/RNG persistence without invoking optimizer.step().
    for p in parameters:
        optimizer.state[p] = dict(
            step=torch.tensor(17.0), exp_avg=torch.full_like(p, 0.001), exp_avg_sq=torch.full_like(p, 0.0002)
        )
    ids = [id(p) for p in parameters]
    directory = root / "diagnostics/handoff"
    directory.mkdir(parents=True, exist_ok=True)
    label = "synthetic-checkpoint-" + str(int(time.time()))
    destination = checkpoint(
        model, optimizer, directory, label, dict(synthetic_only=True, optimizer_updates=0), rank, torch, dist
    )
    restored = torch.load(destination / "optimizer.pt", map_location="cpu", weights_only=False)
    optimizer.load_state_dict(restored)
    assert all(
        torch.all(s["exp_avg"] == 0.001) and torch.all(s["exp_avg_sq"] == 0.0002) and float(s["step"]) == 17
        for s in optimizer.state.values()
    )
    rng = torch.load(destination / f"rank-{rank}.pt", map_location="cpu", weights_only=False)
    random.setstate(rng["python_rng"])
    torch.set_rng_state(rng["torch_rng"])
    torch.npu.set_rng_state(rng["npu_rng"])
    started = time.monotonic()
    handoff_to_rollouts(model, optimizer, torch, dist)
    after_offload = torch.npu.memory_allocated()
    assert ids == [id(p) for p in model.parameters() if p.requires_grad]
    assert all(p.device.type == "cpu" for p in parameters)
    model.to(device)
    move_optimizer(optimizer, device)
    assert ids == [id(p) for p in model.parameters() if p.requires_grad]
    assert all(p.device.type == "npu" for p in parameters)
    handoff_seconds = time.monotonic() - started
    runs = []
    model.eval()
    with torch.no_grad():
        for count in [512, 16384]:
            torch.manual_seed(20261116 + rank + count)
            prompt = torch.randint(100, 10000, (1, count), device=device)
            started = time.monotonic()
            generated = model.generate(
                input_ids=prompt,
                attention_mask=torch.ones_like(prompt),
                do_sample=True,
                temperature=0.8,
                top_k=0,
                top_p=1.0,
                repetition_penalty=1.0,
                max_new_tokens=64,
                min_new_tokens=64,
                use_cache=True,
                return_dict_in_generate=True,
                output_scores=True,
            )
            response = generated.sequences[0, count:].tolist()
            behavior = sum(
                float(torch.log_softmax(s.float(), -1)[0, t]) for s, t in zip(generated.scores, response)
            )
            replay = float(
                log_probability(
                    model, prompt[0].tolist(), response, temperature=0.8, torch=torch, device=device
                )
            )
            gap = replay - behavior
            runs.append(
                dict(
                    prompt_tokens=count,
                    sampled_tokens=len(response),
                    behavior_logprob=behavior,
                    replay_logprob=replay,
                    log_ratio=gap,
                    elapsed_seconds=time.monotonic() - started,
                )
            )
            del generated, prompt
            gc.collect()
            torch.npu.empty_cache()
    result = dict(
        rank=rank,
        runs=runs,
        checkpoint_optimizer_nonzero_roundtrip=True,
        RNG_restored=True,
        parameter_identity_preserved=True,
        allocated_hbm_after_CPU_offload_bytes=after_offload,
        CPU_handoff_and_reload_seconds=handoff_seconds,
        optimizer_updates=0,
        physical_studies=0,
        teacher_calls=0,
        fixture_not_training_data=True,
    )
    (directory / f"rank-{rank}.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)
    dist.barrier()
    # Keep compact manifest/provenance; large synthetic tensors are not data.
    if rank == 0:
        import shutil

        assert destination.resolve().is_relative_to(directory.resolve())
        shutil.rmtree(destination)
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
