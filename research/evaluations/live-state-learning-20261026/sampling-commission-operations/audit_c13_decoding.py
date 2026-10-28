"""Decode retained probabilities; never rerun a model or scientific workflow."""
from pathlib import Path
import sys, json, hashlib, time
r = Path('/home/simjecture/investigations/scientific-attention-20261025')
sys.path.insert(0, str(r / 'workflow-return-source-171ac44/packages/simjecture-monitor/src'))
from simjecture_monitor.action_distribution import choose, CONTRACT, INDEPENDENT, factors
c = r / 'parked-commission-c12'
plan = json.loads((c / 'PLAN.json').read_text())
rows = []
for block in plan['blocks']:
    for trial in block['trials']:
        if trial['role'] != 'sampled':
            continue
        for p in sorted((c / trial['id'] / 'monitor').glob('attention-*.json')):
            d = json.loads(p.read_text()); v = d['result']
            prob = v['prediction']['probabilities']
            constrained, _ = choose(prob, distribution=CONTRACT)
            independent, _ = choose(prob, distribution=INDEPENDENT)
            factor = factors(prob, CONTRACT)[0]
            mass = {route: sum(x for cand, x in zip(factor['candidates'], factor['probabilities'], strict=True) if cand[0] == route) for route in prob['route']}
            rows.append(dict(family=block['family'], episode=trial['id'], receipt=str(p.relative_to(c)), sha256=hashlib.sha256(p.read_bytes()).hexdigest(), sampled=v['decision_answers'], constrained_greedy=constrained, independent_greedy=independent, constrained_route_probabilities=mass, input_tokens=v['prediction']['input_tokens'], scoring_seconds=v['prediction']['total_seconds']))
print(json.dumps(dict(at=time.time(), rows=rows, scope='Offline decoding of identical stored probabilities. No new inference, changed dispatch, counterfactual workflow or optimizer update.')))
