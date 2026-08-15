# Documentation development

The public documentation uses Sphinx with MyST Markdown and the PyData Sphinx
Theme.

```bash
uv sync --group docs
uv run --group docs sphinx-build -W --keep-going -b html docs docs/_build/html
```

Treat warnings as build failures. Keep pages in one of four roles:

- tutorials teach through a complete learning path;
- how-to guides solve a specific operational task;
- reference documents the exact public interface;
- explanation describes architecture, scientific reasoning, and limitations.

Keep the tree to those four roles. Incremental development notes belong in
Git history, not in the current documentation.

Examples must use placeholders for credentials and bounded output directories.
Never paste a real key, private run URL, or unpublished third-party artifact into
the documentation.
