"""Aggregate disjoint continuation receipts, then run the unchanged registered analysis."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path('/home/simjecture/investigations/scientific-attention-20261025')


def aggregate(phases, output):
    records, failures, provider_failures, violations, inputs = [], [], [], [], {}
    for audit, campaign in phases:
        for path in [audit / 'records.json', audit / 'summary.json', campaign / 'CAMPAIGN.json']:
            inputs[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        records.extend(json.loads((audit / 'records.json').read_text()))
        violations.extend(json.loads((audit / 'summary.json').read_text())['violations'])
        value = json.loads((campaign / 'CAMPAIGN.json').read_text())
        assert value['stage'] in ['completed', 'failed']
        failures.extend(value.get('infrastructure_failures', []))
        provider_failures.extend(value.get('preserved_initial_provider_failures', []))
    ids = [row['id'] for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError('An attempted assignment appears in more than one phase')
    output.mkdir(exist_ok=False)
    audit, campaign = output / 'audit', output / 'bookkeeping'
    audit.mkdir(); campaign.mkdir()
    (audit / 'records.json').write_text(json.dumps(records, indent=2))
    (audit / 'summary.json').write_text(json.dumps(dict(violations=violations), indent=2))
    (campaign / 'CAMPAIGN.json').write_text(json.dumps(dict(
        stage='completed', infrastructure_failures=failures,
        preserved_initial_provider_failures=provider_failures,
        scope='Aggregate bookkeeping only; no new actors or scientific outcomes'), indent=2))
    (output / 'provenance.json').write_text(json.dumps(dict(inputs_sha256=inputs, records=len(records)), indent=2))
    return audit, campaign


def main():
    audit, campaign = aggregate([
        (ROOT / 'r7-audit', ROOT / 'base-sft-replication-v3'),
        (ROOT / 'r8-audit', ROOT / 'base-sft-replication-v4'),
    ], ROOT / 'r8-all-continuation-records')
    subprocess.run([sys.executable, str(ROOT / 'combine_base_sft_phases.py'),
                    '--root', str(ROOT), '--new-audit', str(audit),
                    '--new-campaign', str(campaign),
                    '--output', str(ROOT / 'r8-combined-summary.json')], check=True)


if __name__ == '__main__':
    main()
