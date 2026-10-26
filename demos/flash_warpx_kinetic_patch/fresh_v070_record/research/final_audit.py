"""Frozen qualified tensor audit, followed by explicit protocol arithmetic."""
import runpy,sys
sys.argv=['analysis_study.py','--case','seed6101','seed6101_record','evidence_patch.npz','--case','seed6102','seed6102_record','evidence_patch.npz']
runpy.run_path('analysis_study.py',run_name='__main__')
runpy.run_path('decision.py',run_name='__main__')
