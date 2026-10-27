"""Prepare a six-workflow control commission from an immutable source commit.

This command does not execute a worker, allocate compute or load a model.
Execution requires an audited complete predecessor and separately bounded runner.
"""

import argparse
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

from simjecture_monitor.control_commission import TOOL_FILES, plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    revision = subprocess.run(
        ["git", "rev-parse", args.revision + "^{commit}"],
        cwd=args.source,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    source = subprocess.run(
        [
            "git",
            "archive",
            "--format=tar",
            revision,
            "src",
            "scripts",
            "packages/simjecture-monitor",
        ],
        cwd=args.source,
        capture_output=True,
        check=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(source)) as archive:
        hashes = {
            member.name: hashlib.sha256(archive.extractfile(member).read()).hexdigest()
            for member in archive.getmembers()
            if member.isfile()
        }
    value = plan(revision, hashes)
    value["source_archive_sha256"] = hashlib.sha256(source).hexdigest()
    value["source_scope"] = (
        "All tracked regular files under src, scripts and packages/simjecture-monitor"
    )
    package = Path(__file__).parents[1]
    value["commissioning_tools_sha256"] = {
        name: hashlib.sha256((package / name).read_bytes()).hexdigest() for name in TOOL_FILES
    }
    with args.output.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            dict(workflows=value["workflows"], source_revision=revision, execution_started=False)
        )
    )


if __name__ == "__main__":
    main()
