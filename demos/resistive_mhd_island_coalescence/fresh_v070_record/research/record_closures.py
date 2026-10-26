import subprocess,sys
subprocess.run([sys.executable,'calibrate_transient.py'],check=True)
subprocess.run([sys.executable,'effective_width_calibration.py'],check=True)
