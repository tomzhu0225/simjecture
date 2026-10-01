# Benchmarking AI for Fusion & Plasma Simulation

## 01-motivation — From fluent answers to usable evidence

An AI assistant can explain a plasma instability beautifully and still leave a researcher without a usable result. In simulation work, somebody has to open the files, understand their units, calculate the right quantities, and leave an analysis that another person can run. That practical gap motivated our benchmark in Simjecture. We used recorded data from an aluminium plasma investigation and tested coding agents on the work between a simulation and a scientific claim. This video presents our own measured results. The wider motivation is AI for fusion and plasma research, while the measurements cover a specific slice of that workflow: reproducible numerical analysis.

---

## 02-tasks — Two tasks, two deadlines

The first task had a three-minute budget. Given two CSV cases, the agent had to compare radiation escaping the domain with energy removed by the radiation operator, and save both results and findings. The second task had fifteen minutes and used HDF5 files from two cylindrical simulations. R Z means radius and axial position. The grids had sixty-four or one hundred and twenty-eight radial cells, with four axial cells, and four hundred and one frames each. The requested diagnostics included inward kinetic energy, compression, event times, radiation windows, and differences between grids. Both tasks analyzed existing output; they did not launch new FLASH or WarpX simulations.

---

## 03-protocol — Measure the whole coding agent

We scheduled forty-two configurations, not forty-two different model weights. Some entries use the same model with different reasoning effort. Native coding agents kept their own tools and system prompts, while API agents used the configured tool adapters. Each attempt started with a fresh conversation and working directory. The independent host ran the submitted reducer and checked three additional numerical holdouts, with inputs kept immutable. The deadline included verification. There were two hundred and fifty-two scheduled attempts. Twenty-four never reached inference because of subscription or quota availability, leaving two hundred and twenty-eight graded attempts. Those availability observations remain visible, but do not count as failures of numerical ability.

---

## 04-short — Correct numbers did not guarantee completion

The short task produced the most revealing separation. Out of one hundred and eighty-eight graded attempts, one hundred completed the full contract. One hundred and sixty-one passed every numerical check. That leaves sixty-one attempts with correct numbers but incomplete delivery. For example, GPT six point one Sol at high effort passed the numerical checks in all five attempts, yet completed none of the full timed submissions. At low effort, it completed all five. Missing findings or incomplete delivery mattered because the researcher needs the whole analysis. This score checks that findings exist; it does not claim an AI judge has validated the scientific quality of that prose.

---

## 05-short-results — Read completion rate alongside speed

On that short task, GPT six Luna at medium effort completed five out of five attempts, with a median verified finish time of seventy-four seconds. Gemini three point eight Flash at medium effort, running through AGY, also completed five out of five, at a median of one hundred and fifty-eight seconds. DeepSeek Flash completed four out of five, with a median successful finish time of fifty-one seconds. That last time summarizes successful attempts, so it needs the four-out-of-five label beside it. A fast successful trial does not erase a failed one. Even five successes provide limited certainty: five out of five has a wide ninety-five-percent Wilson interval, roughly fifty-seven to one hundred percent.

---

## 06-rz — A longer diagnostic task changed the picture

The fifteen-minute R Z task had thirty-four passes among forty graded attempts. Every one of the nineteen tested Codex configurations passed. DeepSeek Flash finished in about one hundred and fourteen seconds. GPT six Luna at medium effort finished in about two hundred and seventy-two seconds. That is a very different picture from the short deadline. However, this was also a different task, so we cannot isolate extra time as the cause of the improvement. And each R Z configuration had just one attempt. These are observed outcomes, useful for deciding what to investigate next, but not enough to establish a stable ordering across scientific problems or repeated runs.

---

## 07-adapters — A result belongs to a model–agent configuration

MiMo version two point six Flash and Pro did not complete either task in the tested API-agent setup. Yet MiMo Flash passed the short task's numerical checks in four of five attempts. On R Z, neither delivered the required bounded, self-contained reducer. DeepSeek used native tool-message history, while the MiMo setup retained the installed tool framework's default history formatter. Those implementation differences are part of what we measured. Grok four point seven gives another useful example: its R Z numbers passed, but the required findings were missing. Calling these models incapable would go beyond the evidence. The actionable question is which configuration reliably delivers this contract within this budget.

---

## 08-bars — Two rankings, with failure kept visible

The publication separates finish time from cost. The first bar chart ranks median verified finish time, with lower values better. The second ranks mean API-equivalent cost per attempt, including recorded spending on unsuccessful attempts. Completion counts stay beside the bars. Unfinished runs appear in red, after completed entries. They have no verified finish-time rank, but their cost bars still show recorded spending. Partial usage records are marked as lower bounds and receive no money rank. Configurations that never reached inference are omitted from these public charts. Actual receipts remain available, so an incomplete run cannot disappear from the spending account.

---

## 09-pareto — Time and money: the upper left is better

The third plot puts money on the horizontal axis and finish time on the vertical axis. Cost grows to the right; elapsed time grows downward. Faster and cheaper therefore means closer to the upper left. Each model has its own color. Dashed lines connect efforts within the same model and coding agent. White rings mark the observed two-objective frontier. In R Z, DeepSeek Flash was faster, at about four point four US cents, while GPT six Luna was cheaper, at about one point two cents. Neither dominates the other on both axes. With one trial each, that frontier is descriptive. It is not a statistically established claim that either configuration is universally superior.

---

## 10-costs — A public price needs trustworthy usage counters

A vendor's public price is only half the calculation. We also need input, cached input, and output counters for the actual run. These costs use dated standard API tariffs with the default cache-adjusted basis, rather than subscription invoices. AGY estimates are explicitly marked because its cache-counter interpretation is uncertain. Interrupted streams can leave a lower bound. Cumulative conversation totals must not be added again whenever an agent resumes, and a final quota error must not erase earlier paid work. Dynamic model routing can also lack a fixed tariff. Keeping estimates, lower bounds, and complete records separate makes the cost plot honest and gives the next benchmark a clearer accounting target.

---

## 11-verifier — The benchmark itself needed scientific controls

The agents also exposed errors in our own reference implementation before the formal sweep. One version depended on the ordering of cells at equal radius. Another multiplied single-precision fields before converting them to double precision. Independent reducers agreed with one another, yet the reference could reject them. We repaired the radius aggregation and interpolation rules, and promoted fields before arithmetic. Closed-form energy and volume checks, permutation controls, and independent summation checks qualified the replacement. The official sweep then used fresh task-pack zero point three trials. Earlier qualification records remain separate. That distinction matters: repairing the referee cannot justify silently turning old failures into new model successes.

---

## 12-outlook — A reproducible starting point for scientific AI

What we have is a small, inspectable benchmark of scientific delivery. It shows why effort, adapter behavior, deadlines, and accounting belong beside model names. It does not yet measure autonomous hypothesis testing, new three-dimensional solver campaigns, tokamak physics, or the correctness of a research conclusion. Those need separate tasks and stronger controls. The source, sanitized grades, and valuation ledger are available on Simjecture's benchmark development branch. The workspace can run a custom model, and community-controlled submissions stay separate from our owned results. The useful next step is to add independent scientific tasks and repeated solver-backed trials, while keeping the evidence traceable. That is how this can grow into a meaningful benchmark for fusion and simulation research.
