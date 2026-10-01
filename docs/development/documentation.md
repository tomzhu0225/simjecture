# Documentation development

The public documentation uses Sphinx with MyST Markdown and the PyData Sphinx
Theme.

```bash
uv sync --frozen --group docs
uv run --group docs sphinx-build -W --keep-going -b html docs docs/_build/html
```

Treat warnings as build failures. Keep pages in one of four roles:

- tutorials teach through a complete learning path;
- how-to guides solve a specific operational task;
- reference documents the exact public interface;
- explanation describes architecture, scientific reasoning, and limitations.

Current user guides should stay in those four roles. Dated research and release
acceptance records are retained separately under `research/` and `testing/`;
they document what was checked then, not a promise that the same checks passed
on the current host. Incremental implementation notes belong in Git history.

Distinguish stable 0.5.2 instructions from preview 0.5.3rc3 features. Check CLI
examples against the checkout's `--help` and model/API claims against source and
tests. Build with warnings as errors and check relative links. For examples that
need credentials, licensed source, GPU hardware or an unavailable sandbox, state
what was not exercised. Read-only demo verification, task preparation and HTML
export are useful no-key checks; benchmark grading still executes submitted code.

See the repository's [contributor guide](https://github.com/tomzhu0225/simjecture/blob/main/CONTRIBUTING.md)
for coding checks, pull-request expectations, licensing and the draft publication
authorship discussion.

Examples must use placeholders for credentials and bounded output directories.
Never paste a real key, private run URL, or unpublished third-party artifact into
the documentation.
