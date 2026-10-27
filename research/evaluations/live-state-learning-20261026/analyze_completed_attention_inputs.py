"""Describe the completed frozen cohort's public input and dispatch receipts.

No new inference, training, adjudication or threshold selection is performed.
Only stored public model observations and their recorded predictions are read.
"""
from pathlib import Path
import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import json
import statistics


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def distribution(values):
    return dict(count=len(values), minimum=min(values), median=statistics.median(values),
                mean=statistics.mean(values), maximum=max(values)) if values else dict(count=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    summary_path = root / 'r11-combined-summary.json'
    primary = read(summary_path)['primary_all_attempts']
    assert primary['complete_design'] and primary['started'] == primary['planned'] == 64
    assert not primary['audit_violations'] and not primary['unstarted']
    record_paths = [root / 'rep2-audit/records.json', root / 'r11-all-continuation-records/audit/records.json']
    records = sum((read(p) for p in record_paths), [])
    assert len(records) == len({v['id'] for v in records}) == 64
    interface = root / 'replication-source-04f905c/packages/simjecture-monitor/src/simjecture_monitor/decision_interface.py'
    tree = ast.parse(interface.read_text())
    routes = next(ast.literal_eval(node.value) for node in tree.body
                  if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ROUTES' for t in node.targets))
    experts = {'request_worker_help', 'wake_director', 'request_repair_judge'}
    rows, episodes, inputs = [], [], {str(p.relative_to(root)): sha(p) for p in record_paths + [summary_path, interface]}
    for record in records:
        candidates = [p for p in root.glob('base-sft-replication-v*')
                      if (p / record['id']).is_dir() or (p / (record['id'] + '-receipt.json')).is_file()]
        assert len(candidates) == 1, record['id']
        trial = candidates[0] / record['id']
        dispatched = set()
        path = trial / 'monitor/attention-dispatches.jsonl'
        if path.exists():
            inputs[str(path.relative_to(root))] = sha(path)
            for line in path.read_text().splitlines():
                event = json.loads(line)
                if event.get('dispatched'):
                    dispatched.add(event['packet_id'])
        own = []
        for path in sorted((trial / 'monitor').glob('attention-[0-9]*.json')):
            packet = read(path)
            submitted, result = packet['submitted'], packet['result']
            prediction = result.get('prediction', {})
            by_role = Counter()
            exact_duplicate_chars = 0
            seen = set()
            for evidence in submitted['evidence']:
                content = evidence['content']
                role = evidence['source_role']
                category = 'worker_events' if role.startswith('worker_event_') else 'diagnostics' if role.startswith('diagnostic_') else role
                by_role[category] += len(content)
                if content in seen:
                    exact_duplicate_chars += len(content)
                seen.add(content)
            route_probs = prediction.get('probabilities', {}).get('route', {})
            route_answer = prediction.get('answers', {}).get('route')
            if route_probs:
                assert set(route_probs) <= set(routes)
                assert abs(sum(route_probs.values()) - 1) < 1e-5
            row = dict(episode_id=record['id'], family=record['family'], arm=record['arm'],
                       quiet_family_proxy=record['quiet_family'], receipt=str(path.relative_to(root)),
                       packet_id=submitted['packet_id'], input_tokens=prediction.get('input_tokens'),
                       scoring_seconds=prediction.get('total_seconds'),
                       model_view_chars=len(result['view']['text']), evidence_chars=sum(by_role.values()),
                       evidence_chars_by_role=dict(by_role), exact_duplicate_evidence_chars=exact_duplicate_chars,
                       proposal=result['decision']['action'], selected_route=route_answer,
                       selected_route_probability=route_probs.get(route_answer),
                       expert_route_probability=sum(p for label, p in route_probs.items() if routes[label][0] in experts) if route_probs else None,
                       admission=packet['admission']['disposition'],
                       actual_dispatch=submitted['packet_id'] in dispatched)
            inputs[str(path.relative_to(root))] = sha(path)
            own.append(row)
            rows.append(row)
        assert sum(v['actual_dispatch'] for v in own) == len(dispatched), record['id']
        episodes.append(dict(id=record['id'], family=record['family'], arm=record['arm'],
                             verified=record['whole_workflow_verified'], quiet_family_proxy=record['quiet_family'],
                             automatic_alerts=record['automatic_alerts'], observations=len(own),
                             input_tokens=distribution([v['input_tokens'] for v in own if v['input_tokens'] is not None])))

    grouped = defaultdict(list)
    for row in rows:
        grouped[row['arm']].append(row)
    by_arm = {}
    for arm, values in grouped.items():
        roles = Counter()
        for value in values:
            roles.update(value['evidence_chars_by_role'])
        total = sum(roles.values())
        by_arm[arm] = dict(
            observations=len(values), input_tokens=distribution([v['input_tokens'] for v in values if v['input_tokens'] is not None]),
            scoring_seconds=distribution([v['scoring_seconds'] for v in values if v['scoring_seconds'] is not None]),
            evidence_character_shares={key: amount / total for key, amount in roles.most_common()} if total else {},
            actual_dispatches=sum(v['actual_dispatch'] for v in values),
            quiet_dispatch_receipts=[v for v in values if v['actual_dispatch'] and v['quiet_family_proxy']],
        )
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'observations.jsonl').write_text(''.join(json.dumps(v) + '\n' for v in rows))
    (args.output / 'episodes.json').write_text(json.dumps(episodes, indent=2) + '\n')
    (args.output / 'inputs-sha256.json').write_text(json.dumps(inputs, indent=2) + '\n')
    result = dict(
        scope='Descriptive analysis of completed frozen evaluation receipts; no new model calls or optimizer updates',
        episodes=len(episodes), observations=len(rows), by_arm=by_arm,
        evidence_size_unit='Unicode characters, not token allocations; full input token counts come from stored model receipts',
        limitations=['Repeated polls are correlated, not independent episodes.',
                     'Quiet-family labels are only an interruption proxy, not independent false-alert adjudication.',
                     'Model option probabilities are not calibrated incident probabilities.',
                     'This analysis selects no threshold and measures no compressed-input model performance.'],
    )
    (args.output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
