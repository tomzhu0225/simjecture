"""Freeze the report and provenance for independent assessment; no simulation."""
from pathlib import Path
import json,hashlib,shutil
report=Path('RESULTS.md').read_text()
index=json.load(open('evidence_index.json'))
assert hashlib.sha256(report.encode()).hexdigest()==index['report_sha256']
shutil.copyfile('RESULTS.md','review_report.md')
Path('report_snapshot.json').write_text(json.dumps({'kind':'report_assessment_package','scientific_status':'unresolved','accepted_scientific_verdict':None,'fresh_evidence_collected':False,'report_markdown':report,'evidence_index':index,'assessment_request':'Independently assess report accuracy and sufficiency. Methods authorization and fresh commissioning do not support the root. No credible qualified counterexample and no supported original/repair are claimed. Identify any report correction and retain unresolved outcome if no decisive evidence.'},indent=2,allow_nan=False)+'\n')
