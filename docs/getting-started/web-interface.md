# Web interface

For model setup, project conversations, tool installation and autonomous research,
start with the [research workspace](research-workspace.md). Running `simjecture web`
without a campaign opens the workspace. `/monitor` opens the detailed experiment
view below, labelled **Study details · Evidence & review**; supplying a campaign
directory still opens that view directly. Workspace studies expose a shared
**Conversation → Study → Evidence & review** trail and **Back to this conversation**.
The owning conversation is resolved from recorded study ownership, not a browser
return URL. Standalone CLI studies show **Standalone study**, without inventing a
conversation. Read-only sessions keep navigation while disabling mutations.

The permanent dark rail has an experiment-monitor button above its bottom account
button. Open the account menu for theme, workspace details and the GitHub link;
local workspaces also offer Connections there. The chat input stays compact when
empty, expands with the draft and offers a larger editor for long messages. Its
model menu contains the local agent, model and effort choices. Narrow inspector
tabs have overflow arrows and accept horizontal scrolling or the mouse wheel.

The [hosted service](../how-to/public-trials.md) uses the same layout with
operator-managed compute and models. Signed-in visitors can upload files and keep
their work. Guest work is temporary. Clicking a hosted artifact downloads it;
plots can still be previewed inside the conversation.

The local web interface is the primary human-facing view of a Simjecture
campaign. It makes the scientific structure visible without replacing the
durable record. New studies use minimal; choose the agent backend and model
for the launch. Minimal reads `research.json`, experiment snapshots,
commitments and reviews. Legacy `mvp_manifest.json`, `transcript.jsonl`,
`hypothesis_ledger.json`, `mvp_report.json`, and artifact provenance remain the
sources of truth.

Minimal studies show actual agent activity instead of the fixed-stage role strip.
The header shows mode/backend/model and remaining budget. Long guidance and review
rationales fold away, with failed reviews expanded. Usage is pending/unavailable
when the backend has not supplied counters, never assumed to be zero. Archived
DSH activity remains visible, but its launch route is removed.

## Interface language

Choose **English / 简体中文** at the bottom of the workspace sidebar or in the
experiment monitor's top bar. The default is English, including when the browser
uses Chinese. An explicit choice applies immediately and is saved in this
browser's local storage for both pages on the same origin. Other open tabs update
as well. If browser storage is unavailable, switching still works on the current
page, but the preference cannot survive a reload.

Translation covers program-owned interface text: page and section headings,
navigation, buttons, form labels/help/placeholders, dialogs, notifications,
loading/empty states, status labels, graph legends, tooltips, accessibility text
and the onboarding tour. Workspace conversations, projects, tools, machines,
knowledge, benchmarks, study preparation/budgets and the experiment monitor share
the same catalog and language setting.

User names and input, historical conversations, generated research reports,
benchmark execution definitions, raw logs/evidence, model/tool identifiers,
commands, paths and API values remain verbatim. Known built-in tool descriptions,
benchmark descriptions and usage/pricing explanations are translated at their
display boundary only when the server wording matches the catalog. Custom or
newer descriptions and unrecognized server messages remain in their original language.

For contributors, `web/static/language/en.json` and `zh-CN.json` contain the
English and Chinese dictionaries, keyed by the same stable message IDs. Existing
IDs include semantic names such as `workspace.homeIntro` and keys derived from
English copy such as `ui.campaign-id`. Keep an ID stable when its
wording changes; prefer concise semantic names for new entries.
`language/manifest.json` maps language codes to their native display names; it
also supplies both language selectors. To add a language, add its JSON dictionary
and a manifest entry. No page-rendering changes are needed for existing keys.
Existing interpolations include positional names (`{p0}`, `{p1}`) as well as
descriptive names. Both use the same parameter-object API; names must match the
call site and every language's entry. Prefer meaningful names such as `{count}`
and `{model}` for new entries. English is the fallback dictionary.

