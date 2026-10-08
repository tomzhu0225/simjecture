# Release process

Simjecture publishes from a GitHub Release. The release workflow builds the
source distribution and wheel, verifies that the tag matches the version in
`pyproject.toml`, and uploads to PyPI with an OpenID Connect credential. No
long-lived PyPI token is stored in GitHub.

## One-time account connections

Configure a PyPI pending trusted publisher with these exact values:

- PyPI project name: `simjecture`
- GitHub owner: `tomzhu0225`
- GitHub repository: `simjecture`
- Workflow filename: `release.yml`
- Environment name: `pypi`

In Zenodo's GitHub settings, enable the `tomzhu0225/simjecture` repository.
Zenodo then archives each new GitHub Release and assigns a version DOI.
`CITATION.cff` supplies its software metadata.

## Publish a version

1. Update the version in `pyproject.toml`, `CITATION.cff`,
   `src/conjecture_solver/__init__.py`, `scripts/install-workspace.sh`, and the changelog.
   The docs build reads its version from `pyproject.toml`; general installation
   links resolve the latest stable release automatically. Historical study and
   acceptance records keep their original versions.
   Run `uv lock` and build both Python distributions (`uv build`) and the checksummed
   workspace bundle (`python scripts/package_workspace.py --output dist`).
   Verify the installer with `python scripts/verify_workspace_install.py --release-dir dist
   --work-dir /tmp/simjecture-release-install-check`. This uses a fresh HOME, no API key
   or CLI agent, and does not change host system packages.
2. Run the complete local checks and merge them into `main`.
3. Create an annotated `v<version>` tag on the tested commit.
4. Publish a GitHub Release from that tag using the matching changelog section.
5. Verify the GitHub workflow, installer assets/checksums, PyPI files, and Zenodo deposit before announcing
   the release.

Publishing the GitHub Release is intentionally last: it triggers both external
publication paths and cannot be treated as a rehearsal.

## Preview policy

Ship user-facing changes first as explicit release candidates (`X.Y.Zrc1`,
`X.Y.Zrc2`, …). Use matching GitHub tags (`vX.Y.Zrc1`) and mark the GitHub release
**prerelease**, without moving the stable/latest release. PyPI receives the PEP
440 prerelease version; ordinary stable installs do not automatically select it.
If a matching npm bundle is released, use SemVer spelling (`X.Y.Z-rc.1`).

Use the versioned installer URL in that candidate's release notes so preview
checks can be repeated. Never replace an already published release's artifacts
with different code, including a preview. A fix needs a new version.

Record setup, interface, simulation and session-continuity feedback against the
exact candidate. The installer keeps versioned program folders and stable
research-data folders; retain old versions during the preview period. After user
testing and release checks pass, publish the approved final version as stable.
General guides continue using the latest-stable installer; no per-page link sweep
is needed. A preview does not establish scientific qualification for solver
applications.
