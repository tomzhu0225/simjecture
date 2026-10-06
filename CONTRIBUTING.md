# Contributing

Thanks for helping improve Simjecture. You can contribute without running a full
research campaign or installing a scientific solver. Useful contributions include:

- reporting a reproducible bug or a confusing part of the interface;
- improving an example, installation step, or explanation;
- adding a small deterministic regression test;
- improving a runtime integration, scientific validation, or evidence workflow.

For a first change, pick one unclear documentation step or an edge case in an
existing test module. Keep it small enough to explain and review on its own.
Discuss large changes or scientific-policy changes with the maintainer before
investing in an implementation.

## Report a problem

Include the exact package version and Git commit, operating system, execution
backend, minimal reproduction, expected result, and observed result. Identify
whether you are using a stable release or a preview; their features may differ.
Redact credentials and private paths. For security-sensitive issues, follow
[SECURITY.md](SECURITY.md) rather than posting the details publicly.

## Start developing

Use Linux (or WSL), Python 3.11+, and uv. From a source checkout:

```bash
uv sync --frozen
uv run pytest tests/test_models.py
```

The default `dev` dependency group includes pytest and Ruff. The example test
module checks model validation without provider credentials or a solver. Install
additional dependencies only when they are needed for your contribution.

## Check the part you changed

- **Python:** run `uv run ruff check .` and the affected test modules, then broaden
  coverage as appropriate. Follow nearby code, use clear names and consistent type
  annotations, and avoid unrelated reformatting. Ruff's rules are in
  [pyproject.toml](pyproject.toml)
- **Public models:** regenerate with `uv run simjecture schemas --output schemas`,
  then run `uv run simjecture schemas --output schemas --check` and relevant tests
- **Documentation:** use `uv sync --frozen --group docs`, then
  `uv run --group docs sphinx-build -W --keep-going -b html docs docs/_build/html`.
  Check changed examples and links; see [documentation development](docs/development/documentation.md)
- **Browser UI:** add the `browser` dependency group with
  `uv sync --frozen --group browser`, install Chromium with
  `uv run playwright install chromium`, and run the affected browser tests.
  Add `--extra workspace` to the sync command when testing workspace features
- **Hosted service:** add `--extra public` and run `tests/test_public*.py`.
  General executor qualification additionally requires a dedicated Linux host,
  reserved job accounts, Landlock and libseccomp; the operator examples under
  `scripts/setup_public_*` must be adapted to that host
- **DSH integration:** use `uv sync --frozen --extra dsh` and the Node version
  pinned in [CI](.github/workflows/ci.yml), then run `npm ci --prefix integrations/dsh`
  and `SIMJECTURE_MCP_EXECUTABLE="$PWD/.venv/bin/simjecture-mcp" npm test --prefix integrations/dsh`.
  See the [adapter guide](integrations/dsh/README.md#adapter-validation)
- **Execution backends and scientific runtimes:** follow the relevant capability
  guide and probe the actual backend before testing. See
  [adding a capability](docs/how-to/add-a-capability.md) and
  [restricted hosts](docs/how-to/restricted-containers.md)

The [CI workflow](.github/workflows/ci.yml) defines the broader integration and
release checks; its full environment is not the starting requirement for every
contribution. Bubblewrap needs working user namespaces, and cooperative PRoot
needs working tracing. Record unavailable prerequisites, failures, and skipped
checks separately from passes, and run the independent checks you can. Do not use
real provider credentials or paid model calls for ordinary regression tests.

## Keep research records trustworthy

Simjecture is a research harness: agents choose scientific details; the harness
controls permissions, provenance, resource limits, and evidence eligibility.
Keep UI projections separate from durable scientific state, validate untrusted
inputs at their boundary, and do not bypass permission or evidence gates.

Label fixtures, commissioning, discovery, and held-out confirmation clearly.
Preserve original records and append corrections. A replay or coding benchmark
on recorded diagnostics is not a fresh simulation or scientific acceptance.
Keep conclusions within their evidence contract and numerical qualification.
For the workflow-specific rules, read [evidence and claims](docs/concepts/evidence-and-claims.md)
and [minimal-mode methods review](docs/how-to/minimal-oversight.md).

## Before opening a pull request

- Use a focused branch from the intended base, and explain the change and any
  compatibility or migration effects
- Add deterministic regression tests for changed behavior, including relevant
  failure, restart, and recovery paths. Use fixtures and temporary directories
- Update affected examples, user documentation, and the changelog for user-visible
  changes. For UI changes, include desktop/narrow screenshots and the interaction tested
- List the commands you ran and their actual outcomes, including blocked or skipped
  checks. Keep local results separate from historical release evidence
- Review the diff for secrets, generated output, and unrelated changes, then request
  maintainer review. Scientific-policy, security-boundary, and release changes
  require appropriate maintainer review before merging

## License and provenance

By contributing, you agree that your contribution is licensed under the
[Apache License 2.0](LICENSE). Identify upstream sources and retain required
copyright/license notices. Do not contribute code, data, solver material, or
unpublished third-party artifacts you lack permission to redistribute. Keep local
runtime installations, bulk simulation output, and credentials out of commits.
Cite scientific and software sources precisely, including versions and commits
when reporting results. See [CITATION.cff](CITATION.cff) and
[third-party notices](THIRD_PARTY_NOTICES.md).
