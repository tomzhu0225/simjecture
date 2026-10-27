"""Add the disjoint R9 records through the already validated aggregator."""
from pathlib import Path
import subprocess,sys
from combine_r8_continuation import aggregate
ROOT=Path('/home/simjecture/investigations/scientific-attention-20261025')
def main():
 audit,campaign=aggregate([(ROOT/'r7-audit',ROOT/'base-sft-replication-v3'),(ROOT/'r8-audit',ROOT/'base-sft-replication-v4'),(ROOT/'r9-audit',ROOT/'base-sft-replication-v5')],ROOT/'r9-all-continuation-records')
 subprocess.run([sys.executable,str(ROOT/'combine_base_sft_phases.py'),'--root',str(ROOT),'--new-audit',str(audit),'--new-campaign',str(campaign),'--output',str(ROOT/'r9-combined-summary.json')],check=True)
if __name__=='__main__':main()
