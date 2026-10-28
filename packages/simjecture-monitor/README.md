# Optional scientific attention tooling

This separately installable package connects Simjecture to a resident scientific
attention model. It contains the versioned observation/action contract, input
compiler, admission checks, authenticated model client and optional GPU scorer.
Ordinary Simjecture installations do not need this package or GPU dependencies.

[Conjecture 1 v0.1](https://huggingface.co/tomzhu0225/Conjecture-1-4B/tree/v0.1)
is an experimental LoRA adapter for the pinned Intern-Decision-4B base. Publication
provides a reproducible checkpoint; a repeatable overall workflow advantage has
not been established. Its option scores are not calibrated incident probabilities.

Install the lightweight client from a Simjecture checkout:

```bash
uv pip install --python .venv/bin/python -e packages/simjecture-monitor
simjecture attention status
simjecture attention example-config --output /absolute/path/attention.json
```

Edit the configuration with the absolute Unix-socket path and private token-file
path of your separately managed model service. The default mode is `shadow`.
`simjecture attention check --config /absolute/path/attention.json` checks readiness
and exact base/adapter identities without downloading a model. To opt in for a
new study, add `--attention-config /absolute/path/attention.json` to the ordinary
`simjecture study` command. Configuration and attempt/request budgets persist
across resumes. `mode: alerts` explicitly permits bounded director requests.

The observer is asynchronous, with one in-flight request. Shadow mode never
calls the host dispatch function. Alert mode checks fresh state, input binding,
visible citations, persistence, duplicate incidents, cooldown and a finite alert
allowance. A durable reservation precedes an attempted dispatch; interruption
never silently repeats an uncertain action. Every response/error and actual
host dispatch is logged separately. Service failure leaves ordinary supervision,
worker help and scientific review in place.

The first normal-study adapter reads bounded public workflow metadata and public
worker events. It does not read private reasoning or infer progress from silence
when timing is unknown. Domain-specific measurements need an instrument producer
for the typed observation contract; generic metadata is not a qualified numerical
diagnostic. Help/director requests can reach the existing director. Repair-judge
and retrieval proposals remain recorded when their host action is unsupported;
this package never grants repair permission or approves scientific claims.

The model service belongs in an explicitly selected GPU environment. The tested
configuration uses the `[model]` extra plus `flash-linear-attention==0.6.0` and
`fla-core==0.6.0`; see the [setup guide](https://drawingsword.com/simjecture/how-to/scientific-attention.html).
Installing the client does not allocate a GPU, install Torch or fetch weights.

The portable runtime was extracted from research commit
`93a5c3b` without importing the experiment drivers, injected faults or machine
allocation scripts. Historical studies and their exact source revisions remain
on the research branches. The [completed comparison](https://github.com/tomzhu0225/simjecture/blob/93a5c3b/research/evaluations/live-state-learning-20261026/CONTINUATION_RESULTS.md)
includes negative/mixed results and known false-alert limitations. New host
integration is software qualification, not a remeasurement of those outcomes.

Run CPU-only contracts/client tests with:

```bash
PYTHONPATH=src:packages/simjecture-monitor/src pytest packages/simjecture-monitor/tests tests/test_research_attention.py
```
