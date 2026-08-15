from pathlib import Path
lines = Path('guided/gem_collisionless.py').read_text().splitlines()
for rng in [(0,119),(473,570)]:
    for i in range(rng[0], rng[1]):
        print(f'{i+1:4d}: {lines[i]}')
    print('---')