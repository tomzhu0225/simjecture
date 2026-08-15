import json
from pathlib import Path
data = json.loads(Path('guided/gem_anchor_validation.json').read_text())
def shape(obj, prefix='', depth=0, maxdepth=3):
    if depth > maxdepth:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            print('  '*depth + f'{prefix}{k}: {type(v).__name__}' + (f' (len {len(v)})' if isinstance(v, (list, dict)) else f' = {v!r}'))
            if isinstance(v, dict):
                shape(v, prefix='', depth=depth+1, maxdepth=maxdepth)
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                shape(v[0], prefix=f'[0].', depth=depth+1, maxdepth=maxdepth)
shape(data)
print('--- runtime ---')
print(json.dumps(data.get('runtime'), indent=1))
print('--- inputs ---')
print(json.dumps(data.get('inputs'), indent=1))
print('--- derived ---')
print(json.dumps(data.get('derived'), indent=1))