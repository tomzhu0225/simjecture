"""Combine disjoint attempts without replacing failed trials; retain sensitivity."""
from pathlib import Path
import argparse,hashlib,json,sys
from summarize_base_sft_rep2 import summarize

def read(path):return json.loads(Path(path).read_text())
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--new-audit',type=Path,required=True);p.add_argument('--new-campaign',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 original=read(a.root/'base-sft-replication-manifest.json');records=read(a.root/'rep2-audit/records.json')+read(a.new_audit/'records.json')
 violations=read(a.root/'rep2-audit/summary.json')['violations']+read(a.new_audit/'summary.json')['violations']
 ids=[r['id'] for r in records];assert len(ids)==len(set(ids)),'An attempted trial was replaced or duplicated'
 bad_blocks=set();id_to_block={t['id']:b['id'] for b in original['blocks'] for t in b['trials']}
 for path in [a.root/'base-sft-replication-v2/CAMPAIGN.json',a.new_campaign/'CAMPAIGN.json']:
  phase=read(path)
  for failure in phase.get('infrastructure_failures',[])+phase.get('preserved_initial_provider_failures',[]):
   if failure.get('id') in id_to_block:bad_blocks.add(id_to_block[failure['id']])
 primary=summarize(original,records,violations)
 clean=original|dict(blocks=[b for b in original['blocks'] if b['id'] not in bad_blocks])
 clean['workflows']=sum(len(b['trials']) for b in clean['blocks'])
 sensitivity=summarize(clean,[r for r in records if r['block'] not in bad_blocks],violations)
 result=dict(primary_all_attempts=primary,clean_block_sensitivity=sensitivity,excluded_blocks=sorted(bad_blocks),original_manifest_sha256=hashlib.sha256((a.root/'base-sft-replication-manifest.json').read_bytes()).hexdigest(),record_hashes={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in [a.root/'rep2-audit/records.json',a.new_audit/'records.json']},scope='Original outcomes retained, including provider failures; the sensitivity removes whole affected blocks and is conditional, not a replacement primary analysis')
 with a.output.open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(dict(total_started=primary['started'],complete_design=primary['complete_design'],excluded_blocks=sorted(bad_blocks),arms=primary['arms'])))
if __name__=='__main__':main()
