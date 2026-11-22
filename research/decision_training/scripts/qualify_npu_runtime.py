"""Synthetic compatibility check. No research task, generation or optimizer update."""

import argparse
import json
import os
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tokens", type=int, default=256)
    parser.add_argument("--target-tokens", type=int, default=32)
    parser.add_argument("--check-roundtrip", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    import torch
    import torch.distributed as dist
    import torch_npu  # noqa: F401
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForImageTextToText

    root = args.root
    rank = int(os.environ["RANK"])
    local_rank = int(os.environ["LOCAL_RANK"])
    torch.npu.set_device(local_rank)
    device = torch.device(f"npu:{local_rank}")
    dist.init_process_group("hccl")
    torch.manual_seed(20261116)
    started = time.monotonic()
    base = AutoModelForImageTextToText.from_pretrained(
        root / "models/Qwen3.5-9B",
        torch_dtype=torch.bfloat16,
        local_files_only=True,
        attn_implementation="sdpa",
    )
    for parameter in base.parameters():
        parameter.requires_grad_(False)
    cfg = json.loads((root / "config/training.json").read_bytes())
    targets = [
        name
        for name, module in base.named_modules()
        if "language_model" in name
        and name.rsplit(".", 1)[-1] in cfg["lora"]["target_modules"]
        and isinstance(module, torch.nn.Linear)
    ]
    model = get_peft_model(
        base, LoraConfig(r=64, lora_alpha=128, lora_dropout=0, target_modules=targets, task_type="CAUSAL_LM")
    )
    model.to(device).train()
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    load_seconds = time.monotonic() - started
    # IDs are arbitrary synthetic symbols. There is no teacher sample or physics state.
    torch.manual_seed(20261116 + rank)
    inputs = torch.randint(100, 10000, (1, args.tokens), device=device)
    labels = inputs[0, -args.target_tokens :]
    torch.npu.synchronize()
    started = time.monotonic()
    output = model(
        input_ids=inputs[:, :-1],
        attention_mask=torch.ones_like(inputs[:, :-1]),
        use_cache=False,
        logits_to_keep=args.target_tokens,
    )
    loss = (
        sum(
            torch.nn.functional.cross_entropy(
                output.logits[0, offset : offset + 128].float(),
                labels[offset : offset + 128],
                reduction="sum",
            )
            for offset in range(0, args.target_tokens, 128)
        )
        / args.target_tokens
    )
    loss.backward()
    torch.npu.synchronize()
    elapsed = time.monotonic() - started
    grads = [p.grad for p in model.parameters() if p.requires_grad and p.grad is not None]
    finite = bool(torch.stack([torch.isfinite(g).all() for g in grads]).all())
    norm = torch.stack([g.float().square().sum() for g in grads]).sum().sqrt()
    values = torch.tensor([float(loss), float(norm)], device=device)
    dist.all_reduce(values)
    communication_started = time.monotonic()
    for gradient in grads:
        dist.all_reduce(gradient)
        gradient.div_(dist.get_world_size())
    torch.npu.synchronize()
    synchronized_norm = torch.stack([g.float().square().sum() for g in grads]).sum().sqrt()
    report = dict(
        rank=rank,
        synthetic_sequence_tokens=args.tokens,
        assistant_target_tokens=args.target_tokens,
        load_seconds=load_seconds,
        forward_backward_seconds=elapsed,
        LoRA_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),
        finite_gradients=finite,
        loss=float(loss),
        gradient_norm=float(norm),
        communication_sum=values.tolist(),
        peak_hbm_bytes=torch.npu.max_memory_allocated(),
        synchronized_gradient_norm=float(synchronized_norm),
        gradient_communication_seconds=time.monotonic() - communication_started,
        optimizer_updates=0,
        research_tasks=0,
        teacher_calls=0,
        generated_tokens=0,
    )
    if args.check_roundtrip:
        from peft import get_peft_model_state_dict, set_peft_model_state_dict

        state = {name: value.detach().cpu() for name, value in get_peft_model_state_dict(model).items()}
        directory = root / "diagnostics"
        directory.mkdir(exist_ok=True)
        path = directory / f"synthetic-adapter-rank-{rank}.pt"
        torch.save(state, path)
        restored = torch.load(path, map_location="cpu", weights_only=True)
        set_peft_model_state_dict(model, restored)
        current = get_peft_model_state_dict(model)
        report["adapter_roundtrip_exact"] = all(
            torch.equal(value, current[name].detach().cpu()) for name, value in state.items()
        )
        path.unlink()
        model.eval()
        prompt = inputs[:, :128]
        with torch.no_grad():
            generated = model.generate(
                input_ids=prompt,
                attention_mask=torch.ones_like(prompt),
                do_sample=True,
                temperature=0.8,
                top_k=0,
                top_p=1,
                repetition_penalty=1,
                max_new_tokens=4,
                use_cache=True,
                return_dict_in_generate=True,
                output_scores=True,
            )
            response = generated.sequences[:, prompt.shape[1] :]
            behavior = sum(
                torch.log_softmax(scores.float(), dim=-1)[0, token]
                for scores, token in zip(generated.scores, response[0])
            )
            sequence = torch.cat((prompt, response[:, :-1]), dim=1)
            replay = (
                model(
                    input_ids=sequence,
                    attention_mask=torch.ones_like(sequence),
                    use_cache=False,
                    logits_to_keep=response.shape[1],
                )
                .logits[0]
                .float()
                / 0.8
            )
            replay_logp = -torch.nn.functional.cross_entropy(replay, response[0], reduction="sum")
            report["synthetic_generated_tokens"] = response.shape[1]
            report["sampling_replay_logprob_difference"] = abs(float(replay_logp - behavior))
        report["adapter_roundtrip_and_replay_passed"] = (
            report["adapter_roundtrip_exact"] and report["sampling_replay_logprob_difference"] < 0.05
        )
    (root / f"synthetic-npu-rank-{rank}-tokens-{args.tokens}.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
