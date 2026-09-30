# Simjecture

Simjecture is an evidence-governed runtime for autonomous experimentation and
falsification over hypothesis trees inside a human-defined scientific problem.
It accepts a natural-language hypothesis, lets an agent commission and use
computational instruments, and preserves an independently inspectable path from
proposal to claim disposition.

This documentation covers stable 0.5.2 and the 0.5.3rc2 preview. The project
began in computational plasma physics. The same evidence harness is now ready
to extend to other simulation-gated fields. The software has completed real
autonomous CPU and CUDA campaigns, but it does not claim unrestricted
hypothesis solving or empirical closure.

The **0.5.3rc2 preview** adds [SSH experiment workers](how-to/ssh-workers.md),
automatic machine setup, live availability and refreshed research-tool details.
See [preview scope and validation](testing/0.5.3rc2-acceptance.md).

## Choose a starting point

- **No-key tour:** verify and replay the
  [recorded Gray–Scott demo](demos/gray-scott.md); it makes no model calls and
  starts no simulations.
- **New user:** follow [Installation](getting-started/installation.md),
  [Minimal native studies](how-to/research-service.md), and the
  [Web interface](getting-started/web-interface.md). The
  maintenance-mode [Terminal interface](getting-started/terminal-ui.md)
  remains available for SSH and headless operation.
- **Scientist:** read [System architecture](concepts/architecture.md),
  [Evidence and claims](concepts/evidence-and-claims.md), and
  [Scientific limitations](research/limitations.md).
- **Tool author:** start with [Add a capability](how-to/add-a-capability.md) and
  [Guided commissioning](how-to/guided-commissioning.md).
- **Operator:** use [Deploy runtime profiles](how-to/deploy-runtimes.md) to
  provision and verify the core, WarpX, FLASH, equation-of-state, or opacity
  environment. See the [ITER ecosystem pack](how-to/iter-pack.md) for diagnostics,
  IMAS data and guided fusion-solver setup.
- **DSH operator:** use [Run a Simjecture campaign under DSH](how-to/deepseek-harness.md)
  to install the native MCP profile and verify its tool boundary.
- **Simote operator:** use [Simote agent roles](how-to/simote-agent-roles.md)
  to run claim-scoped CLI agents on shared campaigns.
- **Reviewer:** inspect the [MiMo/DeepSeek comparison](research/llm-comparison.md),
  [Evaluation status](research/status.md),
  the [recorded Gray–Scott demo](demos/gray-scott.md),
  the [recorded collisionless GEM demo](demos/collisionless-gem.md),
  [run 0004 audit](research/run-0004.md), and
  [next steps](research/next-steps.md).

```{toctree}
:hidden:
:caption: Getting started

getting-started/installation
getting-started/first-run
getting-started/web-interface
getting-started/research-workspace
getting-started/terminal-ui
```

```{toctree}
:hidden:
:caption: Demonstrations

demos/gray-scott
demos/collisionless-gem
```

```{toctree}
:hidden:
:caption: Explanation

concepts/architecture
concepts/evidence-and-claims
research/limitations
```

```{toctree}
:hidden:
:caption: How-to guides

how-to/guided-commissioning
how-to/restricted-containers
how-to/minimal-oversight
how-to/research-memory
how-to/add-a-capability
how-to/deploy-runtimes
how-to/iter-pack
how-to/deepseek-harness
how-to/dsh-upgrade-assessment
how-to/simote-agent-roles
how-to/ssh-workers
how-to/research-service
how-to/continuation-steering
how-to/llm-bench
```

```{toctree}
:hidden:
:caption: Reference

reference/cli
reference/repository-map
```

```{toctree}
:hidden:
:caption: Research record

research/status
research/llm-comparison
research/run-0004
research/next-steps
research/continuation-steering-rc3
research/stagnation-deep-audit-20260929
research/stagnation-retrospective-20260929
research/stagnation-video-outline-20260929
```

```{toctree}
:hidden:
:caption: Development

development/documentation
development/releasing
testing/rc2-installation-acceptance
testing/rc3-continuation-acceptance
testing/iter-pack-acceptance
testing/0.5.3rc1-acceptance
testing/0.5.3rc2-acceptance
testing/native-api-adapter
testing/ssh-workers-acceptance
testing/mimo-flash-comparison
```
