# Default limits and their purpose

Audited on **17 October 2026**, against commit
[`b3738f5`](https://github.com/tomzhu0225/simjecture/commit/b3738f56b3be71e65886ae49396265ff64834f84).
This is an inventory of first-party limits, not a promise that every limit is well chosen.
The recommendations below are assessments; this audit does **not** change those limits.

**Follow-up repair:** the subsequent [operating-settings changes](../how-to/operating-limits.md)
remove the periodic worker interruption and default action ceiling, preserve reasoning
mode on review retries, add concurrent direction and ranged evidence access, remove the
public adapter's inherited output ceiling, and rotate console logs. The tables below
remain a snapshot of the audited commit, not the current effective defaults.

The most consequential findings are:

- The built-in research adapter's **8,192-token worker / 32,768-token reviewer output ceilings have been removed** in [PR #26](https://github.com/tomzhu0225/simjecture/pull/26). Requests now omit `max_tokens` unless explicitly configured. Provider limits still apply.
- Minimal research still has a **hard-coded 300-second worker slice** and **24 actions per built-in API turn**. These interrupt a turn, not the campaign, but can interrupt reasoning and cause repeated context processing.
- Several source and evidence limits **reject** submissions rather than providing another page. Those are more concerning than ordinary display limits.
- The public service has a **separate model adapter**. Its 4,096/8,192-token defaults remain; the research fix does not cover it.
- There is no single limits policy. Some values are operator settings, two are delegated director decisions, and many are constants scattered across implementations.

## How to read this inventory

**Default** means the value used by the code when no override is provided. Installed configurations can differ. Minimal research, interactive chat, classic/DSH campaigns and the public service do not share every limit. In particular, the public demo's allowances do not limit a local research campaign.

The tables distinguish four effects:

- **Stop/reject:** execution stops or an otherwise legitimate request is rejected.
- **Checkpoint:** a worker turn ends; the campaign may continue from saved state.
- **Excerpt/page:** less information enters a prompt or view; retained files can still contain the complete record.
- **Admission:** a new request is refused or delayed to respect capacity or a budget.

“Fixed” means no supported setting was found at that enforcement point; changing a Python constant manually is not a user-facing override. “Operator” means a CLI argument, profile, manifest or service setting. “Director” means an explicitly delegated, recorded policy change. A timeout on a network request is not the same as a scientific experiment timeout.

Byte units are deliberate: 256,000 bytes differs from 256 KiB. Character limits are not token limits. Where several layers apply, the smallest effective allowance wins.

Coverage: the audit scanned 153 first-party Python files, then checked enforcement sites, JavaScript integrations, browser forms and configuration defaults. It excludes dependency internals, numeric hash/ID truncation used only for identity, and visual layout dimensions. Scientific acceptance thresholds and transfer/display bounds are included separately so they are not misreported as agent termination limits. This is a dated source audit; deployment overrides and future changes require a fresh comparison.

## Research and model execution

Sources: [study CLI][study], [research supervisor][research-supervisor], [shared supervisor][supervisor], [API adapter][api], [finalization][finalization], [provider retries][retry].

| Limit enabled on the relevant path | Default / enforced ceiling | Control and effect | Necessity and recommendation |
|---|---|---|---|
| Research campaign wall budget | CLI: 3,600 s; native launch request inherits 21,600 s | Operator; stop at authorized deadline. Extensions are recorded. | Keep. This represents authorization and cost, not a model capability assumption. Expose remaining time clearly. |
| Turn / inactivity allowance | CLI: 600 s, no greater than initial wall budget | Operator; interpretation depends on transport/activity mode. | Keep an inactivity watchdog, but distinguish inactivity from legitimate long reasoning and network wait. |
| Minimal worker's absolute slice | **300 s**, even if `--turn-seconds` is larger | Fixed; checkpoint/termination of worker process. | **Rework.** Scheduling opportunities are useful; an unconditional five-minute cutoff can waste a long reasoning request. Prefer cooperative checkpoints and budget-aware grace. |
| Built-in API actions per bounded turn | **24**; effectively unbounded when no turn wall budget is supplied | Fixed; checkpoint. Research launches supply a wall budget. | **Make configurable or adaptive.** It is a runaway guard, not evidence that 24 is a good research unit. |
| Research API history retained across turns | One preceding turn's calls/results, plus a fresh durable evidence brief | Fixed policy; excerpt. Older artifacts/journal remain available. | Bound context growth, but measure retrieval/repetition overhead. This is a deliberate memory loss boundary. |
| API output-token allowance after PR #26 | **No Simjecture default cap**; explicit positive-integer `max_tokens` remains supported | Operator profile/request; provider default otherwise. | Keep this behavior. Different providers count reasoning/output differently; no universal 8K assumption is justified. |
| Single API request timeout | Agent: up to 600 s, clipped to remaining turn time; standalone `model_for`: 90 s | Constructor/caller; stop request. | Keep a transport watchdog; make it model-aware. The worker slice can be the tighter bound. |
| SDK transport retries | 1 retry after initial attempt | Adapter setting; network request bound | Prevent hidden retry multiplication. Outer research transport recovery is separate. |
| DeepSeek explicit-completion attempts | 4 attempts in one generation, i.e. initial plus at most 3 follow-ups | Fixed; error if still no usable completion/tool call | Some malformed endings need recovery. Expensive whole-context retries should be visible and configurable. |
| Built-in reviewer attempts | 2 | Fixed; incomplete/truncated responses never count as acceptance | Retain fail-closed acceptance. The retry count should reflect remaining budget. |
| Second DeepSeek reviewer attempt | Forces `thinking: disabled` | Fixed fallback, **a mode restriction rather than a numeric cap** | **Reconsider.** A parser/timeout failure does not establish that less reasoning is appropriate. Record it explicitly. |
| Native Grok judge turns | `--max-turns 1`, with its tools disabled on this judge path | Fixed; reviewer transport restriction | Appropriate only for a supplied, self-contained verdict packet. It restricts independent investigation; do not describe all reviewers as freely tool-using. |
| Director assessment | 120 s per call; ordinarily every 300 s, unchanged-state review interval 900 s | Manifest policy; timeout | Keep review cadence, but **make assessment time configurable**. Frontier reviewers may need longer than two minutes. |
| Claim review transport attempts | 2 per processing pass | Fixed; request stays queued after failure | Keep incomplete reviews from silently approving. Retry scheduling should be bounded by the campaign, not an unexplained universal count. |
| Methods/progress review retrieval | 3 requests per response; initial review plus at most 2 retrieval follow-ups | Fixed; bounded reviewer evidence acquisition | Prevent runaway review cost; **provide pagination and an explicit request-more route** so missing evidence is not mistaken for absence. |
| Consecutive generic supervisor errors | 3 before external-error pause | Fixed; campaign pause | Useful for a broken integration loop. Distinguish these from transient transport errors, which already retry. |
| Transient provider recovery | No fixed total retry count before the campaign deadline; exponential delay capped at 60 s | Deadline bounded | Matches unattended recovery. Authentication/quota/permission failures pause rather than repeatedly spending requests. |
| Worker process termination grace | Typically 5 s before SIGKILL; handoff grace 2 s | Fixed; process lifecycle | A cleanup safeguard. Cooperative state saving should precede termination when possible. |
| Protected report reserve | `min(wall/2, 600, max(120, wall/4))` seconds on normal CLI launch | Launch policy; numerical compute ends before final deadline | Keep a report reserve. Ten minutes is a default, not a scientifically justified maximum for every campaign. Direct service creation may omit this policy. |
| Budget extension metadata | Idempotency key/request ID ≤120 characters, reason ≤2,400, operator identity ≤160; additional hours <10¹⁰⁰ and finite | Fixed validation; latest 8 requests shown in budget status | Metadata/overflow protection, not a practical time allocation. Only the operator grants extra time; existing experiment deadlines do not automatically extend. |
| Analysis during report reserve | Diagnostic execution may use first 40% of reserve | Fixed fraction; execution deadline | Preserve time for review, but replace arbitrary fractions with explicit remaining-work estimates where practical. |
| Report orchestration | Up to 3 draft/analysis passes; draft budget 40%, queued claim review up to 20%; initial report assessment 65% of then-remaining time; one transport retry; revision if >30 s remain | Fixed orchestration inside final budget | Sensible intent, rigid allocation. Measure how often these boundaries cause incomplete reports. |
| Research journal LLM synthesis | Total `min(300 s, 3% campaign budget)`; at most 45 s per call | Fixed; optional synthesis skipped when exhausted | Keep bookkeeping cheap. It must not become the only place an important finding is retained. |
| Director replan gate | Only exploratory diagnostic jobs ≤120 s bypass a pending replan | Fixed; rejects other new jobs until acknowledgement | Keep the stop-and-replan control. The diagnostic exception should be policy-configurable. |

The minimal research path has **no default campaign-wide token or money cap**, no default experiment-count cap, and no default hypothesis-tree-depth cap. Wall time, storage, method review and machine capacity still constrain it. A provider, native agent CLI, scheduler or operator can impose additional limits outside this table.

## Files, tools, context and evidence

Sources: [API tools][api], [images][images], [methods][methods], [research service][service], [retrieved evidence][evidence], [receipts][receipts], [notebook][notebook], [oversight][oversight], [director][director], [journal][journal], [continuation][continuation], [skills][skills].

| Limit | Value / behavior | Control | Necessity and recommendation |
|---|---|---|---|
| API `read_file` | Rejects files >256,000 bytes; directory listing first 20,000 characters | Fixed | Avoid dumping large data into context. **Add ranged reads/search**, rather than requiring shell workarounds for ordinary source files. |
| API terminal command | Default 120 s; clamped to 1–600 s and remaining turn time | Fixed ceiling; caller timeout below it | Good for short commands; unsuitable for long simulation/builds. Managed command/experiment launchers provide longer execution. Make this distinction explicit. |
| API terminal result | Last 24,000 characters of console output | Fixed excerpt | Keep prompt size bounded; persist full logs and return a retrieval reference. A tail can omit the actual error. |
| API public observation/error event | 1,500-character excerpt | Fixed excerpt | Appropriate for UI events, provided the full tool result/receipt remains accessible. |
| API webpage fetch | First 100,000 response bytes; HTTP timeout 30 s | Fixed | Basic network/resource guard. **Expose truncation and allow selected larger/ranged retrieval** for papers and documentation. |
| API skill resource read | 32,000 characters, retaining beginning/end when truncated | Fixed excerpt | Reasonable initial view; add pagination so middle sections are accessible without special handling. |
| Image transport | 4 MiB encoded image file; 16 million pixels; PNG/JPEG/WebP | Fixed; rejects oversize | Keep decode/memory protection; provide explicit downsampling/tiling. These are transport limits, not a scientific image restriction. |
| Method source in review | Code file ≤131,072 bytes (128 KiB) | Fixed; rejects large code source | **Rework.** A legitimate solver/diagnostic can exceed this. Hash the complete source and retrieve selected sections. |
| Method packet | ≤700,000 serialized bytes; code error calls this “700 KiB” | Fixed; rejects submission | Bound prompt construction, but use indexed retrieval rather than rejecting an entire valid method. The code's error unit is inaccurate. |
| Claim review source / packet | Source code ≤128 KiB per file; entire packet ≤1,000,000 serialized bytes | Fixed; rejects submission | **Rework for larger evidence sets.** Completeness/provenance are necessary; arbitrary packet size is not a scientific validity condition. |
| Automatically inspected JSON artifacts | ≤262,144 bytes (256 KiB) in audit, journal and notebook helpers | Fixed; larger files skipped from this inspection | Fine as an initial scan, **not a reason to label large evidence uninspectable forever**. Keep skipped/unknown explicit. |
| Reviewer evidence extraction | JSON file ≤256 KiB; selected serialized value ≤12,000 bytes; available-key preview first 24; default output/missing-output preview first 16 each; error excerpt 350 characters | Fixed; error/selection view | Prevent accidental giant prompts. Allow paged or computed reductions with traceable provenance. |
| Receipt retrieval | Default 16 entries; maximum 32; explicit names ≤16; encoded result ≤12,000 bytes; execution stdout/stderr tail 8,000 characters | Fixed page bounds; caller offset | Keep pages; they do not limit the archived inventory. Expose continuation and avoid treating a page as the complete record. |
| Notebook note | Statement 2,400 characters; 32 experiments; 8 sources, each ≤2,000 characters; 8 alternatives, labels ≤200 / outcomes ≤1,200 characters | Schema/validators; rejects oversize note | Helpful structured memory, but a large argument should be a linked document rather than repeatedly split by hand. |
| Notebook retrieval | Default 20, maximum 100 entries per page | Caller pagination | Keep; not a total notebook limit. |
| Brief serialized size | Default 16,000 bytes; request range 2,048–64,000 bytes | Caller within fixed ceiling | Useful context budget. **Make upper policy model-aware** and tell agents what was omitted. |
| Worker / director brief | Worker 6,000 bytes; director 8,000 bytes | Fixed caller choices | Cheap orientation, but too small as the only view of a complex investigation. Full records must remain retrievable. |
| Brief subsection selection | Up to 12 experiments, 12 notes, 12 audit/trace items, 8 reviews/journal attempts, 6 methods, 2 summaries, 6 progress series before total-size reduction | Fixed excerpt; [detailed selection code][notebook] | Initial navigation only. A fixed “latest N” policy can lose the decisive older case. Prefer relevance plus evidence indexes. |
| Brief text reduction | Hypothesis ≤900 characters initially; alternatives/sources/other fields further shortened when fitting the packet | Fixed excerpt | The original hypothesis remains authoritative. Truncation must never silently replace the scientific contract. |
| Public worker activity passed to oversight | Last 12 actions ×3,000 characters; last 3 messages ×1,600 characters | Fixed excerpt | Good privacy/context boundary; full public transcripts remain on disk. Count real progress independently. |
| Director activity view | Last 3 actions ×1,200 characters; last message ×800 characters; latest 2 decisions | Fixed excerpt | Useful summary, **not enough to establish that work is absent**. Retrieve a longer trace when a decision depends on it. |
| Progress source signature | First 100 eligible source/config files, each ≤128 KiB; recent useful-action hashes 128 | Fixed scan | Avoid expensive scans. **This is a blind spot** for changes outside that subset; use explicit change receipts/indexes. |
| Progress telemetry parsing | Last 256 KiB of monitored log | Fixed tail | Appropriate streaming strategy; use offsets/structured telemetry if the needed record can fall out of the tail. |
| Progress limitations | ≤16 entries, each ≤1,200 characters | Fixed validation | Keep the telemetry envelope compact; link a longer scientific limitations document. |
| Worker wait declaration | Reason 8–2,400 characters; ≤64 receipt IDs per subject type | Fixed validation | Bounded structured scheduling request; allow grouped job manifests if larger campaigns need them. |
| Method limitation descriptions | ≤32 descriptions, each ≤2,400 characters | Fixed validation | Reasonable envelope, not a physical limit. Link longer limitations. |
| Journal synthesis packet / response | ≤24,000 bytes, up to 8 attempts; ≤6 notes, each ≤1,000 characters and ≤8 experiment references | Fixed selection/schema | Keep optional summaries cheap; retain underlying deterministic journal entries. |
| Continuation inheritance | ≤128 selected files, each ≤1 MiB; complete inherited payload ≤16 MiB; preview first 256 eligible files | Fixed; rejects oversize | **Too restrictive for checkpoint inheritance if treated as a data-transfer mechanism.** This is for continuation context; large checkpoints should use separately referenced/staged assets. |

## Experiment storage, machines and SSH

Sources: [service][service], [resource delegation][resources], [registration][registration], [experiment executor][executor], [worker protocol][worker-protocol], [worker][worker], [execution pool][pool], [machine commands][machine-commands], [sandbox][sandbox], [cooperative runner][process-runner].

| Limit | Default / maximum | Control and effect | Necessity and recommendation |
|---|---|---|---|
| Per-experiment storage | 4 GiB, including staged inputs and generated files | Operator policy; director can increase **only when delegated**, delegation defaults off | Keep storage accounting; the default is not suitable for every PIC checkpoint. Explain required bytes before admission. |
| Total research experiment storage | `max(8, 4 × sum(worker.max_jobs)) GiB`; no pool gives 8 GiB | Same delegation | Keep total reservation to prevent parallel jobs exhausting storage. Prefer available-space-aware policy. |
| Minimal experiment per-file size | Same as that experiment's storage allowance | Inherited budget | There is **no separate 512 MiB file cap here now**. Do not confuse this with classic/public limits below. |
| Local frozen experiment memory | 4 GiB at executor's default call boundary | Caller/resource profile; stop | Keep a memory budget, but derive it from an explicit reservation/hardware rather than a hidden universal default. |
| Experiment duration | Service call default 600 s, clipped to compute deadline; remote schema maximum 604,800 s (7 days) | Caller plus operator deadline; remote fixed maximum | Keep authorized deadlines. The seven-day protocol maximum is arbitrary and should not silently prevent longer campaigns/jobs. |
| Default submitted resources | 1 CPU, 1,024 MiB RAM, 0 GPUs | Caller reservation | Necessary accounting, **easy to misuse** with MPI. Validate launcher/resource consistency; do not assume an executable uses all host cores. |
| Manual worker default capacity | 2 CPUs, 4,096 MiB RAM, 2 concurrent jobs, no GPUs | Operator; admission | Safe small defaults, not detected hardware. Automatic provisioning can replace them with detected capacity. |
| Worker schema upper envelopes | 65,536 CPUs, 16 TiB RAM, 256 GPUs, 256 jobs; ≤32 capability directories; ≤256 GPU IDs | Fixed protocol validation | Finite validation envelopes are reasonable. Values should be documented and extensible rather than treated as physical limitations. |
| Remote workspace envelope | 1 MiB–1 TiB, default 4 GiB | Fixed protocol ceiling plus study budget | **Align with delegated storage policy**: granting >1 TiB cannot make a remote request pass this schema. |
| Remote output declarations | ≤20,000 paths/globs | Fixed protocol bound | Avoid huge malformed requests; archived output count is also affected by matching/staging. Consider manifest-based declaration for large campaigns. |
| Worker RPC request | ≤2 MiB | Fixed transport frame | Keep bounded frames, use chunking for large data. |
| Transfer chunk | 1 MiB per upload/fetch operation | Fixed chunk size | **Not a maximum file size.** Large files are transferred in multiple chunks. |
| Remote instrument source read | Default 16,000 bytes; maximum 65,536 bytes; directory listing first 100 entries | Caller within fixed ceiling | Good first page; **add source offsets/pagination** so read-only access can reach the whole file/tree. |
| Remote registration probe | 60 s, 1 attempt | Director can tune timeout/attempts when delegated; new minimal studies enable delegation by default | Keep a bounded handshake, but expensive probes need a recorded increase. Probe failure is not a scientific failure. |
| SSH control request | Default 20 s; status 10 s; scheduling status 5 s | Caller-specific | Prevent a dead SSH endpoint blocking orchestration. Allow realistic high-latency hosts and retry without losing job identity. |
| Setup/provision calls | Usually 600 s; suggestion 15 s; registration/config probe 60 s | Call-site bounds | Builds may need longer. Prefer asynchronous provisioning with progress rather than a larger silent wait. |
| GUI machine setup command | Default 60 s; allowed 1–7,200 s; command ≤32,000 characters | Caller within fixed validation | Keep bounded administrative work. This path is not the scientific experiment's budget. |
| Machine onboarding / availability | SSH address ≤1,000 characters; availability checks use at most 4 concurrent threads | Fixed validation/concurrency | Reasonable control-plane bounds. Probe parallelism should be tunable for large machine pools. |
| Remote status history | Last 100 terminal jobs in worker status | Fixed excerpt | Fine as a status page; does not delete job receipts. Add pagination when needed. |
| Sandbox CPU allowance | `ceil(command_seconds × assigned_cpus) + 1` CPU seconds per process; reserved CPUs validated ≤65,536 | Resource settings / OS | Prevent CPU runaway while allowing multicore work. It is **not an aggregate MPI-tree CPU quota**. |
| Sandbox address-space ceiling | Normal isolated path: configured memory; cooperative/resident-memory-guard path: `2^47` bytes with separate RSS monitoring | OS/runner | Address space and resident memory differ, especially with CUDA/MPI. Keep RSS accounting and state enforcement accurately. |
| Sandbox core dumps | Disabled (`RLIMIT_CORE=0`) | Fixed | Saves potentially huge dumps. Permit an operator debugging override if needed. |
| Cooperative runner RSS | 4 GiB fallback; experiment normally supplies its memory allowance through environment | Operator/caller; stop | Keep host protection; do not mistake the fallback for the actual reservation of every run. |

## Local interactive UI and project assets

Sources: [web server][web-server], [workspace][workspace], [job manager][jobs], [application][application], [project assets][projects], [monitor][monitor], [browser forms][forms].

| Limit | Value | Control/effect | Necessity and recommendation |
|---|---|---|---|
| Ordinary local JSON request body | 64 KiB | Fixed; reject | Reasonable HTTP protection; support linked documents for larger instructions. |
| File-upload/collection body | 96 MiB encoded JSON body | Fixed; reject | Keep transport bound; binary streaming is preferable to base64 JSON for large files. |
| Uploaded decoded file | 64 MiB | Fixed; reject | Fine for small documents, restrictive for simulation data. Add chunked upload and explicit storage admission. |
| Benchmark import body / records | 4 MiB; 1–1,000 reports | Fixed; reject | Sensible batch envelope; allow multiple batches and retain import provenance. |
| Interactive text | General backend text helper 20,000 characters; setup-guidance message 8,000; progress message 2,000; parent instructions 16,000 | Endpoint bounds; reject | Avoid accidental giant prompts. Provide file attachment/reference rather than manual splitting. |
| Conversation fallback | Last 48,000 characters when no resumable native session exists | Fixed excerpt | Recovery fallback, not equivalent to complete session memory. Tell the model/user when history is partial. |
| Project context asset | File-name length ≤500 characters, each file ≤20 MiB; ≤1,024 files and ≤512 MiB total | Fixed; reject | Reasonable document collection defaults; too small for arbitrary scientific data. Separate contextual documents from large datasets. |
| Managed command / simulation duration | Command default 7,200 s, simulation default 3,600 s; maximum 7 days | Caller within fixed maximum | Keep explicit requested time. Explain the difference from synchronous `terminal`. |
| Managed command text | ≤32,000 characters | Fixed; reject | Prefer a versioned script for longer commands. This is reasonable protocol hygiene. |
| Automatic project copy / inherited assets | ≤512 MiB | Fixed; reject; explicit external assets are an alternative | Prevent accidental duplication; expose references/staging rather than presenting this as a solver limitation. |
| Managed job console log | **64 MiB: job fails once log exceeds it** | Fixed; stop | **Rework urgently.** Rotate/spool/compress logs; a verbose scientific code should not lose a valid run because its console is large. |
| Polling console view | Last 24,000 bytes; controller excerpt 2,000 characters | Fixed excerpt | Good UI bounds; retain full logs and let users download/search them. |
| Artifact HTTP delivery | ≤64 MiB per file | Fixed; reject | **Use streaming/range delivery.** Serving a checkpoint should not require reading all of it into memory. |
| Artifact text preview | ≤2 MiB | Fixed excerpt/rejection by preview path | Keep preview bounds, with full download available. |
| Campaign discovery / artifact list | 100 recent campaigns; application artifact list 600; generic listing default 200 | Fixed/page-like display bounds | Appropriate initial UI limits, but add pagination so old work is not hidden. |
| Engine activity view | Last 512 KiB / 80 events; general web activity reader 512,000 bytes; browser legacy view up to 30 activity items | Fixed excerpt | Display only; raw event files remain authoritative. |
| Monitor projection | 80 recent events, 100 projected executions, 12,000-character console excerpt; recent-run discovery default 20 | Fixed display bounds | Keep rendering bounded; make “more” discoverable. These do not authorize deletion. |
| Model discovery | Response ≤2 MiB; first 200 model entries; 10 s HTTP timeout | Fixed | **Page/search large catalogs**; a later model should not become impossible to select merely because it was omitted. |
| CLI discovery / connection check | Usually 15 s for executable/model discovery, 25 s for connection preflight | Fixed timeout | Reasonable startup watchdog; expose a retry/longer timeout for slow backends. |
| Legacy GUI launch field ceilings | Wall ≤7 days; command ≤24 h; workspace/RAM ≤1 TiB; hypothesis/instruction 20,000 characters | Fixed web validation | Backend and UI must agree. These envelopes are arbitrary beyond protocol safety; don't advertise unrestricted budgets. |
| Workspace/project metadata | Identifier 1–100 characters; name 160; description 2,000; instructions 20,000 | Fixed backend validation | Reasonable metadata envelopes; larger supporting context belongs in attached files. |
| Browser form bounds | Legacy campaign ID 128; benchmark model field 160; guidance textarea 8,000; extension reason 2,400 | Fixed UI bounds | Mostly presentation/schema hygiene. A long model identifier should not be limited only by the browser. |
| Browser machine job preview | First 15 jobs | Fixed display excerpt | Fine for a card; provide access to the full queue. |

Interactive local work has **no default overall chat wall-time limit** and the shared API agent has no small action cap when launched without a turn budget. These freedoms do not override managed-job or OS resource limits.

## Public service defaults

Sources: [public worker][public-worker], [public store][public-store], [public workspace][public-workspace], [public lab][public-lab], [broker][broker], [OS limits][lab-child], [public HTTP server][public-server], [OAuth][oauth]. These are code defaults, not a reading of the live website's private settings.

| Limit | Default / maximum | Exceptions/control | Necessity and recommendation |
|---|---|---|---|
| Per-account daily task allowances | Guest: 5 interactive +1 research; member: 20 +2 | Settings; owner has no allowance count cap | Keep fair-use quotas for shared donated compute. Explain reset/usage before launch. |
| Per-job wall time | 600 s | Settings; owner can request unlimited hosted time | Keep public authorization. “Unlimited owner” does not bypass broker command limits. |
| Queue/concurrency | 20 queued globally; 2 running globally; one queued/running task per account | Settings / store policy | Keep capacity admission. Make queue status clear; do not apply these defaults to private SSH campaigns. |
| New guest identities | 10 per IP per day | Store setting/call | Abuse control, but shared university networks can be unfairly blocked. Prefer transparent admission and login alternatives. |
| Model requests | 24 per job; 50 globally per day; 20 globally per minute | Provider settings; owner bypasses job/day limits, **not RPM** | Necessary shared budget control. Values depend on funding/provider, not model intelligence. |
| Token allowance | 200,000 input+output tokens per job | Settings; owner bypasses | Checked before the next request, **not a strict reservation of future output**. It can overshoot on the final request; report actual usage. |
| Public adapter output tokens | **4,096 worker / 8,192 reviewer** | `<role>_max_tokens` in provider settings; owner does not automatically bypass | **Remove these inherited defaults or make them explicit plan limits.** The same reasoning-budget problem as PR #26 remains on this separate path. |
| Prepared request/context size | 240,000 serialized bytes; owner 4,000,000 bytes | Fixed; reject | **Rework into model-aware context handling.** Byte size is a poor proxy for available token context and image payloads. |
| Public API transport | 60 s request timeout; SDK retries 0, outer retry until job deadline | Fixed adapter / deadline | Avoid hidden retry costs; slow reasoning can be wrongly classified as failure. Expose a longer model-appropriate timeout. |
| Public agent actions | Research agent 24; interactive planning agent 12 | Owner effectively unbounded | Keep abuse/budget guard if explicitly part of a plan; avoid claiming equivalent behavior to private research without noting this difference. |
| Tool parallelism | `max_tool_threads=1` | Fixed | Serial execution simplifies budget and artifact ownership. Not inherently necessary if independent tools can be admitted safely. |
| Scientific lab experiments | 6 per job | Settings; owner bypasses | A public allowance, not a research stopping condition. Failed commands also consume records under this counting path. |
| Lab command time | Default 120 s; guest ≤180 s; owner ≤86,400 s | Caller below fixed ceiling | Guest limits fit small demos; unsuitable for meaningful long simulations. Show the restriction before planning. |
| Legacy hosted research storage | 128 MiB per experiment; 512 MiB total on the legacy worker path | Explicit service construction | Tiny demonstration budgets. Do not confuse with minimal research's 4 GiB experiment default. |
| Lab text write | ≤128 KiB per call/file | Fixed; owner included | Too restrictive for large generated input/source. Support staged assets/ranged writes within a total quota. |
| Lab read | Text file ≤8 MiB; default 200 / max 400 lines; returned text ≤40,000 characters | Caller pagination; owner included | Reasonable ranged view; binary/large-file analysis should use a command and retained results. |
| Lab command / declarations | Command ≤12,000 characters; output declarations ≤64; resolved inputs ≤4,096 | Fixed; owner included | Use scripts/manifests for large jobs; unify with the non-public protocol where practical. |
| Public project upload | Base64 string ≤90 MiB; decoded file ≤64 MiB; project total ≤512 MiB | Fixed; signed-in users only | Keep storage admission, add streaming; owner also has these file envelopes. |
| Chat / study input | Message 1–4,000 characters; research question 16–4,000; instruction/constraints 4,000; invitation 128 | Fixed validation | Fine for a free demo, limiting for real research briefs. Link attached documents. |
| Public broker transport | Frame ≤256 MiB | Fixed; owner included | Keep a bounded protocol; stream/chunk large assets. Base64/frame overhead can bind earlier than raw storage limits. |
| Public execution scratch / outputs | ≤512 MiB and ≤50,000 files; unpacked entry ≤128 MiB | Fixed; owner included | Necessary host protection; limits are currently unsuitable for many FLASH/PIC outputs. Advertise the actual demo scope. |
| Public execution individual file | `RLIMIT_FSIZE=128 MiB` | Fixed; owner included | **Unify with storage policy.** A valid result can hit this even with free total space. |
| Public CPU / RAM / GPU | Default 4 CPUs, 4 GiB process-tree RSS; one selected GPU visibility value from configured pool; OpenBLAS threads 1 | Broker settings | Keep capacity reservations. Ensure UI/tool descriptions reflect actual assigned hardware. |
| Public process/file descriptors | `RLIMIT_NPROC=128`, `RLIMIT_NOFILE=256`, core dumps 0; CPU seconds per process `ceil(timeout+10)` | Fixed OS limits; owner included | Host protection, but CPU seconds are **not wall seconds for multithreaded code**. Check this against the four-CPU allocation; MPI can also need more descriptors. |
| Broker connection / cleanup | 30 s initial request timeout; 5 s process wait/cleanup | Fixed | Keep finite cleanup/handshake; separate disconnects from scientific failure. |
| Console / diagnostic trace | Returned console tail 4,000 characters; optional executor trace excerpt 2,000,000 characters | Fixed excerpt | Keep bounded views and complete downloadable logs. Operator trace is optional, not enabled globally. |
| Service admission free disk | At least 1 GiB free by default | Settings | Keep disk reserve; consider projected workspace demand rather than just a fixed free-space threshold. |
| HTTP service concurrency | Uvicorn 100 connections/tasks; 5 s keep-alive | Fixed launch arguments | Ordinary service capacity defaults; tune to host/load and report 503s clearly. |
| Database contention | SQLite busy timeout 30 s | Fixed | Prevent indefinite waits; transactions should remain short. |
| Event feed | 200 events per page | Cursor pagination | Keep; not a total record limit. |
| Guest lifecycle | Lease 180 s; leave grace 30 s | Settings/lifecycle policy | Data-retention rule requested for guests; **not a model budget**. Avoid deleting work during a temporary tab/network interruption. |
| OAuth lifetime / fetch | State 600 s; session cookies 30 days; profile fetch 10 s and ≤256 KiB | Auth policy | Necessary authentication/response bounds; unrelated to research capability. |

## Classic, structured and DSH paths

These apply only when that engine/path is selected. The running built-in minimal API worker does **not** pass through DSH. Sources: [classic config/sandbox][sandbox], [classic launch][classic-launch], [kernel][kernel], [assignment store][assignments], [MCP bridge][mcp], [DSH profile][dsh-profile], [context elision][dsh-context], [role plugin][dsh-roles], [job waiter][dsh-waiter], [numerical plans][parameters], [proposal generation][proposals], [search generation][search].

| Limit | Default / maximum | Necessity and recommendation |
|---|---|---|
| Classic wall/command time | 21,600 s campaign; 600 s per command | Operator-configurable. Keep authorization; avoid transferring small demo defaults to production. |
| Classic storage / individual file / memory | 512 MiB workspace; 64 MiB file; 4 GiB memory | Operator-configurable. **Small for modern simulation**, especially checkpoints; show effective values before launch. |
| Classic tool output | 30,000 characters | Operator-configurable excerpt. Retain raw logs and references. |
| Classic full prompt history | Latest 8 assistant/tool turns; older payloads compacted | Operator-configurable. Useful cost control; verify important evidence survives retrieval. |
| Classic model failures | 3 retries; failover after 2 consecutive failures | Operator-configurable. A bounded local retry policy, distinct from outer persistent recovery. |
| Classic workspace file reads | Up to 400 lines per read | Caller pagination; suitable if the full file stays accessible. |
| Classic linked evidence preview | Up to 8 links and min(tool output cap, 8,000 characters) | Fixed excerpt; include navigation to remaining evidence. |
| Structured/frontier assignment | 80 operations before handoff; assignment schema permits 1–10,000 | Fixed supervisor choice, followed by another assignment. **Not a campaign-wide operation count**; make configurable if it causes churn. |
| Structured next-test memory | Last 12,000 characters | Fixed excerpt. Preserve full handoff file and provenance. |
| Autonomous decision validation | 3 invalid decisions per iteration by default; schema max 10 | Explicit contract setting. Useful broken-output guard, not a scientific result. |
| Kernel final answer | ≤16,384 characters | Fixed rejection. Keep short summary, allow a linked full report instead of requiring scientific reporting to fit this field. |
| Kernel control operation ID | ≤256 characters | Fixed protocol hygiene; reasonable. |
| Kernel feasibility stop assessment | ≤16 jobs, ≤16 alternatives each ≤2,000 characters; feasibility text ≤8,000 | Fixed schema. Reasonable structured summary, with linked detail for larger decisions. |
| Kernel compact snapshots | 12 artifacts, 16 jobs, 4 literature searches, first 5 sources/search; claim summary up to 12 | Fixed excerpt, not archive limit. Provide explicit full/paged retrieval. |
| Kernel compact job values | Stops recursion beyond depth 8; ≤200 mapping/list items; strings ≤4,000 characters; stream tail default 4,000 | Fixed excerpt. Use references for omitted data. |
| MCP result envelope | Default 30,000 characters; environment override range 1,024–1,000,000 | Configurable transport ceiling. Do not silently equate truncated JSON with complete evidence. |
| MCP nested data | Depth 12; ≤500 items; each string ≤16,384 characters | Fixed serialization guard. Keep indexed/raw alternatives. |
| MCP initial hypothesis | ≤16,384 characters | Fixed validation. Reasonable summary envelope; original supporting documents can be external. |
| MCP claim retrieval | Default page 24, max 100; full claims ≤8 | Fixed page/envelope. Full scientific state must remain reachable. |
| MCP role packet | 1 role claim, 2 contracts, 8 evidence entries, 8 validation results; note excerpt 400 characters; claim statement summary 512 | Fixed excerpt/scope. Avoid giant packets, but reviewer must be able to ask for missing evidence. |
| MCP snapshot excerpts | Hypothesis 2,048; instructions 8,192; claim/repair text 256 characters; 8 artifacts; 8 jobs; 3 literature sources | Fixed excerpt. Navigation aids only, never replacement contracts. |
| DSH context elision | Argument and visible-text thresholds 2,000 characters; completed tool exchange retained verbatim for one model request, then compacted | Fixed plugin policy; append-only original events retained. Useful only with retrieval; benchmark information loss/repetition. |
| DSH selected scalar summaries | Stops recursion beyond depth 8; arrays first 30; only selected scalars whose string representation is ≤240 characters | Fixed selection. Larger scalars are omitted, not merely shortened; summaries cannot establish complete diagnostics. |
| DSH summarization override | Specific `deepseek-official/deepseek-v4-flash` matcher: trigger at 50% context, retain 3%, summary output ≤4,096 tokens | Profile setting, **not universal to current DeepSeek aliases**. Update/version-test separately; current built-in research does not use it. |
| DSH role dispatch | Encoded packet ≤80,000 characters; subagent depth 1; repair scientist limited to one repaired scientific child | Fixed plugin boundaries. Claim scope/provenance is useful; rigid branching/depth needs a reason, not just inherited orchestration. |
| MCP call deadline / reconnect | Default 600 s plus 5 s client grace, minimum 1 s; reconnect ≤8 attempts, backoff 0.5–10 s | Environment/profile. Keep transport bounds but coordinate them with actual job deadlines. |
| DSH job waiter | 3 read retries; writer-busy allowance default 15 s; heartbeat 30 s | Retry fixed, timing environment-configurable. Preserve idempotent job identity on failure. |
| Numerical trial plans | Smoke 50 steps; qualification/discovery 1,000 steps; autonomous numerical repairs default 2 failures | Plan parameters. **Preset trial budgets, not a global FLASH/WarpX maximum**. Do not let them substitute for reaching the physical target time. |
| Structured proposal/search output | 16,384 tokens at actual generator defaults; interface protocol defaults 1,024 | Caller configurable. Separate from the shared API fix; expose effective values if this path is used. |
| Proposal/search attempts | 2 regular attempts; proposal escalation 1; search escalation 1 | Generator constructor settings. Reasonable validation guard; budget/model appropriate overrides should be explicit. |

Classic `max_iterations` defaults to **None**: it is not a default-on hard cap. DSH's own provider/context behavior comes from the installed DSH version as well as this plugin; this inventory does not claim to audit the internals of that external package.

## Literature, scientific presets and other adapters

Sources: [literature][literature], [WarpX preset][warpx], [cylinder flow][cylinder], [numerical thresholds][parameters], [Windows bridge][windows], [Windows runtime][windows-runtime], [CST runtime][cst-runtime], [benchmark runner][bench].

| Limit | Default / maximum | Necessity and recommendation |
|---|---|---|
| Literature results | Default 8; request 1–20; authors first 50 | Caller/schema. Fine as a search page; add pagination for systematic review. |
| Literature request | 20 s | Operator/caller. Sensible network watchdog, separate from research time. |
| Literature text fields | Query 500, purpose 1,000; title/snippet/source 1,000; abstract 3,000; URL 4,000; author 300 characters | Fixed schema. Keep metadata small, but fetch full sources rather than inferring from truncated abstracts. |
| Qualified WarpX two-stream preset | Grid 32–4,096; electron particles/cell 16–8,192, ion particles/cell 1–1,024; normalized timestep 0.001–0.2; end time 1–500; diagnostic interval 1–10,000; seed ≤2³¹−1 | Schema-scoped qualification, **not general WarpX capability**. Retain declared tested scope; custom capabilities can support different physics/resolutions. |
| WarpX preset solver/analysis | Poisson tolerance 10⁻¹⁴–10⁻⁴; iterations 10–10,000; fit windows 3–10,000 and other estimator bounds | Qualification defaults/ranges, detailed below. Keep physically/numerically justified conditions distinct from transport limits. |
| WarpX preset physical range | Density 10¹²–10²⁵ m⁻³, thermal speed 10³–2×10⁷ m/s, normalized stream drift 0.1–2, perturbation 10⁻⁷–0.05 | Test-adapter scope. Not grounds for rejecting unrelated custom scientific tools. |
| Numerical acceptance defaults | Residual ≤10⁻⁸; relative energy drift ≤0.01; boundary contamination ≤0.01; numerical damping fraction ≤0.05 | Policy/model values, **not runtime caps**. They require scientific justification per observable; do not assume universal validity. |
| Cylinder-flow launch | 50,000,000 cells maximum by default (`--max-cells`) | Operator configurable. Useful memory guard; estimate required RAM/VRAM and report override. |
| Windows/CST application job | ≤86,400 s; submit/control RPC defaults 600/60 s | Job ceiling fixed, requested duration variable. Arbitrary one-day bound should not be hidden from long studies. |
| Benchmark execution | Explicit task wall budget; verifier timeout ≤120 s normally; fallback verifier 30 s | Benchmark contract. Keep timed ranking reproducible; never apply benchmark deadlines to normal studies. |

The appendix records every Pydantic `Field` upper bound found in first-party Python source, including small metadata envelopes and physical ranges. Fractions bounded by 0–1, byte values bounded by 255, valid TCP ports and positive finite times are type/domain constraints, not automatically arbitrary restrictions on agent autonomy.

## What should change next

1. **Unify a visible limits policy.** Show effective values, inheritance, enforcement layer, and who may change them in CLI, GUI and director packets. Keep owner budgets authoritative; delegate operating limits explicitly.
2. **Stop terminating useful work for scheduling.** Replace unconditional worker slices with cooperative handoff; make API action allowances configurable and preserve transport state on interruption. Evaluate wasted reasoning and cache reuse.
3. **Use provider defaults consistently.** The shared adapter is fixed; audit the public and structured adapters before claiming all backends have equivalent inference budgets. Do not silently disable thinking to obtain a verdict.
4. **Separate evidence integrity from prompt size.** Keep immutable hashes/full records, bounded indexes, ranged source access and reviewer retrieval. A large source file is not invalid science.
5. **Preserve outputs.** Rotate logs; stream/download/chunk files; stage checkpoints by reference. Total storage and memory admission remain necessary.
6. **Measure actual impact.** Record each limit hit with configured/effective value, elapsed time, tokens and recovery outcome. Compare completion, spend and repeated reads before changing defaults further.

Only the output-default fix in PR #26 was implemented as part of this request. The other recommendations above are deliberately left for a separate change and benchmark.

## Schema-bound appendix

The following table is generated from `Field(le=..., lt=..., max_length=...)` declarations. Bounds are active whenever the containing schema is used; a schema's presence does not mean every study uses it. Expressions are shown exactly rather than converted into potentially misleading units.

Assessment codes: **T** = type/physical-domain constraint; **S** = scoped scientific preset needing domain justification; **P** = protocol/metadata envelope, retain a finite envelope but review the value; **R** = research/context restriction to make configurable or replace with retrieval. These assess the kind of bound, not prove the chosen number optimal. Hand-written validators and non-Pydantic limits are covered in the preceding tables.

| Source and field | Default | Enforced upper bound | Assessment |
|---|---|---|---|
| [adapters/warpx.py:104](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L104) · `WarpXPhysicalConfig.reference_density_m3` | `1e+18` | `le=1e+25` | S |
| [adapters/warpx.py:105](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L105) · `WarpXPhysicalConfig.velocity_unit_m_s` | `1000000.0` | `le=20000000.0` | S |
| [adapters/warpx.py:106](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L106) · `WarpXPhysicalConfig.wavenumber_dimensionless` | `0.5` | `le=2.0` | S |
| [adapters/warpx.py:107](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L107) · `WarpXPhysicalConfig.perturbation_amplitude` | `0.02` | `le=0.05` | S |
| [adapters/warpx.py:108](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L108) · `WarpXPhysicalConfig.inner_pair_weight` | `0.5` | `lt=1` | T |
| [adapters/warpx.py:109](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L109) · `WarpXPhysicalConfig.inner_drift` | `0.95` | `lt=1` | T |
| [adapters/warpx.py:110](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L110) · `WarpXPhysicalConfig.outer_drift` | `0.95` | `lt=1` | T |
| [adapters/warpx.py:147](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L147) · `WarpXNumericalConfig.grid_cells` | `64` | `le=4096` | S |
| [adapters/warpx.py:148](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L148) · `WarpXNumericalConfig.electron_macroparticles_per_cell` | `512` | `le=8192` | S |
| [adapters/warpx.py:149](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L149) · `WarpXNumericalConfig.ion_macroparticles_per_cell` | `16` | `le=1024` | S |
| [adapters/warpx.py:150](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L150) · `WarpXNumericalConfig.time_step_omega_pe` | `0.05` | `le=0.2` | S |
| [adapters/warpx.py:151](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L151) · `WarpXNumericalConfig.final_time_omega_pe` | `20.0` | `le=500.0` | S |
| [adapters/warpx.py:152](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L152) · `WarpXNumericalConfig.diagnostic_interval_steps` | `2` | `le=10000` | S |
| [adapters/warpx.py:153](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L153) · `WarpXNumericalConfig.random_seed` | `1` | `le=2147483647` | S |
| [adapters/warpx.py:154](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L154) · `WarpXNumericalConfig.poisson_relative_tolerance` | `1e-10` | `le=0.0001` | S |
| [adapters/warpx.py:155](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L155) · `WarpXNumericalConfig.poisson_max_iterations` | `200` | `le=10000` | S |
| [adapters/warpx.py:156](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L156) · `WarpXNumericalConfig.minimum_diagnostic_samples` | `50` | `le=10000` | S |
| [adapters/warpx.py:161](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L161) · `WarpXNumericalConfig.minimum_window_samples` | `20` | `le=10000` | S |
| [adapters/warpx.py:162](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L162) · `WarpXNumericalConfig.damped_ratio_threshold` | `0.75` | `lt=1` | T |
| [adapters/warpx.py:164](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L164) · `WarpXNumericalConfig.maximum_relative_energy_drift` | `0.01` | `le=1.0` | T |
| [adapters/warpx.py:165](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L165) · `WarpXNumericalConfig.maximum_relative_gauss_residual` | `0.01` | `le=1.0` | T |
| [adapters/warpx.py:166](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L166) · `WarpXNumericalConfig.maximum_relative_charge_imbalance` | `0.01` | `le=1.0` | T |
| [adapters/warpx.py:167](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L167) · `WarpXNumericalConfig.moment_tolerance` | `0.05` | `le=0.5` | S |
| [adapters/warpx.py:168](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L168) · `WarpXNumericalConfig.outcome_tolerance_omega_pe` | `0.02` | `le=1.0` | T |
| [adapters/warpx.py:295](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py#L295) · `WarpXQualifiedScope.maximum_damped_ratio_threshold` | `0.75` | `lt=1` | T |
| [autonomous_research.py:172](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/autonomous_research.py#L172) · `ResearchProblemContract.maximum_invalid_decisions_per_iteration` | `3` | `le=10` | P |
| [benchmarks/electrostatic_pic.py:53](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/benchmarks/electrostatic_pic.py#L53) · `PICNumericalConfig.perturbation_amplitude` | `0.01` | `lt=0.1` | P |
| [benchmarks/electrostatic_pic.py:57](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/benchmarks/electrostatic_pic.py#L57) · `PICNumericalConfig.damped_ratio_threshold` | `0.75` | `lt=1` | T |
| [benchmarks/electrostatic_pic.py:86](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/benchmarks/electrostatic_pic.py#L86) · `PICConfig.stream_drift` | `0.9` | `lt=1` | T |
| [benchmarks/kinetic_sufficiency.py:36](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/benchmarks/kinetic_sufficiency.py#L36) · `GaussianComponent.weight` | `required` | `le=1` | T |
| [campaign_jobs.py:101](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/campaign_jobs.py#L101) · `CampaignJobRequest.operation_id` | `required` | `max_length=256` | P |
| [corrective_audit.py:30](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/corrective_audit.py#L30) · `CorrectiveAuditRecord.reviewer` | `required` | `max_length=200` | P |
| [domains/base.py:39](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/domains/base.py#L39) · `DomainRunSummary.exit_code` | `0` | `le=255` | T |
| [domains/base.py:57](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/domains/base.py#L57) · `DomainEvolutionSummary.exit_code` | `0` | `le=255` | T |
| [domains/kinetic_sufficiency.py:73](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/domains/kinetic_sufficiency.py#L73) · `KineticSufficiencyHypothesisInput.residual_tolerance` | `1e-08` | `le=0.0001` | T |
| [literature.py:30](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/literature.py#L30) · `BoundedAuthor` | `required` | `max_length=300` | P |
| [literature.py:36](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/literature.py#L36) · `LiteratureSource.id` | `required` | `max_length=1200` | P |
| [literature.py:38](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/literature.py#L38) · `LiteratureSource.provider` | `required` | `max_length=100` | P |
| [literature.py:39](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/literature.py#L39) · `LiteratureSource.title` | `required` | `max_length=1000` | P |
| [literature.py:40](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/literature.py#L40) · `LiteratureSource.authors` | `()` | `max_length=50` | P |
| [literature.py:41](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/literature.py#L41) · `LiteratureSource.publication_year` | `None` | `le=3000` | P |
| [literature.py:42](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/literature.py#L42) · `LiteratureSource.doi` | `None` | `max_length=1000` | P |
| [literature.py:43](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/literature.py#L43) · `LiteratureSource.url` | `required` | `max_length=4000` | P |
| [literature.py:44](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/literature.py#L44) · `LiteratureSource.full_text_url` | `None` | `max_length=4000` | P |
| [literature.py:45](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/literature.py#L45) · `LiteratureSource.abstract` | `None` | `max_length=3000` | P |
| [literature.py:46](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/literature.py#L46) · `LiteratureSource.snippet` | `None` | `max_length=1000` | P |
| [literature.py:47](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/literature.py#L47) · `LiteratureSource.source_name` | `None` | `max_length=1000` | P |
| [literature.py:60](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/literature.py#L60) · `LiteratureSearchRecord.requested_results` | `required` | `le=20` | P |
| [mvp_agent.py:157](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/mvp_agent.py#L157) · `MVPSearchLiteratureAction.query` | `required` | `max_length=500` | P |
| [mvp_agent.py:165](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/mvp_agent.py#L165) · `MVPSearchLiteratureAction.purpose` | `required` | `max_length=1000` | P |
| [mvp_agent.py:173](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/mvp_agent.py#L173) · `MVPSearchLiteratureAction.max_results` | `8` | `le=20` | P |
| [mvp_agent.py:185](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/mvp_agent.py#L185) · `MVPReadFileAction.start_line` | `1` | `le=10000000` | P |
| [mvp_agent.py:191](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/mvp_agent.py#L191) · `MVPReadFileAction.line_count` | `None` | `le=400` | P |
| [mvp_claims.py:107](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/mvp_claims.py#L107) · `ClaimEvidenceValidationCheck.json_path` | `required` | `max_length=1024` | P |
| [mvp_claims.py:229](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/mvp_claims.py#L229) · `ClaimInputArtifactProvenance.operation_id` | `None` | `max_length=256` | P |
| [mvp_claims.py:253](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/mvp_claims.py#L253) · `ClaimEvidenceProvenance.operation_id` | `None` | `max_length=256` | P |
| [mvp_claims.py:254](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/mvp_claims.py#L254) · `ClaimEvidenceProvenance.job_id` | `None` | `max_length=256` | P |
| [parameters.py:286](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/parameters.py#L286) · `NumericalDiagnostics.boundary_contamination` | `required` | `le=1` | T |
| [parameters.py:287](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/parameters.py#L287) · `NumericalDiagnostics.numerical_damping_fraction` | `required` | `le=1` | T |
| [parameters.py:294](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/parameters.py#L294) · `NumericalGate.maximum_boundary_contamination` | `0.01` | `le=1` | T |
| [parameters.py:295](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/parameters.py#L295) · `NumericalGate.maximum_numerical_damping_fraction` | `0.05` | `le=1` | T |
| [public/server.py:303](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/public/server.py#L303) · `SessionInput.invitation` | `''` | `max_length=128` | P |
| [public/server.py:308](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/public/server.py#L308) · `JobInput.hypothesis` | `DEFAULT_HYPOTHESIS` | `max_length=4000` | P |
| [public/worker.py:36](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/public/worker.py#L36) · `PICCase.stream_drift` | `0.9` | `le=0.95` | P |
| [public/worker.py:40](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/public/worker.py#L40) · `PICCase.seed` | `7` | `le=1000000` | P |
| [research_control.py:23](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_control.py#L23) · `ExperimentMonitor.quantity` | `'Physical time'` | `max_length=160` | P |
| [research_control.py:24](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_control.py#L24) · `ExperimentMonitor.unit` | `'ns'` | `max_length=40` | P |
| [research_development.py:14](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_development.py#L14) · `SolverDevelopment.rationale` | `required` | `max_length=2400` | P |
| [research_development.py:15](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_development.py#L15) · `SolverDevelopment.preserved_assumptions` | `required` | `max_length=2400` | P |
| [research_development.py:16](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_development.py#L16) · `SolverDevelopment.validation_plan` | `required` | `max_length=2400` | P |
| [research_development.py:17](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_development.py#L17) · `SolverDevelopment.build_experiments` | `factory` | `max_length=16` | P |
| [research_director.py:21](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_director.py#L21) · `TimeRequest.reason` | `required` | `max_length=2400` | P |
| [research_director.py:27](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_director.py#L27) · `DirectorVerdict.rationale` | `required` | `max_length=3000` | P |
| [research_director.py:30](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_director.py#L30) · `DirectorVerdict.stop_experiments` | `factory` | `max_length=8` | P |
| [research_director.py:42](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_director.py#L42) · `DirectorVerdict.report_assessment` | `None` | `max_length=512` | P |
| [research_director.py:47](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_director.py#L47) · `DirectorVerdict.next_action` | `required` | `max_length=2400` | P |
| [research_journal.py:126](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_journal.py#L126) · `SummaryNote.statement` | `required` | `max_length=1000` | P |
| [research_journal.py:127](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_journal.py#L127) · `SummaryNote.experiments` | `required` | `max_length=8` | P |
| [research_journal.py:132](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_journal.py#L132) · `JournalSynthesis.notes` | `required` | `max_length=6` | P |
| [research_notebook.py:23](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_notebook.py#L23) · `ResearchNote.statement` | `required` | `max_length=2400` | R |
| [research_notebook.py:25](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_notebook.py#L25) · `ResearchNote.experiments` | `factory` | `max_length=32` | R |
| [research_notebook.py:26](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_notebook.py#L26) · `ResearchNote.sources` | `factory` | `max_length=8` | R |
| [research_notebook.py:29](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_notebook.py#L29) · `ResearchNote.alternatives` | `factory` | `max_length=8` | R |
| [research_oversight.py:26](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_oversight.py#L26) · `OversightVerdict.evidence_requests` | `factory` | `max_length=3` | R |
| [research_progress.py:21](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_progress.py#L21) · `ProgressRequest.quantity` | `required` | `max_length=160` | P |
| [research_progress.py:22](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_progress.py#L22) · `ProgressRequest.unit` | `required` | `max_length=80` | P |
| [research_progress.py:26](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_progress.py#L26) · `ProgressRequest.series` | `''` | `max_length=160` | P |
| [research_progress.py:27](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_progress.py#L27) · `ProgressRequest.limitations` | `factory` | `max_length=16` | P |
| [research_receipts.py:14](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_receipts.py#L14) · `InventorySelection.names` | `factory` | `max_length=16` | R |
| [research_receipts.py:16](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_receipts.py#L16) · `InventorySelection.limit` | `16` | `le=32` | R |
| [research_registration.py:16](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_registration.py#L16) · `RegistrationTuning.max_attempts` | `required` | `le=sys.maxsize` | T |
| [research_registration.py:17](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_registration.py#L17) · `RegistrationTuning.reason` | `required` | `max_length=2400` | P |
| [research_resources.py:13](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_resources.py#L13) · `StorageIncrease.max_experiment_bytes` | `required` | `le=sys.maxsize` | T |
| [research_resources.py:14](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_resources.py#L14) · `StorageIncrease.max_total_bytes` | `required` | `le=sys.maxsize` | T |
| [research_resources.py:15](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_resources.py#L15) · `StorageIncrease.reason` | `required` | `max_length=2400` | P |
| [review_evidence.py:17](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/review_evidence.py#L17) · `EvidenceRequest.experiment` | `required` | `max_length=100` | P |
| [review_evidence.py:18](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/review_evidence.py#L18) · `EvidenceRequest.output` | `None` | `max_length=256` | P |
| [review_evidence.py:19](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/review_evidence.py#L19) · `EvidenceRequest.path` | `None` | `max_length=1024` | P |
| [search.py:73](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/search.py#L73) · `SymmetricMixtureCandidate.inner_pair_weight` | `required` | `lt=1` | T |
| [search.py:74](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/search.py#L74) · `SymmetricMixtureCandidate.inner_drift` | `required` | `lt=1` | T |
| [search.py:75](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/search.py#L75) · `SymmetricMixtureCandidate.outer_drift` | `required` | `lt=1` | T |
| [search.py:166](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/search.py#L166) · `BlindedSearchRequest.evaluations_per_method` | `8` | `le=64` | P |
| [worker_protocol.py:24](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L24) · `Resources.cpus` | `1` | `le=65536` | P |
| [worker_protocol.py:25](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L25) · `Resources.memory_mb` | `1024` | `le=16 * 1024 ** 2` | P |
| [worker_protocol.py:26](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L26) · `Resources.gpus` | `0` | `le=256` | P |
| [worker_protocol.py:34](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L34) · `WorkerConfig.capabilities` | `factory` | `max_length=32` | P |
| [worker_protocol.py:35](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L35) · `WorkerConfig.cpus` | `2` | `le=65536` | P |
| [worker_protocol.py:36](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L36) · `WorkerConfig.memory_mb` | `4096` | `le=16 * 1024 ** 2` | P |
| [worker_protocol.py:37](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L37) · `WorkerConfig.gpu_ids` | `factory` | `max_length=256` | P |
| [worker_protocol.py:38](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L38) · `WorkerConfig.max_jobs` | `2` | `le=256` | P |
| [worker_protocol.py:60](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L60) · `AutomaticSetup.cpus` | `None` | `le=65536` | P |
| [worker_protocol.py:61](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L61) · `AutomaticSetup.memory_mb` | `None` | `le=16 * 1024 ** 2` | P |
| [worker_protocol.py:62](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L62) · `AutomaticSetup.max_jobs` | `None` | `le=256` | P |
| [worker_protocol.py:64](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L64) · `AutomaticSetup.capabilities` | `factory` | `max_length=32` | P |
| [worker_protocol.py:70](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L70) · `Machine.label` | `''` | `max_length=160` | P |
| [worker_protocol.py:72](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L72) · `Machine.host` | `''` | `max_length=253` | P |
| [worker_protocol.py:73](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L73) · `Machine.port` | `22` | `le=65535` | T |
| [worker_protocol.py:74](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L74) · `Machine.user` | `''` | `max_length=64` | P |
| [worker_protocol.py:104](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L104) · `Experiment.outputs` | `required` | `max_length=20000` | P |
| [worker_protocol.py:106](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L106) · `Experiment.timeout` | `required` | `le=604800` | P |
| [worker_protocol.py:107](https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py#L107) · `Experiment.workspace_bytes` | `4 * 1024 ** 3` | `le=1024 ** 4` | P |

[api]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/workspace_agent.py
[study]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/study.py
[research-supervisor]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_supervisor.py
[supervisor]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/agent_supervisor.py
[finalization]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_finalization.py
[retry]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/provider_retry.py
[images]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/workspace_images.py
[methods]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_methods.py
[service]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_service.py
[evidence]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/review_evidence.py
[receipts]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_receipts.py
[notebook]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_notebook.py
[oversight]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_oversight.py
[director]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_director.py
[journal]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_journal.py
[continuation]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_continuation.py
[skills]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/mvp_skills.py
[resources]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_resources.py
[registration]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/research_registration.py
[executor]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/experiment_executor.py
[worker-protocol]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/worker_protocol.py
[worker]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/execution_worker.py
[pool]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/execution_pool.py
[machine-commands]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/web/workspace_machines.py
[sandbox]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/mvp_agent.py
[process-runner]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/process_runner.py
[web-server]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/web/server.py
[workspace]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/web/workspace.py
[jobs]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/web/jobs.py
[application]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/web/application.py
[projects]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/workspace_projects.py
[monitor]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/mvp_monitor.py
[forms]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/web/static/workspace.html
[public-worker]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/public/worker.py
[public-store]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/public/store.py
[public-workspace]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/public/workspace.py
[public-lab]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/public/lab.py
[broker]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/public/lab_broker.py
[lab-child]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/public/lab_child.py
[public-server]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/public/server.py
[oauth]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/public/oauth.py
[classic-launch]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/mvp_launch.py
[kernel]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/campaign_kernel.py
[assignments]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/role_assignments.py
[mcp]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/mcp_server.py
[dsh-profile]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/integrations/dsh/cordis.patch.yml
[dsh-context]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/integrations/dsh/context-elider.js
[dsh-roles]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/integrations/dsh/roles.js
[dsh-waiter]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/integrations/dsh/job-waiter.js
[parameters]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/parameters.py
[proposals]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/proposals.py
[search]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/search.py
[literature]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/literature.py
[warpx]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/adapters/warpx.py
[cylinder]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/cylinder_lbm.py
[windows]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/windows.py
[windows-runtime]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/windows_runtime.py
[cst-runtime]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/cst_windows.py
[bench]: https://github.com/tomzhu0225/simjecture/blob/b3738f56b3be71e65886ae49396265ff64834f84/src/conjecture_solver/llm_bench/runner.py
