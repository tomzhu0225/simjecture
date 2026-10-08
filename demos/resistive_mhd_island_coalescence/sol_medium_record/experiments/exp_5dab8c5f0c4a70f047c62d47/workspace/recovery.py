"""Recover diagnostics from frozen stage-evidence FLASH fields; never evolve."""
import json,sys,hashlib
from pathlib import Path
import calculation
if '--report' in sys.argv:
 import study_analysis
 study_analysis.main(sys.argv[sys.argv.index('--report')+1])
else:
 origin=json.loads(Path('origin.json').read_text())
 if origin['stage']!='evidence':raise ValueError('Recovery cannot promote exploratory evolution')
 calculation.main()
 d=json.loads(Path('result.json').read_text())
 if d['provenance']['parameter_sha256']!=origin['parameter_sha256']:raise ValueError('Original parameter identity mismatch')
 if d['provenance']['hdf5_hashes']!=origin['hdf5_hashes']:raise ValueError('Preserved field identity mismatch')
 d['recovery']={'parent_experiment':origin['experiment'],'parent_stage':origin['stage'],'parent_execution_status':'timed_out','new_evolution':False,'evolution_target_reached':d['actual_end']>=d['realized']['tmax'],'processing_completed':True,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':'Same predeclared complete flux window from preserved evidence-stage parent; timeout retained. No continuation or exploratory-data promotion.'}
 Path('result.json').write_text(json.dumps(d,indent=2,allow_nan=False))
