from pathlib import Path
src = Path('guided/gem_collisionless.py').read_text()
lines = src.splitlines()
print('total lines', len(lines))
for i in range(300, 470):
    print(f'{i+1:4d}: {lines[i]}')