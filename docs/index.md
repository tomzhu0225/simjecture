# Simjecture

Simjecture is an evidence-governed runtime for autonomous experimentation and
falsification over hypothesis trees inside a human-defined scientific problem.
It accepts a natural-language hypothesis, lets an agent commission and use
computational instruments, and preserves an independently inspectable path from
proposal to claim disposition.

This documentation describes version 0.1, a research preview. The project
began in computational plasma physics. The same evidence harness is now ready
to extend to other simulation-gated fields. The software has completed real
autonomous CPU and CUDA campaigns, but it does not claim unrestricted
hypothesis solving or empirical closure.

## Choose a starting point

- **No-key tour:** verify and replay the
  [recorded Gray–Scott demo](demos/gray-scott.md); it makes no model calls and
  starts no simulations.
- **New user:** follow [Installation](getting-started/installation.md),
  [First autonomous run](getting-started/first-run.md), and the
  [Web interface](getting-started/web-interface.md). The
  maintenance-mode [Terminal interface](getting-started/terminal-ui.md)
  remains available for SSH and headless operation.
- **Scientist:** read [System architecture](concepts/architecture.md),
  [Evidence and claims](concepts/evidence-and-claims.md), and
  [Scientific limitations](research/limitations.md).
- **Tool author:** start with [Add a capability](how-to/add-a-capability.md) and
  [Guided commissioning](how-to/guided-commissioning.md).
- **Operator:** use [Deploy runtime profiles](how-to/deploy-runtimes.md) to
  provision and verify the core, WarpX CPU, or WarpX CUDA environment.
- **DSH operator:** use [Run a Simjecture campaign under DSH](how-to/deepseek-harness.md)
  to install the native MCP profile and verify its tool boundary.
- **Reviewer:** inspect [Evaluation status](research/status.md),
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
how-to/add-a-capability
how-to/deploy-runtimes
how-to/deepseek-harness
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
research/run-0004
research/next-steps
```

```{toctree}
:hidden:
:caption: Development

development/documentation
development/releasing
```
