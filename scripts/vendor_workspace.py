"""Vendor a small, offline Web Awesome component set and highlight.js (build-time only)."""

import base64
import hashlib
import io
import json
import re
import tarfile
import tempfile
from pathlib import Path

import httpx

TARGET = Path(__file__).resolve().parents[1] / "src/conjecture_solver/web/static/vendor"


def package(name, version, directory):
    metadata = httpx.get(f"https://registry.npmjs.org/{name}/{version}", timeout=30).json()
    response = httpx.get(metadata["dist"]["tarball"], timeout=60)
    response.raise_for_status()
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(response.content).digest()).decode()
    if integrity != metadata["dist"]["integrity"]:
        raise ValueError("Package integrity mismatch")
    with tarfile.open(fileobj=io.BytesIO(response.content)) as archive:
        archive.extractall(directory, filter="data")
    return directory / "package", dict(
        name=name, version=version, integrity=integrity, source=metadata["dist"]["tarball"]
    )


def main():
    TARGET.mkdir(exist_ok=True)
    manifest = []
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        source, identity = package("@awesome.me/webawesome", "3.14.0", root / "wa")
        manifest.append(identity)
        destination = TARGET / "webawesome-3.14.0"
        destination.mkdir(exist_ok=True)
        (destination / "LICENSE.md").write_bytes((source / "LICENSE.md").read_bytes())
        source = source / "dist-cdn"
        pending = [
            source / f"components/{name}/{name}.js"
            for name in ("split-panel", "tab-group", "tab", "tab-panel", "spinner", "drawer")
        ]
        pending += [source / "styles/themes/default.css"]
        seen = set()
        while pending:
            path = pending.pop().resolve()
            if path in seen:
                continue
            seen.add(path)
            relative = path.relative_to(source.resolve())
            content = path.read_text()
            output = destination / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content)
            for dependency in re.findall(r"""["'](\.[^"']+\.(?:js|css))["']""", content):
                pending.append(path.parent / dependency)
        print(f"Web Awesome: {len(seen)} local modules/styles")
        source, identity = package("@highlightjs/cdn-assets", "11.11.1", root / "hljs")
        manifest.append(identity)
        for src, dst in [
            ("highlight.min.js", "highlight-11.11.1.min.js"),
            ("styles/github-dark.min.css", "highlight-github-dark.css"),
            ("LICENSE", "highlight-LICENSE"),
        ]:
            (TARGET / dst).write_bytes((source / src).read_bytes())
    (TARGET / "workspace-vendors.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
