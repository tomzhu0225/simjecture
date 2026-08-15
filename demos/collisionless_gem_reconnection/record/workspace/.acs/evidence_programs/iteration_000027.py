from pathlib import Path
import json
lines = Path('guided/gem_collisionless.py').read_text().splitlines()
for i in range(564, 636):
    print(f'{i+1:4d}: {lines[i]}')
print('=====ANCHOR SUMMARY STRUCTURE=====')
data = json.loads(Path('guided/gem_anchor_validation.json').read_text())
print('top keys:', sorted(data.keys()))
print('checks categories:', {k: sorted(v.keys()) for k, v in data.get('checks', {}).items()})
print('derived:', {k: data.get('derived', {}).get(k) for k in ('di_m', 'dt_s', 'dt_omega_ci', 'va_upstream_over_c', 'dx_over_de', 'dz_over_de', 'dt_over_multidimensional_cfl')})
print('inputs subset:', {k: data.get('inputs', {}).get(k) for k in ('temperature_ratio_Ti_Te', 'ppc_per_population', 'seed', 'duration_omegaci', 'mass_ratio', 'steps')})
hist = data.get('observations', {}).get('history', [])
print('history length:', len(hist))
print('first history:', hist[0] if hist else None)
print('last history:', hist[-1] if hist else None)
print('runtime:', data.get('runtime', {}))
print('outputs dir?', (Path('guided/anchor_run').exists()))