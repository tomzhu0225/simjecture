# Contribute to Simjecture

Bring a scientific question, a reliable tool, or one improvement that makes the
next investigation easier to run and assess. You do not need a large GPU, paid
model access or a full research campaign to make a useful contribution.

## Find a place to start

| You bring… | A useful first contribution | Start here |
|---|---|---|
| Domain knowledge | Review a diagnostic, numerical control or claim in a recorded study | [Recorded investigations](../demos/index.md) |
| A scientific solver | Provide a working example, readable outputs and a bounded validation case | [Add a capability](../how-to/add-a-capability.md) |
| An experimental workflow | Commission it through the actual launcher, with inputs and diagnostics | [Guided commissioning](../how-to/guided-commissioning.md) |
| A research question | Write the hypothesis, scope and a test that could falsify it | [First investigation](../getting-started/first-run.md) |
| Python or web experience | Reproduce a bug and add a focused fix with a regression check | [Repository map](../reference/repository-map.md) |
| A fresh reader's perspective | Fix an unclear setup step or improve an explanation | [Documentation development](documentation.md) |

[Open an issue](https://github.com/tomzhu0225/simjecture/issues/new/choose) to discuss
a contribution. For a small, clear fix, a pull request with the problem, change
and validation is enough. Discuss new scientific policies or substantial
architecture changes before building them.

## Make a scientific contribution inspectable

A useful tool contribution includes a runnable example, the model's assumptions,
how to read its outputs, and a numerical check whose failure is meaningful.
Identify the upstream source, license and runtime requirements. Operator-supplied
software can be integrated without redistributing its source or binaries.

A useful research record includes the human's question, agent instructions,
software/model identities, actual commands and results, numerical controls and
review decisions. An unresolved result is welcome if the record makes clear what
was learned and what still needs testing. Separate numerical reproduction from
replaying recorded artifacts and from a fresh autonomous study.

The [evidence guide](../concepts/evidence-and-claims.md) explains the contract.
The [FLASH record](../demos/island-coalescence.md) shows why scientific review can
remain useful after a campaign ends; the [Kepler record](../demos/kepler-energy.md)
provides a small example with no-key verification and numerical reproduction.

## Development and credit

[CONTRIBUTING.md](https://github.com/tomzhu0225/simjecture/blob/main/CONTRIBUTING.md)
is the canonical guide for environment setup, checks, pull requests and licensing.
Run the checks relevant to your change and report unavailable prerequisites
separately from passes. Ordinary regression work should not require paid calls.

Keep contributor names and upstream attribution with the relevant tool or study.
In a research record, distinguish human framing, implementation, numerical work,
independent review and later editorial material. Identify the exact Simjecture
version and commit when citing a result. Scientific authorship should reflect
the actual contribution and be discussed with the study's collaborators.
