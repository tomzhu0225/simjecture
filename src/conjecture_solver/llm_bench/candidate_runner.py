"""Executed in the candidate sandbox, without expected answers or grading authority."""

import importlib.util
import json
import sys
from pathlib import Path

module_path, manifest_path, output_path = map(Path, sys.argv[1:])
sys.path.insert(0, str(module_path.parent))
spec = importlib.util.spec_from_file_location("submission", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
results = {}
for name, directory in json.loads(manifest_path.read_text()).items():
    results[name] = module.reduce_case(directory)
output_path.write_text(json.dumps(results, allow_nan=False))
