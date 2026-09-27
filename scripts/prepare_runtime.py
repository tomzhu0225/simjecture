"""Prepare optional solver dependencies without system package privileges."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from conjecture_solver.runtime_bootstrap import prepare_runtime_environment

prepare_runtime_environment(sys.argv[1], Path(sys.argv[2]).resolve())
