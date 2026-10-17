# Adjust research operating settings

A campaign's deadline and resource reservations remain authoritative. Worker turn
boundaries, model response budgets and review packet sizes serve different purposes;
they should not silently prevent a feasible investigation.

## Defaults

New minimal studies have no fixed worker action count and no automatic five-minute
worker interruption. The director can review a long-running turn concurrently, using
a separate process and context. Its verdict returns to the main supervisor for
validation and application. Director usage remains part of campaign accounting.

The host still handles explicit review handoffs, replans, pauses, cancellation,
inactivity and the authorized deadline. It also keeps the protected reporting phase.
Removing a periodic interruption does not remove those controls.

| Setting | Default | Effect of an explicit value |
|---|---|---|
| `worker_action_limit` | `null` | End a built-in API turn after that many actions; preserve an incomplete checkpoint. |
| `worker_checkpoint_seconds` | `null` | Apply an explicit absolute worker-turn timeout. It can interrupt a request; use only when needed. |
| `review_seconds` | `null` | Use this allowance for director and independent review calls, within the remaining campaign/finalization budget. |

With `review_seconds: null`, an existing study retains its recorded director allowance;
otherwise the normal turn allowance applies (the study CLI defaults to 600 seconds).
An older saved director policy can therefore still specify 120 seconds. Set an explicit
larger allowance to change it. The optional journal synthesizer keeps its smaller budget.

Changes apply to subsequent calls. A currently running model request keeps its existing
settings. The scientific hypothesis, acceptance rules, experiment timeouts and total
wall/storage/memory allowances do not change.

## Browser

In a study card or its experiment monitor, use **Run settings**, beside the deadline.
Leave a field blank to remove the local worker ceiling or use the recorded review
allowance. Enter a reason and save. The same settings are available to CLI operators
and the research director. Public hosted trials retain their operator-managed service
quotas and do not expose this administrative control.

## Command line

Inspect the effective settings:

```bash
simjecture study limits --campaign /path/to/study
```

Write the requested changes to a JSON file, for example `limits.json`:

```json
{
  "worker_action_limit": null,
  "worker_checkpoint_seconds": null,
  "review_seconds": 900
}
```

Apply it with a reason:

```bash
simjecture study limits --campaign /path/to/study \
  --limits-file limits.json --reason "Allow time to inspect the complete diagnostic"
```

Omitted fields retain their current values; explicit `null` clears an override. Invalid
updates are rejected before persistence. The latest policy is in `operating_limits.json`;
individual changes, reasons and actors are retained under `operating_limit_changes/`.
Resume uses this policy without rewriting the original launch contract.

The director can return an `operating_limits` change in its structured decision. The
host records it separately from scientific acceptance. This authority cannot grant
additional campaign time or waive resource reservations. Storage increases retain
their separate explicit delegation policy.

A private profile's explicit `action_limit` still applies when the study does not
override it. Clear that profile setting as well to rely solely on the campaign budget.

## Model-provider budgets

Both the shared built-in API adapter and the public service now omit `max_tokens`
unless the operator sets an explicit value. Provider defaults and provider limits
still apply; this is not unlimited inference.

Private API profiles can set a positive integer `max_tokens`, an optional positive
`action_limit`, and a positive finite `request_timeout_seconds`. Public profiles also
support role-specific output overrides such as `reviewer_max_tokens` and
`researcher_max_tokens`. Those are deliberate operator allowances, not model defaults.

The built-in request watchdog follows the supplied turn budget unless overridden;
unbounded interactive work uses a 600-second request watchdog. Public requests use
600 seconds by default. Native CLIs retain their own provider transport behavior.
The supervisor's inactivity allowance is separate and remains configurable through
`--turn-seconds`.

Provider failures return to the supervisor's recovery path after the SDK's single
retry, rather than starting hidden library retries or an unlimited model action loop.
A failed reconnect before any new work preserves the previous turn's saved receipts
and private transport context. On controller resume, a verified orphaned director
process is stopped and its known or missing usage recorded; its stale verdict is not
applied.

An empty or truncated reviewer response never counts as approval. Retrying a review
preserves the provider's reasoning mode; the harness no longer silently turns off
DeepSeek thinking for the second attempt.

## Complete evidence, bounded views

Large source files and result documents no longer fail review submission simply
because they exceed 128/256 KiB. Relevant complete files are retained in a
content-addressed `review_objects/` store, with their original SHA256 identities.
Small files can appear inline; large ones have explicit references. When a review
packet is large, the model receives an index into its complete retained form.

The acceptance hash remains bound to the authoritative packet, not its prompt-sized
view. Hashes establish identity, not scientific correctness. Referenced contents are
uninspected until the reviewer reads them; missing inline content is not evidence of
absence or validity.

Built-in API reviewers receive a read-only `read_review_asset` tool. It accepts an
object SHA256, an optional deterministic JSON path and a byte offset, and returns
`next_offset` for further pages. It cannot write files, execute commands, or read a
provider credential file. Native reviewers use their existing read-only file tools;
the prompt supplies the study's object-store location.

Worker file, skill and instrument readers also support offsets. Webpage fetches expose
the next byte offset. These page sizes bound individual messages without making the
rest of a file inaccessible. Remote source paging requires a worker version that
implements the offset argument.

## Console logs and downloads

Managed interactive commands and simulations no longer fail merely because console
output reaches 64 MiB. The controller compresses completed log segments and keeps a
bounded live `output.log`. **Complete console logs** in the run's output panel provides
the retained files. Storage errors still fail explicitly; rotation does not grant disk
space or silently discard diagnostics.

Headless API terminal commands also retain complete console logs and return their
location alongside a bounded excerpt. Large local artifact downloads are streamed;
the previous 64 MiB delivery ceiling no longer applies. Inline figure previews retain
their size guard. Upload quotas, public broker limits and scientific experiment
storage reservations remain separate.

For the preceding source audit, including classic/DSH and public-hosting boundaries,
see [Default limits and their purpose](../reference/default-limits.md).
