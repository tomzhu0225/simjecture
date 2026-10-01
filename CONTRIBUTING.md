# Contributing

Contributions are welcome. Simjecture is a research harness: agents may choose
scientific details, while the harness controls permissions, provenance, resource
limits and evidence eligibility. Keep those responsibilities separate.

## Start with a reproducible problem

For a bug, report the exact package version and Git commit, operating system,
execution backend, minimal reproduction, expected result and observed result.
Redact credentials and private paths. For security-sensitive issues, follow
[SECURITY.md](SECURITY.md) rather than opening a public issue. Discuss large changes
or scientific-policy changes with the maintainer before investing in an implementation.

Stable 0.5.2 and the 0.5.3rc3 preview have different feature sets. Develop against
the intended branch and identify it in the issue or pull request; do not assume
preview behavior is available in a stable installation.

## Development setup

Use Linux (or WSL), Python 3.11+ and uv. From a source checkout:

```bash
uv sync --frozen --extra workspace --extra tui --extra dsh --group browser --group docs
uv run ruff check .
uv run pytest
uv run simjecture schemas --output schemas --check
uv run --group docs sphinx-build -W --keep-going -b html docs docs/_build/html
```

`dev` is the default dependency group. Browser tests additionally need Chromium:
`uv run playwright install chromium`. DSH integration work needs the pinned Node
version from `.github/workflows/ci.yml`, followed by:

```bash
npm ci --prefix integrations/dsh
SIMJECTURE_MCP_EXECUTABLE="$PWD/.venv/bin/simjecture-mcp" npm test --prefix integrations/dsh
```

Consult the CI workflow for the complete release checks. Bubblewrap-dependent
checks require a host that permits user namespaces; PRoot needs working tracing
and is only a cooperative alternative. A missing binary, blocked kernel feature
or skipped integration test is not a pass. Record the exact blocker and run the
independent checks you can. See [restricted hosts](docs/how-to/restricted-containers.md).
Do not use real provider credentials or paid model calls for ordinary regression tests.

## Code style and tests

- Follow nearby code and keep changes focused. Python targets 3.11+; Ruff enforces
  a 100-column limit and the `E`, `F`, `I`, `UP`, `B`, `SIM` rule families configured
  in `pyproject.toml`. Import ordering is checked by Ruff. Do not reformat unrelated files
- Use clear names, type annotations consistent with the surrounding module and
  small explicit interfaces. Explain non-obvious scientific or security assumptions
- Keep UI projections separate from durable scientific state. Validate untrusted
  paths and inputs at their boundary; do not bypass permission or evidence gates
- Add deterministic regression tests for changed behavior, including failure paths,
  restart/recovery and compatibility when affected. Use temporary directories and
  fixtures instead of user installations, network accounts or licensed solver source
- Changes to public models must regenerate schemas and pass the schema check.
  Update affected CLI examples, user docs and the changelog with user-visible changes
- Keep JavaScript consistent with nearby modules and run the relevant browser or
  DSH tests. There is no separate repository-wide JavaScript formatter requirement

For a focused iteration, run the affected test module (for example,
`uv run pytest tests/test_study.py` if that file is relevant), then broaden to the
checks above. Report actual commands and outcomes, including skipped tests.

## Pull request process

1. Create a focused branch from the intended base. Explain the observed failure or
   public contract, proposed behavior and any compatibility or migration effects
2. Include the regression test and before/after evidence. For UI changes, include
   screenshots at desktop and narrow widths, plus the interaction tested
3. Run applicable checks and list their outcomes in the PR. Separate tests run
   locally from historical release evidence; do not imply an unavailable solver,
   provider or sandbox was exercised
4. Review the diff for secrets, generated output and unrelated changes. Do not
   commit credentials, local runtime installations, bulk simulation output or
   unpublished third-party material
5. Request maintainer review and address feedback. Do not merge scientific-policy,
   security-boundary or release changes without the appropriate maintainer review

Clearly label fixtures, commissioning output, discovery evidence and held-out
confirmation evidence. Preserve original records and attach corrections rather
than rewriting historical scientific evidence. A coding benchmark over recorded
diagnostics is not a new simulation or a scientific acceptance result. Do not
strengthen a conclusion beyond its evidence contract and numerical qualification.

## Publication authorship — DRAFT for Bowen's review

**This section is a discussion draft, not an adopted authorship policy.**
Substantial contributors **may be considered for authorship on relevant papers**.
A contribution, accepted pull request or software credit does not promise or
entitle anyone to authorship. No final eligibility criteria are set here.

Bowen must decide the criteria and review process before any policy is adopted,
including what counts as substantial contribution to a particular paper, how
contributions are documented, how authorship is discussed with collaborators,
and how applicable venue requirements and other forms of credit are handled.
These are open questions for Bowen to review, not conditions contributors should
interpret as already agreed. Paper-specific authorship requires a separate
explicit discussion and agreement.

## License and provenance

By contributing, you agree that your contribution is licensed under the
[Apache License 2.0](LICENSE). Identify upstream sources and retain required
copyright/license notices. Do not contribute code, data or solver material you
lack permission to redistribute. Cite scientific and software sources precisely;
record the version and commit when reporting results. See [CITATION.cff](CITATION.cff)
and [third-party notices](THIRD_PARTY_NOTICES.md).
