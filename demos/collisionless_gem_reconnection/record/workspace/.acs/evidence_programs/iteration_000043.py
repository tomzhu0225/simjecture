from pathlib import Path
lines = Path('guided/gem_collisionless.py').read_text().splitlines()
for i in range(58, 119):
    print(f'{i+1:4d}: {lines[i]}')
(campaign_sums := Path('campaign/summaries')).mkdir(parents=True, exist_ok=True)
for label in ['p16_t1_s20260902','p16_t1_s20260903','p16_t1_s20260904','p16_t20_s20260902','p16_t20_s20260903','p16_t20_s20260904','p8_t1_s20260902','p8_t1_s20260903','p8_t1_s20260904','p8_t20_s20260902','p8_t20_s20260903','p8_t20_s20260904']:
    Path(f'campaign/run_{label}').mkdir(parents=True, exist_ok=True)
print('campaign dirs ready')