"""CPU-only full-input token measurements on completed, stored model receipts."""
from pathlib import Path
import argparse
from collections import defaultdict
import copy
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import resource
import statistics
import time

for key in ['USE_TORCH', 'USE_TF', 'USE_FLAX']:
    os.environ[key] = '0'
for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[key] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30))
resource.setrlimit(resource.RLIMIT_CPU, (180, 180))

from transformers import AutoTokenizer
from simjecture_monitor import attention_support as protocol
from simjecture_monitor.decision_interface import compile_messages, scientific_request


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stats(values):
    return dict(count=len(values), minimum=min(values), median=statistics.median(values),
                mean=statistics.mean(values), maximum=max(values), total=sum(values))


def expanded(text):
    value = json.loads(text.split('\nDATA\n', 1)[1])
    if 'evidence_rows' in value:
        columns = value.pop('evidence_columns')
        measurements = value.pop('measurement_columns')
        value['evidence'] = [dict(zip(columns, row, strict=True)) for row in value.pop('evidence_rows')]
        for row in value['evidence']:
            row['measurements'] = [dict(zip(measurements, m, strict=True)) for m in row['measurements']]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    assert importlib.util.find_spec('torch') is None
    root = args.root.resolve()
    assert read(root / 'r11-combined-summary.json')['primary_all_attempts']['complete_design']
    receipts = [json.loads(line) for line in (root / 'completed-input-analysis-01/observations.jsonl').read_text().splitlines()]
    receipts = [r for r in receipts if r['input_tokens'] is not None]
    assert len(receipts) == 313
    tokenizer = AutoTokenizer.from_pretrained(root / 'tokenizer-analysis-assets', local_files_only=True)
    marker = tokenizer.encode('<decision>', add_special_tokens=False)
    assert len(marker) == 1
    rows, inputs = [], {}
    status_path = root / 'input-encoding-analysis-status.json'
    for index, receipt in enumerate(receipts):
        path = (root / receipt['receipt']).resolve()
        assert path.is_relative_to(root)
        record = read(path)
        packet = protocol.Observation.model_validate(record['submitted'])
        views = {name: protocol.pack(packet, len, token_counter_id='assembly:characters',
                                    budget_tokens=1_000_000, compact=compact)
                 for name, compact in [('named', False), ('column', True)]}
        assert views['named'].text == record['result']['view']['text']
        assert views['named'].aliases == views['column'].aliases
        assert views['named'].question_aliases == views['column'].question_aliases
        assert views['named'].included_ids == views['column'].included_ids
        assert views['named'].omitted_ids == views['column'].omitted_ids
        assert expanded(views['named'].text) == expanded(views['column'].text)
        counts, hashes = {}, {}
        for name, view in views.items():
            request = scientific_request(packet, view)
            original, labels = compile_messages(request)
            for escaping in ['escaped', 'raw']:
                messages = copy.deepcopy(original)
                if escaping == 'raw':
                    quoted = json.dumps(request['state'], ensure_ascii=False, indent=2, allow_nan=False)
                    assert messages[1]['content'].count(quoted) == 1
                    messages[1]['content'] = messages[1]['content'].replace(quoted, request['state'], 1)
                rendered = tokenizer.apply_chat_template(messages, tokenize=False,
                                                        add_generation_prompt=False, enable_thinking=False)
                ids = tokenizer.encode(rendered, add_special_tokens=False)
                assert ids.count(marker[0]) == len(labels) == 5
                key = name + '_' + escaping
                counts[key] = len(ids)
                hashes[key] = hashlib.sha256(rendered.encode()).hexdigest()
        assert counts['named_escaped'] == receipt['input_tokens']
        assert hashes['named_escaped'] == record['result']['input_prompt_sha256']
        rows.append(dict(episode_id=receipt['episode_id'], arm=receipt['arm'],
                         receipt=receipt['receipt'], input_tokens=counts, prompt_sha256=hashes))
        inputs[receipt['receipt']] = sha(path)
        if index % 40 == 0:
            status_path.write_text(json.dumps(dict(stage='counting', completed=index + 1,
                                                  total=len(receipts), at=time.time())))
    profiles = {}
    for name in ['named_escaped', 'column_escaped', 'named_raw', 'column_raw']:
        tokens = [r['input_tokens'][name] for r in rows]
        base = [r['input_tokens']['named_escaped'] for r in rows]
        reductions = [1 - x / b for x, b in zip(tokens, base, strict=True)]
        profiles[name] = dict(tokens=stats(tokens), fractional_reduction=stats(reductions),
                              total_token_reduction_fraction=1 - sum(tokens) / sum(base))
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'rows.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    (args.output / 'input-hashes.json').write_text(json.dumps(inputs, indent=2) + '\n')
    value = dict(
        stage='completed', started_at=started, ended_at=time.time(), observations=len(rows),
        episodes=len({r['episode_id'] for r in rows}), baseline_prompt_hashes_reproduced=len(rows),
        baseline_token_counts_reproduced=len(rows), profiles=profiles,
        tokenizer_files_sha256={p.name: sha(p) for p in (root / 'tokenizer-analysis-assets').iterdir() if p.is_file()},
        packages={n: importlib.metadata.version(n) for n in ['transformers', 'tokenizers', 'huggingface-hub', 'pydantic']},
        compiler_source_sha256={n: sha(root / 'replication-source-04f905c/packages/simjecture-monitor/src/simjecture_monitor' / n)
                                for n in ['attention_support.py', 'attention_contract.py', 'decision_interface.py']},
        model_weights_loaded=False, gpu_calls=0, optimizer_updates=0,
        limits=dict(cpu_seconds=180, virtual_memory_bytes=4 << 30),
        scope='Token counts only; all evidence, aliases, fields and semantic data retained. Counterfactual formats are not enabled in the released model.',
        limitations=['No model prediction, accuracy, latency or intervention utility is measured.',
                     'Lossless data serialization does not imply equivalent model behavior.',
                     'Repeated observations are correlated; this is a paired descriptive size comparison.'],
    )
    (args.output / 'summary.json').write_text(json.dumps(value, indent=2) + '\n')
    status_path.write_text(json.dumps({k: value[k] for k in ['stage', 'ended_at', 'observations']}))
    print(json.dumps(value), flush=True)


if __name__ == '__main__':
    main()
