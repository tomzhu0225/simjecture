# Simjecture documentation

Simjecture helps you turn a scientific question into recorded experiments,
counterexample searches and independently reviewed claims. The browser workspace
is the recommended starting point. Use a compatible API model or an installed
native agent CLI; terminal automation is also supported.

These guides cover **Simjecture 0.6.0**, including the shared local/hosted workspace
and optional server mode. See the [release checks and limits](testing/0.6.0-acceptance.md)
or [try the hosted workspace](https://simjecture.com).

## Start in the workspace

1. [Install Simjecture](getting-started/installation.md) on Linux or WSL
2. Follow the [workspace walkthrough](getting-started/research-workspace.md) to
   choose an agent, start a conversation and prepare a study
3. Try a [small first investigation](getting-started/first-run.md), then inspect
   its experiments and review

Want to look around first? The [recorded Gray–Scott demo](demos/gray-scott.md)
can be verified and replayed without an API key or new simulations.

## Solve a specific task

- **Automate a study:** [headless CLI workflow](how-to/headless-studies.md)
- **Continue or guide work:** [continuation and steering](how-to/continuation-steering.md)
- **Prepare a scientific instrument:** [guided commissioning](how-to/guided-commissioning.md),
  [runtime deployment](how-to/deploy-runtimes.md), [ITER pack](how-to/iter-pack.md)
- **Use remote compute:** [SSH workers](how-to/ssh-workers.md) and
  [restricted hosts](how-to/restricted-containers.md)
- **Inspect a study:** [web monitor](getting-started/web-interface.md),
  [methods and progress oversight](how-to/minimal-oversight.md),
  [research memory](how-to/research-memory.md)
- **Compare models:** [benchmark guide and community results](how-to/llm-bench.md)
- **Extend the harness:** [add a capability](how-to/add-a-capability.md) or
  [contribute](https://github.com/tomzhu0225/simjecture/blob/main/CONTRIBUTING.md)

## Understand the evidence

Read [architecture](concepts/architecture.md),
[evidence and claims](concepts/evidence-and-claims.md),
[evaluation status](research/status.md) and
[scientific limitations](research/limitations.md) for what the harness records,
what has been demonstrated and what still needs scientific judgment.

Current guides describe supported workflows and identify version-specific
features where needed. Dated audits, model comparisons and acceptance checks live
in the [research and release archive](archive/index.md). Release changes are in
[CHANGELOG.md](https://github.com/tomzhu0225/simjecture/blob/main/CHANGELOG.md).

```{toctree}
:hidden:
:caption: Getting started

getting-started/installation
getting-started/research-workspace
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
research/status
```

```{toctree}
:hidden:
:caption: How-to guides

how-to/headless-studies
how-to/research-service
how-to/continuation-steering
how-to/guided-commissioning
how-to/restricted-containers
how-to/minimal-oversight
how-to/research-memory
how-to/add-a-capability
how-to/deploy-runtimes
how-to/iter-pack
how-to/ssh-workers
how-to/public-trials
how-to/llm-bench
how-to/deepseek-harness
how-to/simote-agent-roles
```

```{toctree}
:hidden:
:caption: Reference

reference/cli
reference/repository-map
```

```{toctree}
:hidden:
:caption: Development

development/documentation
development/releasing
testing/0.6.0-acceptance
```

```{toctree}
:hidden:
:caption: Archive

archive/index
```
