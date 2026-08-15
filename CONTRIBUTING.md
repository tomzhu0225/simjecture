# Contributing

Contributions are welcome during the research-preview phase. Changes must keep
the distinction between scientific reasoning and infrastructure authority
explicit: agents may choose scientific details, while the harness controls
permissions, provenance, resource limits, and evidence eligibility.

## Development setup

```bash
uv sync --all-groups
uv run ruff check .
uv run pytest
uv run --group docs sphinx-build -W --keep-going -b html docs docs/_build/html
```

## Pull requests

- Keep each change scoped and explain which observed failure or public contract
  motivates it.
- Add regression tests for harness behavior.
- Do not commit credentials, local runtime installations, raw multi-gigabyte
  simulation output, or unpublished third-party material.
- Clearly label fixtures, commissioning output, discovery evidence, and held-out
  confirmation evidence.
- Do not strengthen a scientific conclusion beyond the evidence contract and
  recorded numerical qualification.

Generated schemas must remain synchronized:

```bash
uv run simjecture schemas --output schemas --check
```

By contributing, you agree that your contribution is licensed under the Apache
License 2.0.
