from pathlib import Path
lines = Path('guided/gem_collisionless.py').read_text().splitlines()
for i in range(119, 300):
    print(f'{i+1:4d}: {lines[i]}')