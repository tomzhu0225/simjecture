"""Validate the optional CUDA convolution against the installed reference path."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from simjecture_monitor.events import put
from simjecture_monitor.kernels import enable_fla_prefill


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Retain existing validation outputs")
    import torch
    from transformers.models.qwen3_5 import modeling_qwen3_5 as qwen

    torch.set_num_threads(2)
    torch.manual_seed(20261024)
    torch.cuda.set_per_process_memory_fraction(0.05)
    torch.backends.cudnn.allow_tf32 = False
    original = qwen.causal_conv1d_fn
    identity = enable_fla_prefill()
    rows = []
    for dtype in [torch.float32, torch.bfloat16]:
        for tokens in [127, 512]:
            for activation in [None, "silu"]:
                for use_bias in [False, True]:
                    x = torch.randn(2, 128, tokens, device="cuda", dtype=dtype)
                    weight = torch.randn(128, 4, device="cuda", dtype=dtype)
                    bias = torch.randn(128, device="cuda", dtype=dtype) if use_bias else None
                    with torch.inference_mode():
                        expected = original(x, weight, bias, activation=activation)
                        actual = qwen.causal_conv1d_fn(x, weight, bias, activation=activation)
                    tolerance = 0.03 if dtype == torch.bfloat16 else 1e-5
                    torch.testing.assert_close(actual, expected, atol=tolerance, rtol=tolerance)
                    assert torch.isfinite(actual).all()
                    rows.append(
                        dict(
                            dtype=str(dtype),
                            tokens=tokens,
                            activation=activation,
                            bias=use_bias,
                            maximum_absolute_error=float((actual - expected).abs().max()),
                        )
                    )
    try:
        qwen.causal_conv1d_fn(x, weight, cu_seqlens=torch.tensor([0, 127], device="cuda"))
    except ValueError:
        rejected_packed = True
    else:
        raise AssertionError("Packed inputs were silently accepted")
    put(
        args.output,
        dict(
            runtime=identity, checks=rows, packed_rejected=rejected_packed, completed_at=time.time()
        ),
    )


if __name__ == "__main__":
    main()
