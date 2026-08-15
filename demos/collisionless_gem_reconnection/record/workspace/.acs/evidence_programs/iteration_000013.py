from pathlib import Path
lines = Path('guided/gem_collisionless.py').read_text().splitlines()
for i in range(469, 640):
    print(f'{i+1:4d}: {lines[i]}')