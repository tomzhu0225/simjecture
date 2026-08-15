import json, hashlib, subprocess, sys
from pathlib import Path
# regenerate fixtures
subprocess.run([sys.executable, 'gen_fixtures.py'], check=True)
# verify energy reader hash
pinned = '1b4d05ae6842b21255d1a6cc56b53aa6a2eecf508520966cca5d694bb48b366b'
actual = hashlib.sha256(Path('energy_reader.py').read_bytes()).hexdigest()
print('energy_reader_hash_match:', actual == pinned)
print('energy_reader_sha256:', actual)
# run analyzer on fixtures via plain python (workbench smoke)
subprocess.run([sys.executable, 'analyze_ensemble.py', '--manifest', 'fixtures/commission_manifest.json', '--output', 'fixtures/commission_output_wb.json'], check=True)