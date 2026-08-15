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

1. Update the version in `pyproject.toml`, `CITATION.cff`, and the changelog.
2. Run the complete local checks and merge them into `main`.
3. Create an annotated `v<version>` tag on the tested commit.
4. Publish a GitHub Release from that tag using the matching changelog section.
5. Verify the GitHub workflow, PyPI files, and Zenodo deposit before announcing
   the release.

Publishing the GitHub Release is intentionally last: it triggers both external
publication paths and cannot be treated as a rehearsal.
