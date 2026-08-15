from pathlib import Path
lines = Path('guided/gem_collisionless.py').read_text().splitlines()
for i in range(564, 637):
    print(f'{i+1:4d}: {lines[i]}')