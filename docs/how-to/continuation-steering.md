# Continue and steer an investigation

Available in the 0.5.3rc3 preview for minimal studies. The published rc2
installer does not yet include these actions.

## Continue after a deadline or change direction

Open the study in **Autonomous research**, or open its **experiment monitor**.
Choose **Continue investigation**, describe the follow-up, choose a new wall-time
budget and select working files to inherit. Choose **Prepare directly** to review the normal study brief and agent/model
selection, then **Start research**.
Preparation alone starts neither an agent nor a simulation.

The new study links to its parent. Selected programs/readers are copied to
`research/inherited/`. A compact `continuation_input/brief.json` summarizes counts, recent unreviewed
notes and pending reviews. A hash-verified snapshot outside the writable research
folder preserves the original files and a record summary. Large raw results stay
at the parent's receipt paths; move/copy them explicitly if using a different
machine. References do not grant new scientific acceptance. Prior exploration stays
exploration, and old observations cannot satisfy a new prospective commitment.
No prior method approval is automatically imported. Reuse its scoped validation
as context when explaining the next method, instead of repeating irrelevant tests.

The original hypothesis, instructions, reviews and deadline are unchanged. Each
phase has a separate budget and may select a different agent/model. Required
instrument rules are inherited unless explicitly supplied for a new CLI phase.
The parent should remain available for receipt and raw-data inspection. If it is
still active, the handoff captures recorded context at the new phase's launch;
later parent results are not silently imported.

CLI equivalent:

```bash
simjecture study --campaign runs/phase-2 --continue-from runs/phase-1 \
  --instructions-file next-phase.md --inherit-file calculation.py \
  --inherit-file analysis.py --backend builtin --model deepseek-flash \
  --provider-config /private/provider.json --wall-seconds 7200
```

Omit `--hypothesis-file` to retain the original question. Specify a different one
for an explicitly revised question. Configure the execution backend appropriate
to the host. For a new phase the backend is checked afresh. Selected files are
limited to 128 files, 1 MiB each, with a 16 MiB handoff including metadata. Hidden
configuration, known credential filenames, symlinks and `lab.py` are excluded.

## Prepare the continuation with an agent

The continuation dialog also offers **Prepare with agent**. You can leave the
follow-up description blank if you want to discuss the direction first. Select
initial files and a proposed budget, then choose that button to open the chat.

The interactive agent receives a parent-study context file: original question,
previous instructions, limitations and review state, selected files, your guidance
and the proposed budget. It can ask focused questions and call `draft_study` to
prepare or revise the continuation brief. It may refine the inherited file list;
the host checks every selected path against the parent's research workspace.
Parent lineage and the inherited instrument registry survive later chat turns
and agent-written briefs. Prior observations remain context, not fresh evidence.

**Prepare with agent** also appears beside the parent-study link in an existing
continuation conversation, so you can discuss a directly prepared draft later.
If no model is configured, the parent selection is retained: choose the agent in
chat and use that button again. The resulting brief appears in **Autonomous
research**. Preparing in chat uses the selected interactive agent, but starts no
autonomous research allocation; **Start research** remains a separate action.

## Give advice during a study

Choose **Send guidance** beside the study controls. Add an observation, a paper URL,
an alternative interpretation or a suggested experiment. It is queued durably for
the next agent checkpoint. **Operator guidance** shows its timestamp and whether
it has been included in a worker prompt. Delivery does not mean the agent has
implemented the suggestion. Recent guidance is repeated after session recovery,
and independent reviewers also receive the advice with its scope and timestamp.

```bash
simjecture steer --campaign runs/phase-2 \
  --message "Measure boundary Poynting flux independently; do not infer it from energy closure."
```

Guidance is advisory. It does not rewrite commitments, change acceptance rules,
extend time or interrupt active simulations. Use the existing Pause/Stop controls
for execution control. For new requirements, a new hypothesis or more time, use
**Continue investigation**. This keeps the original contracts auditable while
leaving the research agent free to plan its next experiments.

## Review and status recovery

The built-in reviewer now records whether output was empty or truncated and its
provider finish reason. It makes at most two transport attempts per invocation;
a DeepSeek retry disables thinking after an empty/truncated response. Usage includes
both attempts. Persistent failure remains an error, never approval. Invalid
oversight retries back off up to 30 minutes while other research can continue.

Live status reconciles expired budgets and recorded supervisor identity. Final
reports are written on supervisor exit, including an external-error exit. A
continuation does not erase or silently resolve a parent's pending review.
