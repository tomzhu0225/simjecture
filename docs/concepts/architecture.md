# How the system fits together

Simjecture separates the agent's freedom to investigate from the authority to
accept a scientific claim. The current default is **minimal** mode, available
through the browser workspace and headless launcher.

## Human direction and study state

A conversation helps prepare the question, scientific scope, operator requirements,
instruments and resource budget. Launching records that brief. The root hypothesis,
requirements, completion policy and deadline stay fixed within the study.

Steering adds visible guidance for the next checkpoint. A continuation creates a
linked phase with its own agreed brief and budget, preserving the previous phase.
See [continuation and steering](../how-to/continuation-steering.md).

## Worker, director and reviewers

| Role | Responsibility | Authority |
|---|---|---|
| Human researcher | Choose the question, assess relevance, guide interpretation | Launch, steer, stop and prepare continuations |
| Research worker | Plan, implement, run experiments, challenge and repair claims | Submit work and request reviews |
| Research director | Assess feasibility, time remaining and scientific coverage | Request a recorded replan and stops of named experiments |
| Methods reviewer | Assess an instrument-backed implementation and commissioning | Approve or return gaps for the proposed method |
| Claim reviewer | Assess whether evidence supports or falsifies the target | Return an explicit scientific verdict |
| Host evidence service | Preserve state and enforce recorded rules | Validate identities, receipts, commitments and completion conditions |

These are responsibilities and separate contexts, not a requirement to buy several
model providers. Worker and reviewer models can be chosen independently. The
[director](../how-to/minimal-oversight.md#research-director-stop-and-replan) does not
accept scientific claims; a strategic decision to continue a calculation is not
methods approval.

## Agent runtime and evidence service

Native agents retain their normal shell, filesystem and configured tools. A
compatible-API worker is also available. The service exposes a compact `lab`
client for recorded experiments, prospective repair commitments, review requests,
notes and progress. See [the minimal-mode API](../how-to/research-service.md).

The host maintains its own ledger and report. It records scientific state from
receipts and review decisions rather than inferring success from an agent's final
message. Review gaps can resume the investigation; transient provider disconnects
retry within the same wall budget. Authentication or exhausted-quota failures
require attention and are reported explicitly.

## Local and remote numerical execution

Experiments can run locally or on selected SSH workers. Their frozen inputs,
resource requests, execution outcomes and retained files share the same research
record. Detached numerical jobs can survive an agent turn or coordinator restart.
An unreachable worker remains operationally uncertain until its job is reconciled.

Slurm submission is not implemented by the current SSH worker adapter. It is a
separate integration opportunity. See [SSH workers](../how-to/ssh-workers.md).

## Execution and trust

Bubblewrap is the default numerical execution backend where the host supports its
namespaces. Explicit cooperative PRoot and native-process backends accommodate
restricted trusted hosts; neither is an OS security boundary. Native agent tools
run with host-account access outside the numerical sandbox.

The public service uses per-visitor ownership, quotas and its separately configured
executor. A private local workspace and a public multi-user service have different
trust assumptions. See [server deployment](../how-to/public-trials.md) and
[security guidance](https://github.com/tomzhu0225/simjecture/blob/main/SECURITY.md).

## Scientific evidence and completion

The [evidence guide](evidence-and-claims.md) explains source/output identity,
methods qualification, counterexample search, fresh repair tests and independent
review. The saved `answer` or `repair` completion policy determines which reviewed
outcomes complete the study. Neither elapsed time nor successful process exit
establishes a scientific answer.

## Other workflows and historical records

Structured and frontier workflows remain explicit launcher choices. DSH and the
legacy campaign kernel retain their own contracts and role interfaces. Existing
studies keep their recorded mode; they are not migrated silently.

The [classic architecture](../archive/classic-architecture.md) and
[classic evidence model](../archive/classic-evidence-and-claims.md) explain those
older records. Their active-time accounting and claim APIs should not be applied
to minimal studies, which use an absolute wall deadline and their own evidence API.
