"""Recorded study entry point; execution arguments select the owned calculation."""
import argparse,runpy,sys
p=argparse.ArgumentParser();p.add_argument('task',choices=['flash','transfer','kinetic','analysis']);a,rest=p.parse_known_args()
sys.argv=[{'flash':'macro_study.py','transfer':'transfer_study.py','kinetic':'kinetic_study.py','analysis':'analysis_study.py'}[a.task]]+rest
runpy.run_path(sys.argv[0],run_name='__main__')
