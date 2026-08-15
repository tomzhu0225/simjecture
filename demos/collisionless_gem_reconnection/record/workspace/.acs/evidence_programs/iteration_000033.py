from pathlib import Path
import json
lines = Path('guided/gem_collisionless.py').read_text().splitlines()
for i in range(729, len(lines)):
    print(f'{i+1:4d}: {lines[i]}')
print('=====ANCHOR OUTPUT SCHEMA (non-evidentiary)=====')
root = Path('guided/anchor_run')
if root.exists():
    for p in sorted(root.rglob('*'))[:20]:
        print('exists', p)
else:
    print('anchor_run dir absent (as shown earlier)')