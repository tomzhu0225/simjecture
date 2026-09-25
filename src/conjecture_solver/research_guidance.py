"""Reuse the classic guided package without treating supplied outputs as evidence."""

import json

from .mvp_guidance import MVPGuidedCommissioningPackage


class GuidedResearch:
    def install_guidance(self, path):
        from .research_service import put

        package = MVPGuidedCommissioningPackage.read(path)
        descriptor = package.descriptor()
        if package.spec.capability not in self.capability_hashes():
            raise ValueError("Guided capability is not installed in this study")
        if (
            any(r.bytes > 512 * 1024**2 for r in package.file_records)
            or sum(r.bytes for r in package.file_records) > self.manifest["max_experiment_bytes"]
        ):
            raise ValueError("Guided package exceeds study input limits")
        reserved = {"lab.py", "RESEARCH_GUIDE.md", "RESEARCH_BRIEF.md"}
        if any(r.path.split("/")[0] in reserved for r in package.file_records):
            raise ValueError("Guided package uses a reserved workspace path")
        with self.lock():
            manifest = json.loads((self.root / "research.json").read_text())
            prior = manifest.get("guided_commissioning")
            if prior:
                if prior != descriptor:
                    raise ValueError("Guided commissioning is immutable on resume")
                self.verify_guidance()
                return
            if (
                self._all("experiments")
                or self._all("methods")
                or (self.root / "study-launch.json").exists()
            ):
                raise ValueError("Cannot introduce guided commissioning after launch")
            payload = [(r.path, package.read_file(r.path)) for r in package.file_records]
            for name, _ in payload:
                target = self.work / name
                if not target.resolve().is_relative_to(self.work.resolve()):
                    raise ValueError("Guided path escapes its destination")
                if target.exists() or target.is_symlink():
                    raise ValueError("Guided package would overwrite existing workspace files")
            for name, data in payload:
                for base in [self.root / "guided_commissioning_input", self.work]:
                    target = base / name
                    if not target.resolve().is_relative_to(base.resolve()):
                        raise ValueError("Guided path escapes its destination")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
            manifest["guided_commissioning"] = descriptor
            put(self.root / "research.json", manifest)
            self.manifest = manifest

    def reproduce_anchor(self, *, timeout=600):
        """Run the exact unchanged guided command as a fresh exploratory observation."""
        from .research_service import sha

        descriptor = self.manifest.get("guided_commissioning")
        if not descriptor:
            raise ValueError("No guided commissioning package installed")
        self.verify_guidance()
        for record in descriptor["files"]:
            path = self._source(record["path"])
            if sha(path) != record["sha256"]:
                raise ValueError(
                    "Guided workspace changed; restore the original anchor or use lab.run"
                )
        source = descriptor["program_path"]
        output = descriptor["validation_summary_path"]
        return self.run(
            source,
            args=descriptor["validated_argv"][1:],
            inputs=[r["path"] for r in descriptor["files"] if r["path"] not in {source, output}],
            outputs=[output],
            capability=descriptor["capability"],
            stage="exploration",
            timeout=timeout,
            purpose="validation",
            key="guided-anchor",
        )

    def verify_guidance(self):
        from .research_service import sha

        base = self.root / "guided_commissioning_input"
        for record in self.manifest.get("guided_commissioning", {}).get("files", []):
            p = base / record["path"]
            if (
                p.is_symlink()
                or not p.resolve().is_relative_to(base.resolve())
                or not p.is_file()
                or sha(p) != record["sha256"]
            ):
                raise ValueError("Guided commissioning snapshot identity changed")


def main():
    """Bounded, model-free readiness run; never starts a hypothesis campaign."""
    import argparse
    import time
    from pathlib import Path

    from .execution import require_execution_backend
    from .research_service import ResearchService, put

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--guided-commission", type=Path, required=True)
    parser.add_argument("--capabilities", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wall-seconds", type=float, default=600)
    parser.add_argument(
        "--execution-backend", choices=["bubblewrap", "proot-cooperative"], default="bubblewrap"
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a fresh output directory; readiness never overwrites prior work")
    require_execution_backend(args.execution_backend)
    package = MVPGuidedCommissioningPackage.read(args.guided_commission)
    s = ResearchService.create(
        args.output,
        "Reproduce the supplied instrument anchor only.",
        capabilities=args.capabilities,
        wall_seconds=args.wall_seconds,
        execution_backend=args.execution_backend,
    )
    s.install_guidance(args.guided_commission)
    exp = s.reproduce_anchor(timeout=args.wall_seconds)
    while True:
        s.status()  # Reconcile detached-worker failures.
        exp = s._read("experiments", exp["id"])
        if exp["status"] not in {"queued", "running"}:
            break
        if time.time() >= s.manifest["deadline"]:
            s.cancel_active()
            exp = s._read("experiments", exp["id"])
            break
        time.sleep(0.25)
    result = dict(
        experiment=exp["id"],
        status=exp["status"],
        package_sha256=package.package_sha256,
        scientific_evidence_eligible=False,
        scope="Anchor reproduction only; no hypothesis or new geometry qualification",
        elapsed_seconds=time.time() - s.manifest["created_at"],
    )
    put(s.root / "readiness.json", result)
    print(json.dumps(result, indent=2))
    return 0 if exp["status"] == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
