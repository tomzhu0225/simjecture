"""Finish managed FreeCAD/Gmsh installs after Micromamba dependency setup."""

import json
import os
import subprocess
import sys
from pathlib import Path

os.environ["PYTHONNOUSERSITE"] = "1"
profile, raw_prefix = sys.argv[1:]
prefix = Path(raw_prefix).resolve()
if profile == "gmsh":
    subprocess.run(
        [str(prefix / "bin/python"), "-m", "pip", "install", "gmsh==4.15.2", "meshio==5.3.5"],
        check=True,
    )
elif profile != "freecad":
    raise ValueError("Unsupported geometry runtime")
share = prefix / "share"
share.mkdir(exist_ok=True)
packages = [json.loads(p.read_text()) for p in sorted((prefix / "conda-meta").glob("*.json"))]
record = {
    "profile": profile,
    "conda_packages": [
        {key: p.get(key) for key in ("name", "version", "build", "sha256", "url")} for p in packages
    ],
}
if profile == "gmsh":
    record["pip_packages"] = json.loads(
        subprocess.check_output([str(prefix / "bin/python"), "-m", "pip", "list", "--format=json"])
    )
(share / "build-record.json").write_text(json.dumps(record, indent=2) + "\n")
