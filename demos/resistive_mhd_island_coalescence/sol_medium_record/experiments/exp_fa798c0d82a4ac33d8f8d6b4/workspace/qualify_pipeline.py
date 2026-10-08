import json,copy
from pathlib import Path
import study_analysis as s
parents=['exp_22b4b0e7c2fcdc0417ce7387','exp_45fced4d67b6d6b304622ac3']
base={'experiment':parents[0],'json':'cfl08.json','stage':'exploration'};fine={'experiment':parents[1],'json':'refine384.json','raw':'qualify_raw.npz','stage':'exploration'}
def run(entries):
 Path('manifest.json').write_text(json.dumps(entries));s.main('manifest.json');return json.loads(Path('analysis.json').read_text())
missing=run([base]);assert not missing['cases'][0]['eligible'] and missing['cases'][0]['log_margin'] is None
bad=json.loads(Path('refine384.json').read_text());bad['window']['min_sheet_fwhm_cells']=2;Path('bad_refine.json').write_text(json.dumps(bad));invalid=run([base,{**fine,'json':'bad_refine.json'}]);assert not any(r['eligible'] for r in invalid['cases'])
truncated=json.loads(Path('cfl08.json').read_text());truncated['timeseries']=truncated['timeseries'][:5];Path('truncated.json').write_text(json.dumps(truncated));censored=run([{**base,'json':'truncated.json'},fine]);assert censored['cases'][0]['rate'] is None and not any(r['eligible'] for r in censored['cases'])
valid=run([base,fine]);assert all(r['eligible'] for r in valid['cases']);assert all(r['crossing_bracket_rate_bounds']['rate_bounds'][0]<=r['rate']<=r['crossing_bracket_rate_bounds']['rate_bounds'][1] for r in valid['cases'])
Path('pipeline_qualification.json').write_text(json.dumps({'parents':parents,'valid_cases':valid['cases'],'qualified_gap':valid['matched_log_rate_differences'],'missing_refinement':missing['cases'],'ineligible_refinement':invalid['cases'],'censored':censored['cases'],'checks':{'matched_pair_qualified':True,'missing_refinement_unresolved':True,'ineligible_refinement_unresolved':True,'missing_window_and_variants_explicit':True,'brackets_enclose_interpolated_rate':True},'figure_stage':'exploration','scope':'Implementation qualification with actual recorded commissioning fields; synthetic modifications test failure paths only, not physical evidence.'},indent=2))
