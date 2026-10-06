"""Copy to the project and execute with the warp-lbm-cylinder-1.0 capability."""

import os
import runpy

runpy.run_path(os.environ["SIMJECTURE_LBM_DRIVER"], run_name="__main__")
