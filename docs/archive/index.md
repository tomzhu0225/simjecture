# Research and release archive

These records describe a particular release, experiment or audit at the time it
was performed. They preserve the original scope, measurements and limitations;
they are not setup instructions or evidence that a check passed on your current
host. Existing record URLs are retained.

For current tasks, start with the [workspace walkthrough](../getting-started/research-workspace.md)
or [how-to guides](../index.md). Release changes have one home
in [CHANGELOG.md](https://github.com/tomzhu0225/simjecture/blob/main/CHANGELOG.md);
GitHub Releases use the matching changelog section. The
[evaluation overview](../research/status.md) separates demonstrated behavior from
open scientific goals.

## Release acceptance

These pages are indexed automatically from their dated acceptance records.
They retain the versions and commands actually tested.

```{toctree}
:glob:
:maxdepth: 1

../testing/*acceptance
```

## Model evaluations and adapter checks

For current benchmark instructions and interpretation, use the
[benchmark guide](../how-to/llm-bench.md).

- [Owned benchmark sweep, 2026-10-01](../testing/owned-llm-benchmark-20261001.md)
- [Native API adapter checks](../testing/native-api-adapter.md)
- [MiMo/Flash comparison checks](../testing/mimo-flash-comparison.md)
- [Guided model comparison](../research/llm-comparison.md)
- [DSH upgrade assessment](../how-to/dsh-upgrade-assessment.md)

```{toctree}
:hidden:

../testing/owned-llm-benchmark-20261001
../testing/native-api-adapter
../testing/mimo-flash-comparison
../research/llm-comparison
../how-to/dsh-upgrade-assessment
```

## Campaign audits and historical plans

The original [classic architecture](classic-architecture.md) and
[classic evidence model](classic-evidence-and-claims.md) explain historical
campaigns. Current studies are introduced in [the research loop](../concepts/research-loop.md).

```{toctree}
:hidden:

classic-architecture
classic-evidence-and-claims
```

Original scientific records remain intact. Read each report's qualifications and
corrections together with the claimed result.

- [Run 0004 audit](../research/run-0004.md)
- [Demo refresh and harness audit, 2026-10-08](../research/demo-audit-20261008.md)
- [Historical next-step plan](../research/next-steps.md)
- [Continuation and steering research note](../research/continuation-steering-rc3.md)
- [Stagnation deep audit, 2026-09-29](../research/stagnation-deep-audit-20260929.md)
- [Adaptive aluminium campaign audit, 2026-10-04](../research/adaptive-campaign-audit-20261004.md)
- [Z-pinch execution and timestep repair qualification, 2026-10-03](../testing/zpinch-repair-qualification-20261003.md)
- [Research director and adaptive FLASH qualification, 2026-10-03](../testing/research-director-adaptive-20261003.md)
- [Stagnation retrospective, 2026-09-29](../research/stagnation-retrospective-20260929.md)
- [Stagnation video outline, 2026-09-29](../research/stagnation-video-outline-20260929.md)

```{toctree}
:hidden:

../research/run-0004
../research/demo-audit-20261008
../research/next-steps
../research/continuation-steering-rc3
../research/stagnation-deep-audit-20260929
../research/adaptive-campaign-audit-20261004
../testing/zpinch-repair-qualification-20261003
../testing/research-director-adaptive-20261003
../research/stagnation-retrospective-20260929
../research/stagnation-video-outline-20260929
```
