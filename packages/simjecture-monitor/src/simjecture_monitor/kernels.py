"""Optional FLA prefill convolution for the single-pass CUDA monitor.

Enable explicitly in an isolated model environment. This changes floating-point
execution, not weights; behavior probabilities must be logged on that runtime.
Cached generation and packed training are outside this profile's contract.
"""

from __future__ import annotations


def enable_fla_prefill():
    import hashlib
    import importlib.metadata
    import inspect
    from pathlib import Path

    from fla.modules.causal_conv1d import causal_conv1d
    from torch.nn import functional as F
    from transformers.models.qwen3_5 import modeling_qwen3_5

    def prefill(hidden_states, weight, bias=None, activation=None, **kwargs):
        if any(kwargs.get(key) is not None for key in ["cu_seqlens", "cu_seq_lens_q", "seq_idx"]):
            raise ValueError("FLA monitor prefill profile does not accept packed sequences")
        if activation not in {None, "silu", "swish"}:
            raise ValueError("Unsupported FLA prefill activation")
        output, _ = causal_conv1d(
            hidden_states.to(weight.dtype).transpose(1, 2),
            weight=weight,
            bias=bias,
            activation=None,
            output_final_state=False,
            backend="triton",
        )
        # Keep the reference rounding boundary before SiLU instead of fusing
        # activation into the convolution's higher-precision accumulator.
        if activation is not None:
            output = F.silu(output)
        return output.transpose(1, 2).to(hidden_states.dtype)

    modeling_qwen3_5.causal_conv1d_fn = prefill
    source = Path(inspect.getsourcefile(enable_fla_prefill))
    return dict(
        profile="fla-prefill",
        fla_core=importlib.metadata.version("fla-core"),
        adapter_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        convolution="fla.modules.causal_conv1d:causal_conv1d; BCT/BTC layout adapter",
        scope="Dense single-pass CUDA prefill, use_cache=False; no packed sequences",
    )
