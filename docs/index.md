---
hide-toc: true
---

# Autonomous research with inspectable evidence

```{raw} html
<p class="sj-eyebrow">Simjecture · Autonomous numerical research</p>
<p class="sj-lead">Bring a hypothesis and the conditions that matter. Let an agent design experiments, search for counterexamples and test a better explanation—with recorded evidence and independent review.</p>
<div class="sj-actions">
  <a class="sj-button primary" href="getting-started/first-run.html">Run your first investigation →</a>
  <a class="sj-button" href="demos/index.html">Explore recorded studies</a>
  <a class="sj-button" href="https://simjecture.com">Try online ↗</a>
</div>
```

## How research moves forward

```{raw} html
<ol class="sj-loop">
  <li><strong>Frame the question</strong><span>You and the agent agree on the hypothesis, physical scope and budget.</span></li>
  <li><strong>Run experiments</strong><span>The agent chooses methods and runs recorded numerical computations.</span></li>
  <li><strong>Look for a failure</strong><span>Challenge the prediction and check candidate counterexamples.</span></li>
  <li><strong>Commit a repair</strong><span>Preserve the failed claim and state a justified replacement before testing it.</span></li>
  <li><strong>Collect fresh evidence</strong><span>Run the committed tests and challenge the revised prediction.</span></li>
  <li><strong>Review the conclusion</strong><span>A separate context examines the claim, source, results and numerical controls.</span></li>
</ol>
<p class="sj-loop-note">Review gaps return the agent to investigation. Human steering can change the next experiment. The selected completion policy determines whether a falsification finishes the study or starts a repair; the deadline can leave it incomplete.</p>
```

[Understand the loop](concepts/research-loop.md) ·
[See what counts as evidence](concepts/evidence-and-claims.md)

[中文：课题组安装与开发指南](zh-cn/research-group-guide.md)

## See the process in a real record

The [48 hour FRC campaign on eight GPUs](research/frc-48-hour-campaign-20261014.md)
records two days of solver development and numerical controls. It ended with the
merger hypothesis unresolved; its public accounting includes model usage, GPU
allocations and API pricing scenarios.

The fresh v0.7.0 [FLASH island-coalescence study](demos/island-coalescence.md)
falsifies a specified reconnection-rate slope band after numerical qualification
and independent review. Its proposed repair remains unvalidated.

![Fresh FLASH fields and the accepted scaling contrast](_static/demos/fresh-v070-island-fields.png)

The fresh [FLASH-to-WarpX investigation](demos/flash-warpx-patch.md) connects an MHD
current sheet to local kinetic calculations. Two prospective particle seeds and
numerical controls support the finite pressure prediction. Its independent claim
and report reviews are accepted; historical records retain their original outcomes.

The [Qin-1 hardware-to-plasma study](demos/qin1-hardware-plasma.md) follows CAD
and feed redesign through coupled circuit/EM calculations into native 3D plasma
dynamics. Its interactive results show both the stronger cold-conductor field
and the numerical limits on predicted leakage. This is a local toolchain study,
with its execution mode and qualification limits stated explicitly.

For a short, fully inspectable example, the
[orbital-accuracy investigation](demos/kepler-energy.md) found five counterexamples
and supported a narrower claim with fresh numerical tests and independent review.
Ordinary CPU Python is enough to reproduce its experiments.

```{raw} html
<div class="sj-cards">
  <a class="sj-card" href="getting-started/first-run.html"><span class="sj-label">Start investigating</span><strong>From a conversation to a tested claim</strong><p>Prepare a brief, choose a completion policy and follow a study through experiments and review.</p></a>
  <a class="sj-card" href="concepts/evidence-and-claims.html"><span class="sj-label">Understand the record</span><strong>Why should you trust this result?</strong><p>Trace a conclusion to its numerical inputs, outputs, counterexamples and review decisions.</p></a>
  <a class="sj-card" href="how-to/guided-commissioning.html"><span class="sj-label">Bring a scientific tool</span><strong>Start from a working instrument</strong><p>Give the agent a verified example, source access, diagnostics and clear physical limits.</p></a>
  <a class="sj-card" href="how-to/continuation-steering.html"><span class="sj-label">Keep exploring</span><strong>Guide the next experiment</strong><p>Steer at a checkpoint or open a linked continuation with a revised brief and new budget.</p></a>
</div>
```

## Choose your working environment

Use [the hosted workspace](https://simjecture.com) with supplied inference and
compute within usage limits, or [install locally](getting-started/installation.md)
and choose your own API or native CLI agent. You can run ordinary Python studies,
add scientific capabilities, and use [SSH workers](how-to/ssh-workers.md) for
numerical experiments. [Server mode](how-to/public-trials.md) supports an operated
service with per-visitor allowances.

The sidebar identifies the documentation build version. Current walkthroughs and
historical records are labelled separately. See [research status](research/status.md),
[release checks](archive/index.md), or
[contribute a tool or study](https://github.com/tomzhu0225/simjecture/blob/main/CONTRIBUTING.md).

```{toctree}
:hidden:
:caption: Start here

concepts/research-loop
getting-started/installation
getting-started/first-run
getting-started/research-workspace
```

```{toctree}
:hidden:
:caption: Research records

demos/index
research/campaigns
demos/island-coalescence
demos/flash-warpx-patch
demos/qin1-hardware-plasma
demos/kepler-energy
```

```{toctree}
:hidden:
:caption: Understand the system

concepts/evidence-and-claims
concepts/architecture
research/limitations
research/status
```

```{toctree}
:hidden:
:caption: Work with Simjecture

how-to/headless-studies
how-to/projects-and-workspaces
how-to/research-service
how-to/minimal-migration
how-to/continuation-steering
how-to/extend-study
how-to/minimal-oversight
how-to/operating-limits
how-to/research-memory
getting-started/web-interface
```

```{toctree}
:hidden:
:caption: Tools and deployment

how-to/guided-commissioning
how-to/multi-tool-studies
how-to/add-a-capability
how-to/scientific-attention
how-to/quantum-espresso
how-to/deploy-runtimes
how-to/campaign-deployment
how-to/material-eos
how-to/cad-and-simulation
how-to/iter-pack
how-to/windows-applications
how-to/cst-windows
how-to/cylinder-flow
how-to/ssh-workers
how-to/restricted-containers
how-to/public-trials
how-to/llm-bench
```

```{toctree}
:hidden:
:caption: Reference and contributing

reference/cli
reference/default-limits
reference/repository-map
development/contributing
development/documentation
development/releasing
archive/index
```

```{toctree}
:hidden:
:caption: 中文指南

zh-cn/research-group-guide
```
