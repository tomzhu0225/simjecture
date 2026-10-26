"""Qualified base/continued-SFT comparison, with detailed adapter diagnostics."""
from pathlib import Path
import contextlib
import copy
import hashlib
import json
import sys
import time
import traceback

ROOT = Path('/content/science-attention')
SOURCE = ROOT / 'parked-source-f689353'
sys.path.insert(0, str(SOURCE / 'packages/simjecture-monitor/src'))
OUT = ROOT / 'primary3-score-output'
OUT.mkdir(exist_ok=False)
status = dict(stage='waiting_for_preparation', started_at=time.time(), scored=0, errors=0)


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def put(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2)); temporary.replace(path)


def save():
    put(OUT / 'STATUS.json', status)


def deadline():
    return read(ROOT / 'primary3-lease.json')['stop_by']


save()
try:
    while time.time() < deadline() - 150:
        path = ROOT / 'primary3-prepare-status.json'
        if path.exists():
            prep = read(path)
            if prep['stage'] == 'failed':
                raise RuntimeError('Preparation failed')
            if prep['stage'] == 'ready':
                break
        time.sleep(3)
    else:
        raise TimeoutError('No scoring interval remains after restoration')
    plan = read(ROOT / 'primary3-score-plan.json')
    for name, expected in plan['inputs_sha256'].items():
        assert sha(ROOT / name) == expected
    for name, expected in plan['source_files_sha256'].items():
        assert sha(SOURCE / name) == expected
    assert sha(Path(__file__)) == plan['scorer_sha256']
    rows = read(ROOT / 'primary3-score-rows.json')
    probes = read(ROOT / 'primary3-score-probes.json')
    warm_rows = read(ROOT / 'primary3-score-warm-rows.json')
    adapter = ROOT / 'validation-assets/continued_sft/adapter'
    assert len(rows) == 24 and len(probes) == 2
    assert {name: sha(adapter / name) for name in ['adapter_config.json', 'adapter_model.safetensors']} == plan['adapter_hashes']
    import torch
    from peft import PeftModel, get_peft_model_state_dict
    from safetensors.torch import load_file
    from simjecture_monitor.decision_interface import encode_request
    from simjecture_monitor.decision_model import DecisionModel
    assert 'A100' in torch.cuda.get_device_name(0)
    status.update(stage='loading_base', gpu=torch.cuda.get_device_name(0)); save()
    model = DecisionModel(prep['base'], max_tokens=8192, kernel_profile='fla-prefill')
    model.temperature = 1.0
    identity = copy.deepcopy(model.identity)
    for row in warm_rows:
        model.predict(row)
    before = model.predict(probes[0]['row'])
    put(OUT / 'BASE_BEFORE_ADAPTER.json', before)
    status['stage'] = 'loading_single_sft_adapter'; save()
    model.model = PeftModel.from_pretrained(model.model, str(adapter)).eval()
    model.identity['adapter_files_sha256'] = plan['adapter_hashes']

    def tensor_audit(name):
        actual = get_peft_model_state_dict(model.model, adapter_name=name, save_embedding_layers=False)
        saved = load_file(str(adapter / 'adapter_model.safetensors'))
        missing = sorted(set(saved) - set(actual))
        extra = sorted(set(actual) - set(saved))
        differences = {
            key: float((actual[key].detach().cpu().float() - saved[key].float()).abs().max())
            for key in set(saved) & set(actual)
        }
        return dict(adapter_name=name, missing=missing, extra=extra,
                    maximum_tensor_difference=max(differences.values(), default=None),
                    tensors=len(differences), dtypes=sorted({str(v.dtype) for v in actual.values()}))

    loaded = tensor_audit('default')
    put(OUT / 'DEFAULT_ADAPTER_TENSORS.json', loaded)
    if loaded['missing'] or loaded['extra'] or loaded['maximum_tensor_difference'] != 0:
        raise RuntimeError('Loaded adapter tensors differ from the saved checkpoint')
    with model.model.disable_adapter():
        after = model.predict(probes[0]['row'])
    base_error = max(abs(value-after['probabilities'][field][key])
                     for field, values in before['probabilities'].items() for key, value in values.items())
    put(OUT / 'BASE_AFTER_ADAPTER.json', dict(prediction=after, maximum_probability_error=base_error))
    if base_error > 1e-4:
        raise RuntimeError('Disabled adapter changed the unadapted base predictions')

    def probe(index, prefix, *, enforce):
        item = probes[index]
        prediction = model.predict(item['row'])
        reference = item['reference']
        if prediction['prompt_sha256'] != reference['prompt_sha256']:
            raise ValueError('Probe input hash changed')
        converted = {}
        errors = {}
        for field, values in reference['probabilities'].items():
            scaled = {k: v ** reference['temperature'] for k, v in values.items()}
            total = sum(scaled.values()); converted[field] = {k: v/total for k,v in scaled.items()}
            errors[field] = max(abs(value-prediction['probabilities'][field][key])
                                for key,value in converted[field].items())
        result = dict(index=index, prefix=prefix, prediction=prediction, reference=reference,
                      expected_at_temperature_one=converted, field_errors=errors,
                      maximum_probability_error=max(errors.values()),
                      active_adapter=model.model.active_adapter)
        put(OUT / f'{prefix}-probe-{index}.json', result)
        if enforce and result['maximum_probability_error'] > 1e-4:
            raise RuntimeError(f'{prefix} probe {index} error {result["maximum_probability_error"]}')
        return {k: result[k] for k in ['index','prefix','field_errors','maximum_probability_error','active_adapter']}

    status['stage'] = 'qualifying'; save()
    probe(0, 'first-adapted', enforce=False)
    for row in warm_rows:
        model.predict(row)
    qualified = []
    for index in range(2):
        qualified.append(probe(index, 'qualified', enforce=True))
        status['qualification'] = qualified; save()
    status['stage'] = 'scoring'; save()
    with (OUT / 'predictions.jsonl').open('w') as stream:
        for policy in ['base', 'continued_sft']:
            model.model.set_adapter('default'); model.model.eval()
            model.identity = copy.deepcopy(identity)
            model.identity['adapter_files_sha256'] = {} if policy == 'base' else plan['adapter_hashes']
            for row in rows:
                if time.time() >= deadline() - 60:
                    raise TimeoutError('Scoring reached its resource lease')
                record = dict(id=row['id'], policy=policy, adapter_active=policy!='base', started_at=time.time())
                try:
                    encoded = encode_request(row, model.tokenizer, maximum_tokens=1000000)
                    record.update(input_tokens=len(encoded['input_ids']), prompt_sha256=encoded['prompt_sha256'])
                    if record['input_tokens'] > 8192:
                        raise ValueError('Full input exceeds the frozen limit')
                    with model.model.disable_adapter() if policy == 'base' else contextlib.nullcontext():
                        prediction = model.predict(row)
                    record.update(status='completed', prediction=prediction)
                except Exception as error:
                    record.update(status='failed', error_type=type(error).__name__, error=str(error)); status['errors'] += 1
                record['ended_at'] = time.time(); stream.write(json.dumps(record)+'\n'); stream.flush()
                status['scored'] += 1; save()
    model.identity['adapter_files_sha256'] = plan['adapter_hashes']
    status['final_qualification'] = [probe(i, 'after-scoring', enforce=True) for i in range(2)]
    status['primary3_validated'] = True; save()
    # A duplicate named adapter tests load/selection equivalence after the
    # primary3 comparison is complete. These are diagnostics, not extra scores.
    if time.time() < deadline() - 120:
        status['stage'] = 'diagnosing_named_adapter'; save()
        try:
            model.model.load_adapter(str(adapter), adapter_name='continued_sft', is_trainable=False)
            put(OUT / 'NAMED_ADAPTER_TENSORS.json', tensor_audit('continued_sft'))
            model.model.set_adapter('continued_sft'); model.model.eval()
            status['named_adapter_diagnostics'] = [probe(i, 'named-copy', enforce=False) for i in range(2)]
        except Exception as error:
            status.update(diagnostic_error_type=type(error).__name__, diagnostic_error=traceback.format_exc())
    status.update(stage='completed', ended_at=time.time(), optimizer_updates=0,
                  peak_cuda_bytes=torch.cuda.max_memory_allocated())
except Exception as error:
    status.update(stage='failed', ended_at=time.time(), error_type=type(error).__name__, error=traceback.format_exc())
finally:
    save()
