# Documentation development

The public documentation uses Sphinx, MyST Markdown and the
[Furo theme](https://pradyunsg.me/furo/). Its light/dark identity uses the application's
approved brand assets directly; `docs/_static/docs.css` supplies the landing-page
layout and typography. Search, mobile navigation, source links and theme switching
come from Furo.

```bash
uv sync --frozen --group docs
uv run --group docs sphinx-build -W --keep-going -b html docs docs/_build/html
```

The rendered site is published at [drawingsword.com/simjecture](https://drawingsword.com/simjecture/).
The `Publish documentation` workflow builds and checks relevant changes on `main`
before deploying to GitHub Pages. Pull requests run the same Sphinx and local-link
checks in CI. Publication does not require a package release, and the release
number shown in the sidebar comes from package metadata.

Treat warnings as build failures. Keep pages in one of four roles:

- tutorials teach through a complete learning path;
- how-to guides solve a specific operational task;
- reference documents the exact public interface;
- explanation describes architecture, scientific reasoning, and limitations.

Current user guides should stay in those four roles. Dated research and release
acceptance records are retained at their existing `research/` and `testing/` paths
and grouped in the [archive](../archive/index.md). They document what was checked
then, not a promise that the same checks passed on the current host. Incremental
implementation notes belong in Git history.

## Give each fact one home

- `README.md`: the research loop, a concrete evidence example, quickstart and next steps
- `CONTRIBUTING.md`: ways to help, minimal setup and contribution-specific checks
- Installation and how-to guides: complete task recipes and their prerequisites
- Reference: exact command interfaces, compatibility aliases and import names
- Explanation: architecture, scientific contracts and limitations
- `CHANGELOG.md`: release changes; GitHub Releases use the matching section, as
  described in the [release process](releasing.md)
- Dated archive records: validation commands, measurements, context and known limits

When behavior changes, update its owning guide and link to it from entry points.
Do not copy the release diary, test totals or the full CLI recipe into every page.
Keep historical reports intact and attach clearly labelled corrections when needed.
Change user guides when their instructions or claims change, rather than when
the package number changes.

Distinguish stable instructions from preview-only features. Check CLI
examples against the checkout's `--help` and model/API claims against source and
tests. Build with warnings as errors and check relative links. For examples that
need credentials, licensed source, GPU hardware or an unavailable sandbox, state
what was not exercised. Read-only demo verification, task preparation and HTML
export are useful no-key checks; benchmark grading still executes submitted code.

See the repository's [contributor guide](https://github.com/tomzhu0225/simjecture/blob/main/CONTRIBUTING.md)
for coding checks, pull-request expectations and licensing.

Examples must use placeholders for credentials and bounded output directories.
Never paste a real key, private run URL, or unpublished third-party artifact into
the documentation.

## Keep release maintenance small

| Kind of page | Version policy |
|---|---|
| README, installation and everyday guides | Use the latest stable installer or an unpinned stable package install. Describe behavior without repeating the current release number. |
| Generated site chrome | Read the build version from `pyproject.toml` in `docs/conf.py`. |
| Changelog and release acceptance | Record the exact version, tested commit, commands and outcomes once. Acceptance pages are indexed by the archive's glob toctree. |
| Scientific demos and audits | Freeze the original software, model, solver and data identities. Append corrections; do not relabel an old run as a new release. |
| Independently versioned capabilities and benchmarks | Keep their actual runtime or task-pack versions. They need not match the application version. |

A guide that requires a new feature should state that requirement where the user
needs it, especially during a preview. Do not remove dependency or compatibility
constraints merely to make text look evergreen. General instructions follow the
stable behavior; versioned records explain exactly what happened on an earlier
checkout.

## Report host-dependent and long-running checks honestly

Before a solver or full workspace test, run the selected execution backend's
`simjecture doctor --execution-backend BACKEND` probe. An installed `bwrap` or
`proot` binary does not establish that namespaces or tracing work. Some existing
tests check only binary presence, so a restricted host can fail rather than skip
those tests. Preserve the failure and classify it from the actual probe/log.

For a long check, retain the command, start time, log and final exit status. A
quiet log or polling timeout is not a pass or permission to resubmit a detached
job. Reconcile its recorded identity before retrying. Keep blocked, skipped,
running and failed checks separate from passed checks; never change tests to
report success merely because the host cannot run them.

Examples requiring paid model calls, credentials, licensed solver source, GPU
hardware, SSH workers or Docker should list those prerequisites. Run them only
in an authorized environment; otherwise report the unexercised behavior and
continue independent no-key checks. A successful replay of historical artifacts
does not replace a fresh numerical execution or long-job recovery test.

## Present the research process

Entry pages should show human framing, autonomous counterexample search, prospective
repairs, fresh tests and independent review before listing infrastructure. Identify
the default minimal workflow and distinguish `answer` from `repair` completion.
Historical demos retain their original records and carry a visible workflow/version
label. A newly rendered screenshot does not make an old investigation a current run.

A fresh example should publish its operator inputs, software identity, selected
backend, recorded outcome and verification recipe. Attribute human framing, agent
work, independent review and later editorial plots separately. Keep credentials
and private native-session details out of distributable records. Do not turn a
stopped or inconclusive study into a success story.

For visual changes, inspect the generated site in light/dark modes and at a narrow
mobile width. Exercise search, sidebar navigation and the primary tutorial/demo
links. Raw HTML landing-page links also need checking: a warning-free Sphinx build
does not validate their destinations.
