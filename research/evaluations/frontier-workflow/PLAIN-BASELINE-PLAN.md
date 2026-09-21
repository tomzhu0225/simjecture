# Plain codex-glm baseline after prompt audit

Audit found empty base_instructions.text in all 26 available native sessions from
the previous two pilots. Replacing that base with an empty file is therefore an
explicit configuration check, not removal of a previously present coding persona.
Codex still supplies skill/permission context, environment and native tool schemas.

Run the same two mathematical hypotheses directly with GLM 5.3 and native tools,
without Simjecture's tool adapter, role assignments, contract approvals or review
queue. Give each a 900-second maximum, fresh thread, at most two concurrently;
allow natural completion rather than forcibly resuming a finished response.
Use an explicit empty model_instructions_file and inspect native session metadata
to verify the override was applied. If the CLI rejects an empty file, record that
failure before selecting any replacement. Do not change account-wide config.

Require executable standard-library calculation code, task/rows JSON matching
the original numerical schema, a finite-domain conclusion, limitations, and an
explicit tested repair of the false Euler claim. Independently rerun the source,
check all specified cases and review the numerical argument. This measures
mathematical deliverable completion, not kernel-accepted scientific completion.
One run per task is a diagnostic baseline, not statistical evidence of superiority.
Keep native tool availability and existing login; do not infer provider billing
from reported token counters. Preserve raw outputs privately.

Preflight: both explicit empty-file launches exited with CLI error before creating a model session. The baseline therefore uses the existing model-default empty base, verified from native session metadata; no non-empty substitute is introduced. Failed launch records are retained privately.
