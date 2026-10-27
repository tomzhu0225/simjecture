"""Fresh portable-adapter load after timed collection has stopped; A100 only."""
from pathlib import Path
import hashlib
import json
import os
import signal
import sys
import time
import traceback

ROOT = Path('/content/science-attention')
RUN = ROOT / 'portable-qualification-r7'
payload = json.loads((RUN / 'input.json').read_text())
status = dict(stage='starting', pid=os.getpid(), started_at=time.time(), optimizer_updates=0)


def save():
    p = RUN / 'STATUS.tmp'
    p.write_text(json.dumps(status, indent=2))
    p.replace(RUN / 'STATUS.json')


def stop(signum, frame):
    raise TimeoutError('Bounded portable qualification ended')


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


save()
signal.signal(signal.SIGALRM, stop)
signal.alarm(max(1, min(300, int(payload['deadline'] - time.time()))))
try:
    sys.path.insert(0, str(ROOT / 'replication-source-04f905c/packages/simjecture-monitor/src'))
    from simjecture_monitor.decision_model import DecisionModel
    from simjecture_monitor.attention_server import AttentionService
    import torch
    from peft import get_peft_model_state_dict
    from safetensors import safe_open

    original = ROOT / 'validation-assets/continued_sft/adapter/adapter_model.safetensors'
    adapter = RUN / 'adapter'
    adapter.mkdir()
    assert sha(original) == payload['weights_sha256']
    os.link(original, adapter / original.name)
    (adapter / 'adapter_config.json').write_text(payload['portable_config'])
    assert sha(adapter / 'adapter_config.json') == payload['config_sha256']
    free, total = torch.cuda.mem_get_info()
    assert free > 20 * 1024**3, 'Insufficient free memory for an isolated fresh load'
    status.update(stage='loading', gpu_free_before=free, gpu_total=total)
    save()
    preparation = json.loads((ROOT / 'r7-prepare-status.json').read_text())
    model = DecisionModel(preparation['base'], adapter=adapter, max_tokens=8192,
                          kernel_profile='fla-prefill')
    model.temperature = 1.0
    state = get_peft_model_state_dict(model.model)
    elements = 0
    with safe_open(adapter / original.name, framework='pt', device='cpu') as stored:
        assert set(state) == set(stored.keys()), 'Loaded adapter tensor names changed'
        for name in stored.keys():
            tensor = stored.get_tensor(name)
            actual = state[name].detach().cpu()
            assert actual.dtype == tensor.dtype and torch.equal(actual, tensor), name
            elements += tensor.numel()
    status.update(stage='probing', tensor_count=len(state), adapter_elements=elements,
                  model_identity=model.identity)
    save()
    service = AttentionService(model, adapter_loaded=True, maximum_tokens=8192)
    probes = []
    for probe in payload['probes']:
        policy = 'base' if probe['policy'] == 'base' else 'adapted'
        result = service.predict(dict(observation=probe['observation'], policy=policy))
        reference = probe['reference']
        errors = []
        for field, values in reference['probabilities'].items():
            converted = {key: value**reference['temperature'] for key, value in values.items()}
            total = sum(converted.values())
            errors.extend(abs(value / total - result['prediction']['probabilities'][field][key])
                          for key, value in converted.items())
        assert result['input_prompt_sha256'] == reference['prompt_sha256']
        assert max(errors) < 1e-4, 'Portable adapter does not reproduce the saved probability probe'
        probes.append(dict(policy=probe['policy'], maximum_probability_error=max(errors),
                           reference=reference, result=result))
        (RUN / 'PROBES.json').write_text(json.dumps(probes, indent=2))
    status.update(stage='completed', ended_at=time.time(), probes=len(probes),
                  maximum_probability_error=max(row['maximum_probability_error'] for row in probes))
except Exception:
    status.update(stage='failed', ended_at=time.time(), error=traceback.format_exc())
    raise
finally:
    save()
print(json.dumps(status), flush=True)