The local and hosted servers include the complete English dictionary in the
`i18n-messages.js` response. If `language/en.json` is missing or unreadable
at startup, the servers use the copy packaged with the Web service. If only
some entries are missing or invalid, valid entries still take precedence.
This also works on a first visit when the browser cannot fetch any locale JSON.

Edit English copy in `web/static/language/en.json`. Refresh the packaged copy
from the repository root with the following command. The catalog test checks
that both files contain identical keys and text.

```sh
cp src/conjecture_solver/web/static/language/en.json src/conjecture_solver/web/english_fallback.json
```

The loader fetches the manifest and optional dictionaries once; `i18n.js` retains
the existing translation and DOM-binding API. Both page initializers await
`SimjectureI18n.ready`, so delayed requests cannot start a partially translated
application. The selector is disabled until initialization completes. Loading an
optional dictionary or the manifest can fail without preventing startup. The
selector offers languages with usable dictionaries. If a saved language is
unavailable, the page opens in English and retries that preference on the next
visit. Missing or invalid entries in a partial dictionary use English. All
catalogued interface text, including dynamic messages and accessibility attributes,
still has its full English fallback even if every locale JSON request fails.
Existing languages switch synchronously after initialization. A much larger language set
could use loading on demand later; the current two dictionaries need no bundler,
framework or runtime dependency.

