import json
from pathlib import Path
for name in ('prior_campaign_0003_audit_summary.json', 'prior_campaign_audit_summary.json', 'prior_campaign_0002_audit_summary.json'):
    data = json.loads(Path('guided', name).read_text())
    print('='*20, name, '='*20)
    print(json.dumps(data, indent=2)[:6500])
print('='*20, 'GUIDED DIAGNOSTIC SECTION', '='*20)
lines = Path('guided/gem_collisionless.py').read_text().splitlines()
for i in range(505, 565):
    print(f'{i+1:4d}: {lines[i]}')