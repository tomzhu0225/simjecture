"""Registered paired analysis of the repeated base/SFT scientific workflows."""
from pathlib import Path
from collections import defaultdict
import argparse,hashlib,json,math,random,statistics

def mean(values):
 return statistics.mean(values) if values else None

def contrast(records,learned,baseline,metric,confidence,draws=10000,seed=202610261338):
 blocks=defaultdict(dict)
 for row in records:
  if row['arm'] in blocks[row['block']]:raise ValueError('Duplicate block/arm')
  blocks[row['block']][row['arm']]=row
 families=defaultdict(list)
 paired=[]
 for block_id,block in blocks.items():
  if learned not in block or baseline not in block:continue
  a,b=block[learned],block[baseline]
  assert a['family']==b['family'] and a['seed']==b['seed'] and a['repeat']==b['repeat']
  difference=a[metric]-b[metric];families[a['family']].append(difference)
  paired.append(dict(block=block_id,family=a['family'],repeat=a['repeat'],difference=difference))
 if not paired:return dict(pairs=0,difference=None,interval=None)
 groups=list(families.values());rng=random.Random(seed);samples=[]
 for _ in range(draws):
  sampled=rng.choices(groups,k=len(groups))
  samples.append(statistics.mean(statistics.mean(rng.choices(g,k=len(g))) for g in sampled))
 samples.sort();tail=(1-confidence)/2
 return dict(pairs=len(paired),family_clusters=len(groups),difference=statistics.mean(statistics.mean(g) for g in groups),interval=[samples[int(draws*tail)],samples[min(draws-1,math.ceil(draws*(1-tail))-1)]],confidence=confidence,replicates=draws,seed=seed,cluster_unit='mechanism family, then repetitions within family',paired_differences=paired)

def summarize(manifest,records,violations):
 planned={t['id']:(b,t) for b in manifest['blocks'] for t in b['trials']}
 assert len(planned)==manifest['workflows']
 seen=set();rows=[]
 for record in records:
  assert record['id'] in planned and record['id'] not in seen
  seen.add(record['id']);block,assignment=planned[record['id']]
  for field in ['arm','family','seed','repeat']:assert record[field]==assignment[field]
  assert record['block']==block['id']
  row=dict(record)
  if row['whole_workflow_verified']:
   assert math.isfinite(row['elapsed_seconds']) and row['elapsed_seconds']>=0
   row['restricted_completion_seconds']=min(650.0,row['elapsed_seconds'])
  else:row['restricted_completion_seconds']=650.0
  rows.append(row)
 arms={}
 for arm in manifest['arms']:
  subset=[r for r in rows if r['arm']==arm];quiet=[r for r in subset if r['quiet_family']]
  arms[arm]=dict(planned=sum(t['arm']==arm for _,t in planned.values()),started=len(subset),verified=sum(r['whole_workflow_verified'] for r in subset),mean_elapsed_seconds=mean([r['elapsed_seconds'] for r in subset]) if all(r['elapsed_seconds'] is not None for r in subset) else None,mean_restricted_completion_seconds=mean([r['restricted_completion_seconds'] for r in subset]),native_starts=sum(r['native_starts'] for r in subset),automatic_alerts=sum(r['automatic_alerts'] for r in subset),quiet_started=len(quiet),quiet_with_alert=sum(r['automatic_alerts']>0 for r in quiet))
 comparisons={}
 for baseline in ['base','observe','rules']:
  confidence=manifest['primary_interval'] if baseline=='base' else manifest['secondary_interval']
  comparisons[baseline]={m:contrast(rows,'continued_sft',baseline,m,confidence,manifest['bootstrap_replicates'],manifest['bootstrap_seed']) for m in ['restricted_completion_seconds','whole_workflow_verified','native_starts']}
 return dict(planned=len(planned),started=len(rows),unstarted=[t for k,(_,t) in planned.items() if k not in seen],complete_design=len(rows)==len(planned),audit_violations=violations,arms=arms,continued_sft_minus_baseline=comparisons,scope='Fresh stochastic executions of previously explored mechanisms; reviewer judgments are not workflow outcomes',limitations=['Unstarted trials are reported, not assigned fabricated failures.','Unmatched started trials remain in arm summaries; paired contrasts require both members.','A partial design does not complete the registered rep2.','Quiet attention incidence is not adjudicated false-alert incidence.','Equal observed completion counts do not establish population equivalence.'])

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--audit',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 m=json.loads(a.manifest.read_text());rows=json.loads((a.audit/'records.json').read_text());audit=json.loads((a.audit/'summary.json').read_text())
 result=summarize(m,rows,audit['violations']);result['manifest_sha256']=hashlib.sha256(a.manifest.read_bytes()).hexdigest();result['records_sha256']=hashlib.sha256((a.audit/'records.json').read_bytes()).hexdigest()
 with a.output.open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(dict(started=result['started'],planned=result['planned'],complete_design=result['complete_design'],audit_violations=result['audit_violations'],arms=result['arms'])))
if __name__=='__main__':main()