This follows the common separation of language resources from rendering code,
as described in [i18next resource loading](https://www.i18next.com/how-to/add-or-load-translations)
and [explicit fallback](https://www.i18next.com/principles/fallback), while preserving
Simjecture's native JavaScript architecture.

Mark text-only elements with `data-i18n="message.key"`; use
`data-i18n-placeholder`, `data-i18n-title`, `data-i18n-aria-label` and the other
supported attribute markers for static attributes. Keep nested controls and
research content outside text-only markers.

Dynamic DOM helpers use `SimjectureI18n.content(node, value)`:

- Pass `SimjectureI18n.message("message.key", {name: value})` for UI copy.
- Use `SimjectureI18n.live(() => ...)` or `bindText(node, () => ...)` for display
  expressions that combine localized labels with changing values. Use catalog
  parameters rather than replacing fragments of an English sentence.
- Use `SimjectureI18n.attribute(node, "aria-label", () => ...)` for live attributes.
- Pass research data as ordinary strings. It is never searched for translations.
- Use `label(rawEnum, englishDisplay)` only for displayed enum labels; keep option
  values, datasets, state and API payloads raw. The default English display keeps
  the raw token, including underscores; pass an explicit fallback only when that
  view already formats it. `known(key, serverText)` is reserved
  for explicitly identified built-in UI descriptions, with raw fallback.

Changing language updates bound text/attributes in place, preserving inputs,
event handlers and expanded sections. State/revision signatures must use raw
values or stable message IDs, never translated display expressions. UI-only Markdown uses an explicit render
adapter; research Markdown keeps its normal renderer. Bindings use a `WeakMap`,
with no global mutation observer. Missing Chinese entries fall back to English;
an unknown key is displayed unchanged. No build step or extra runtime dependency
is required.

The Simplified Chinese catalog distinguishes domain concepts consistently:

| English concept | Simplified Chinese |
| --- | --- |
| study / campaign | 研究 / 研究活动 |
| instrument / tool / capability | 仪器 / 工具 / 能力 |
| judge / review | 裁决 / 评审 (审阅 for reading a document) |
| commissioning | 调试验证 |
| qualifies / verified | 资格认定 / 已验证 |

Here, an instrument may be a numerical program or method, not just physical
hardware. These are display terms; stored identifiers and scientific records
remain unchanged.

Run the repeatable source audit from the repository root:

```sh
python scripts/check_web_i18n.py --check
python scripts/check_web_i18n.py --json > /tmp/simjecture-i18n-audit.json
python -m pytest tests/test_web_i18n.py
```

The audit skips `vendor/` and separates localized references, reviewed technical
literals and unresolved candidates, including nested JS templates and obvious
text/attribute sinks. Reviewed non-UI blocks can use paired
`// i18n-technical-start: reason` and `// i18n-technical-end` comments; keep
these blocks narrow, since their contents are excluded from translation.
It is a conservative lexer, not a full JavaScript parser or
a translation percentage: indirect runtime values and server-provided copy need
browser review. New exclusions must identify technical content, not hide UI copy.
Review both languages at desktop and mobile widths, including open forms/dialogs,
dynamic updates, reloads, navigation and simultaneous tabs. Optional hosted,
authentication, provider and SSH workflows also require their usual integration
checks; real research output must remain unchanged.

## Open a recorded campaign

The browser interface is included in the core installation and has no Node.js
build or optional Python dependency:

```bash
uv sync --frozen
uv run simjecture web demos/kepler_energy/record
```

This starts a local server at `http://127.0.0.1:8765/` and opens the default
browser. Use `--no-open` to print the address without opening it, `--open` to
state the default explicitly, or `--port 0` to select an available local port
automatically.

In **Study details · Evidence & review**, a minimal study presents its recorded
hypothesis, requirements, completion policy, experiments, prospective repair
commitments, independent claim and methods reviews, director decisions, and
study ledger.

When attached to an archived classic campaign record, the interface also renders
its five legacy projections:

- **Claim graph:** one view of the durable ledger, with all four claim kinds as
  first-class nodes: `scientific`, `instrument`, `diagnostic`, and `control`.
  Claim records and inspectors retain their relations, including `repairs`,
  `refines`, `alternate`, `instrument_of`, `diagnostic_of`, and `control_for`.
  Scientific-only mode is a visual filter over this graph, not a second
  hypothesis data structure.
  A derived commissioning-stage node exposes the workflow dependency hidden by
  the parent-owned ledger representation. Scientific hierarchy arrows remain
  parent → child; prerequisite arrows point instrument claim → **qualifies** →
  commissioning → **enables evidence for** → scientific target. Diagnostic and
  control prerequisites likewise point into their scientific target. The stage
  and every supporting-claim inspector name that target. This exposes the
  capability evidence gate and guided starting point without becoming a fifth
  durable claim kind or changing the underlying ledger.
- **Claim inspector:** click any of the four node kinds to see its rationale,
  parent and child relations, prospective evidence contracts, linked evidence,
  closure reason, and iteration metadata.
- **Execution monitor:** recent simulations and calculations appear as separate
  runs. Select one run to inspect its state, command binding, elapsed time,
  heartbeat I/O, workspace size, return code, and bounded console excerpt.
- **Research trace:** typed model decisions, the model-authored `research_note`,
  tool outcomes, retries, routes, and input/output/reasoning/cache token counts.
  This is an auditable laboratory trace, not a representation of a provider's
  private hidden chain-of-thought. A durable loop strip above the trace names
  the current stage (`commissioning`, `falsification`, `repair`, or
  `adjudication`), active role (Falsifier, Scientist, or Judge), repair cycle,
  active claim, and remaining wall time. Its moving bar is intentionally
  indeterminate: an open scientific search has no honest completion percentage.
- **Artifacts and conclusion:** contained workspace results, generated figures,
  audit records, and the terminal answer when one exists.

The graph uses the bundled Dagre engine to compute both left-to-right and
top-to-bottom layered layouts, then selects the orientation that permits the
largest on-screen text while every visible node still fits. This happens on
first load and whenever the claim set changes. Scroll over the canvas to zoom
around the cursor, drag empty canvas to pan, use **Fit all** to recover the
complete view, or use the plus/minus controls for centered zoom. Each node is
keyboard-selectable and independently draggable. Positions are stored under a
campaign-specific browser key and never written into the durable run; **Reset
layout** removes the local arrangement and recomputes the optimal layout. Node
copy is line-bounded, ellipsized, and clipped to its box. The four kinds use
distinct node treatments while their status is shown separately, so claim type
is never inferred from supported or falsified state. Expanded contract and
evidence sections remain open while the one-second live refresh advances. The
header theme button switches between the high-contrast light and dark palettes
and remembers the choice locally.

Human-facing scientific text is rendered as sanitized Markdown throughout the
campaign heading, claim inspector, contracts, evidence assessments, research
notes, and conclusion. Inline code, fenced code, lists, tables, links, and TeX
delimiters are supported; TeX is converted to MathML. The browser bundles its
pinned parser, sanitizer, and math renderer locally and makes no CDN request.
Raw HTML, images, form controls, embedded objects, and unsafe links are removed
before display. For legacy natural-language hypotheses that predate the
Markdown convention, a conservative display-only adapter recognizes common
ASCII forms such as `0 < theta_0 <= 2.5 rad` and
`T_0 = 2*pi*sqrt(L/g)` and supplies TeX delimiters before rendering. Explicit
Markdown math and inline code are left untouched. The underlying JSON record
remains unchanged.

The built-in `scientific-markdown` skill tells the autonomous agent how to use
this presentation layer without moving estimator definitions, units,
normalizations, thresholds, or validation checks out of machine-readable
evidence artifacts.

The execution monitor deliberately does not invent a percentage for an
unbounded scientific search. A running command uses an indeterminate activity
bar and reports only observed state, heartbeat, time, I/O, and resource values.
When several runs exist, the left-hand list selects the one shared console view;
the page does not create a wall of simultaneous terminals.

## Follow or control a campaign

Attach the browser to an existing output directory:

```bash
uv run simjecture web artifacts/my-campaign
```

The server polls only durable, fsynced state. A missing terminal report is not
enough to label a process as running: the green `running` state requires a
supervisor record that still matches the PID, process start time, command line,
and output directory.

Pause, resume, and stop use the same verified control functions as the CLI.
Pause is cooperative at the next action boundary. Stop sends
SIGINT and a bounded SIGTERM fallback only to a verified process. Closing the
browser or pressing Ctrl-C in the server terminal does not stop a campaign.

For review or screen sharing, disable every mutation:

```bash
uv run simjecture web demos/kepler_energy/record --read-only
```

## Advanced hypothesis launch

Open `/monitor` and select **New hypothesis** for the advanced launch form. For
conversation-led setup and research, use the workspace's **New conversation** instead. The
form keeps the immutable root hypothesis separate from optional operational
guidance and records the execution envelope before starting the runner. The
child process inherits provider credentials from the terminal environment; the
advanced form does not request an API key. The separate workspace **Connections**
page stores a user-supplied compatible API key in a private mode-0600 server file;
it does not send that key back to the browser.

```bash
uv run simjecture web --runs-root artifacts
```

The advanced form launches minimal research with a native CLI agent using its
existing login. For the built-in API agent, configure **Connections** and prepare
a study from a workspace conversation. Both use the same minimal evidence workflow.

Browser and CLI studies preserve `study-launch.json` and the exact operator
input files. No shell command is constructed from hypothesis text. Minimal is the
only launch mode; legacy DSH/API, structured and frontier choices are removed.
Historical records remain inspectable without Node.js or DSH. See
[migration](../how-to/minimal-migration.md) before upgrading an older running study.

## Local security boundary

For the separate development public trial gateway, see
[public trials](../how-to/public-trials.md). Its controlled tools and visitor
sessions do not change the operator workspace's boundary described below.

The local web interface is intentionally an operator tool rather than a hosted service:

- the server refuses non-loopback bind addresses;
- mutating requests require an unguessable per-process control token and a
  same-origin JSON request;
- no cross-origin access is enabled;
- artifact paths are contained inside the selected run and symbolic links are
  not served;
- a restrictive content-security policy blocks external scripts and frames.

It does not provide remote authentication, multi-user ownership, or a public
deployment boundary. Use the headless CLI commands or SSH port forwarding for
remote hosts; do not proxy the local server onto a network.

## Headless clients

The browser, `status`, and `watch` are clients of the same durable projection.
New interactive UX is developed for the browser, while `status` and `watch`
remain the stable headless clients for SSH and machines without a browser. See
[Run a headless study](../how-to/headless-studies.md).
