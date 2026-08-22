---
name: scientific-markdown
description: Write human-facing scientific claims, evidence contracts, laboratory notes, evidence assessments, and conclusions in readable Markdown when equations, symbols, code identifiers, or structured reasoning benefit from formatting. Do not use it to replace machine-readable evidence or validation checks.
---

# Scientific Markdown

Use restrained Markdown in the natural-language string fields of actions:
claim `statement` and `rationale`, evidence-contract prose, evidence notes,
`research_note`, closure reasons, and `final_answer`. The surrounding action
must remain one valid JSON object; never wrap that JSON object in a Markdown
code fence.

- Write code identifiers, paths, estimator names, and exact scalar labels as
  inline code, for example `` `energy_drift` `` or `` `result.json` ``.
- Write inline mathematics as `$R = \mu_1/\mu_{20}$` and display mathematics
  between `$$` delimiters when it materially improves readability. Remember to
  escape backslashes correctly inside the JSON string returned to the harness.
- Use short lists or a small table when several outcomes or controls must be
  compared. Keep a simple claim statement as a sentence rather than forcing a
  heading-and-list template onto it.
- Use fenced code only for a short excerpt needed to explain an interface or
  equation implementation. The workspace source and evidence artifact remain
  authoritative.
- Do not emit raw HTML. The human interface sanitizes Markdown and renders
  supported TeX notation as MathML.

Formatting never changes scientific semantics. Preserve estimator identity,
units, normalization, component/sign convention, and time/window rules as
exact machine-readable scalars in evidence summaries and prospective
`validation_checks`. Do not hide a decision threshold only in a table, equation,
emphasis, or prose. A rendered contract is a human view of the same durable JSON
contract, not a substitute for it.
