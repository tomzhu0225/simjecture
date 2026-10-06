# Host public trials

The optional `serve` command provides the normal Simjecture workspace at
`/` and `/workspace`, backed by a tenant-scoped hosted service. Conversations, study
preparation, live experiment monitoring and evidence browsing use the shared
interface. The host assigns the model and installs the available scientific tools.
Visitors cannot change providers, install global tools or configure SSH. Signed-in
visitors can upload scientific files. A commissioned general executor can run
agent-authored Python, custom solver inputs and private application builds.
The existing `simjecture web` remains a localhost operator tool; its unrestricted
backend and control token are never proxied to visitors.

## Deployment

```bash
pip install 'simjecture[public]==0.6.0'
simjecture serve --root /srv/simjecture-public/data --port 8788
```

Run under a dedicated unprivileged account. Keep installed application code
read-only to that account, make the state directory mode 0700, and put an HTTPS
reverse proxy or named Cloudflare Tunnel in front of the loopback listener.
`--development-http` relaxes secure cookies for local browser testing only.
For general scientific execution, use the private Unix socket profile below;
the server refuses the TCP profile when that executor is enabled.

Set `settings.json` in the state directory:

```json
{
  "public_origin": "https://simjecture.example.org",
  "max_active_jobs": 2,
  "max_queue": 20,
  "wall_seconds": 600,
  "experiments_per_job": 6,
  "guest_interactive": 5,
  "guest_research": 1,
  "member_interactive": 20,
  "member_research": 2,
  "owner_github_ids": [],
  "tools_registry": "/opt/simjecture-public/tools/registry.json",
  "guest_ephemeral": true,
  "guest_leave_grace_seconds": 30,
  "guest_lease_seconds": 180,
  "minimum_free_bytes": 1073741824
}
```

An optional `invitation` limits session creation to invited testers. Otherwise,
visitors receive private, opaque cookie sessions without registration. Guest
allowances are keyed to the client address; verified members have account allowances
shared across browsers. Each interactive turn or study consumes its own allowance
when admitted, over a rolling 24-hour window. Cancelling a queued task refunds its
reservation. Logging in does not erase already charged guest usage. When the
connector is local, Cloudflare's client-address header supplies that connection
identity. This assumes the loopback port is accessible only to the trusted
connector/operator, not arbitrary remote clients.

The HTTP app owns a singleton admission dispatcher. SQLite transactions protect
global slots across requests. Jobs wait durably, and the scientific execution
budget starts at admission. Detached job processes survive a web-server restart;
process identity checks avoid treating a reused PID as the original worker.
An interrupted worker is reported explicitly and its evidence is retained.

Guest pages renew a lease while open. Closing the last tab requests cleanup after
a 30-second grace period; missing heartbeats expire after 180 seconds. Other tabs,
refreshes and an active GitHub sign-in protect the session. Cleanup cancels live
work, confirms its workers have stopped, removes scientific files/artifacts and
conversation content, and revokes the cookie. Minimal allowance/usage counters
remain to prevent quota resets. Signed-in projects persist across closing tabs.
Uploads require verified sign-in and a session control token, accept up to 64 MiB
per file and are limited to the visitor's own project. Artifact clicks download
by default; safe raster images have a separate preview response. HTML/SVG are not
served as active same-origin documents.

## GitHub sign-in and owner access

Register a GitHub OAuth app with the callback
`https://YOUR_HOST/api/auth/github/callback`. Sign-in uses state bound to the initiating
browser, PKCE, a verified GitHub email and the provider's immutable account ID.
The application rotates its session and CSRF tokens on sign-in. Projects remain
private and become available on other browsers signed into the same account.
GitHub access tokens are used only to verify identity and are not stored.

The running server accepts the OAuth client ID and secret through the private
mode-0600 Unix socket `<state-directory>/.oauth-inlet.sock`. A local operator sends
a newline-terminated JSON object with `client_id` and `client_secret`; only the
server user or root can provision it. The credentials remain in server RAM and
are never written to configuration files. After a server restart, provision them
again to enable new sign-ins; existing verified sessions remain valid.

List owner **numeric GitHub IDs** in `owner_github_ids`. Names, browser fields and
user-supplied launch parameters never grant this tier. Owners have no hosted
interactive/research quota, request/token allowance, simulation-count limit or
campaign wall-time cutoff. A time budget of zero explicitly means unlimited;
a positive owner budget is still honored. Evidence-service leases renew while an
unbounded worker is alive. Shared concurrency, rate limiting, numerical parameter
ranges, per-experiment protection and the provider's actual available credit still
apply. Usage is recorded for owners as well as visitors.

## Inference

Numerical reproductions need no model key. To enable AI investigations, create a
private mode-0600 `provider.json` outside visitor project directories:

```json
{
  "public_enabled": true,
  "base_url": "https://openrouter.ai/api/v1",
  "api_key": "YOUR_APPLICATION_API_KEY",
  "model": "YOUR_TESTED_FREE_MODEL_ID",
  "daily_requests": 50,
  "requests_per_minute": 20,
  "requests_per_job": 24,
  "tokens_per_job": 200000
}
```

Choose a provider plan that permits application-backend use. Personal coding
subscriptions are not automatically eligible. Pin and test the model rather than
silently changing it between requests. Set the account's own provider spending
limits too if using paid inference: these application token limits stop subsequent
calls after reported usage reaches the allowance and are not an invoice ceiling.

Worker and reviewer requests share the same durable allowance. Failed attempts
consume request reservations; SDK/library retries are disabled. The host retries
transient network/server failures within the same deadline and allowances, recording
each attempt. Authentication and exhausted quota failures stop explicitly.
Reported input/output tokens, cache and reasoning usage where supplied, context sizes,
finish reasons, request identifiers and roles are retained privately. Keys and raw
provider-error bodies are not returned by the public API. Exhaustion is explicit;
there is no automatic switch to a paid model.

Optional `researcher_request_parameters` and `reviewer_request_parameters` supply
provider-specific request fields from the operator's private configuration. For
example, MiMo supports `{"thinking":{"type":"disabled"}}` for a short public trial.
These settings are never supplied by visitors. Identical source text is sent once
per review, with references to the complete frozen source. The original evidence
packet remains authoritative for the verdict fingerprint; compaction does not
change scientific data. Truncated reviewer output never approves a claim.

## Scientific execution profiles

Without a general executor, hosted workers can run only the qualified native
examples registered by the operator. Templates describe the demonstrated setup;
installation alone never establishes arbitrary physics capability. The obsolete
electrostatic-PIC entry is not shown in the Research tools catalogue.

With a qualified executor, `write_file`, `read_file` and `run_command` support
general Python, numerical solvers, custom initial conditions and application builds.
Installed templates are starting points. FLASH binaries are still application
specific: use an appropriate build or compile a private source copy. Installed
solver sources and guidance remain read-only; generated inputs and analysis live
in the visitor's project. An empty output list is valid for inspections, whose
console is recorded. Declared numerical output files must actually be created.
Native examples return project-relative paths to their raw output archive so
follow-up HDF5/Python analysis does not need access to host experiment directories.

The Linux lab broker is a separate operator-owned service. It authenticates the
gateway over a group-restricted Unix socket, reserves a dedicated non-login UID
per command, then drops privileges and enforces Landlock, seccomp and resource
limits before executing code. Enforcement failure stops the command. The tested
profile supports CUDA and compiler jobs on a namespace-restricted Linux host.
It limits CPU affinity, processes, memory, wall time, file size and temporary
storage, including shared-memory objects. All processes using the reserved UID
are stopped before output collection and UID reuse. File collection rejects
symlinks/hardlinks; console collection reads original open descriptors.

This profile provides filesystem/UID/syscall confinement and **does not provide
a network namespace**. Internet tools are available. Use a dedicated compute host
with appropriately protected network services; stronger isolation can use a
separate VM/container fleet. The private operator workspace is not a tenant API.

Example operator configuration (adapt paths, UID reservations and GPU IDs):

```json
{
  "socket": "/run/simjecture-executor/lab.sock",
  "gateway_uid": 998,
  "gateway_gid": 998,
  "uids": [73000, 73001],
  "work_root": "/srv/simjecture-labs",
  "cpus": 4,
  "memory_bytes": 4294967296,
  "gpu_ids": ["0", "1"],
  "path": "/opt/science/bin:/opt/simjecture/venv/bin:/usr/bin:/bin",
  "read_only": ["/usr", "/bin", "/lib", "/lib64", "/etc", "/proc", "/sys", "/opt/science", "/opt/simjecture"]
}
```

Protect this configuration and installed application code from scientific jobs.
The reserved accounts must be named `simjecture-lab-*`; run the broker as root
under a service manager:

```bash
python -I -m conjecture_solver.public.lab_broker --config /etc/simjecture-executor.json
```

Commission through the same launcher and non-root gateway account before adding
`executor_socket`, `executor_qualified: true`, `source_roots` and `guides_root`
to hosted settings. Add only operator-authorized scientific reference folders;
respect the supplied source/data licences. Keep the provider/OAuth state outside
those roots. Run the gateway with:

```bash
simjecture serve --root /srv/simjecture-public/data \
  --unix-socket /srv/simjecture-public/data/http.sock
```

The connector shares the gateway account and proxies to
`unix:/srv/simjecture-public/data/http.sock`. Scientific UIDs cannot access that
private socket or spoof a trusted loopback admission address. Disable obsolete
TCP/quick-tunnel listeners when switching profiles.

General commands use the existing minimal `ResearchService`, frozen inputs and
runtime/source/executor provenance. A failed command cannot be accepted as
successful numerical evidence; retries get fresh receipts. Campaign briefs are
frozen at queuing, including requirements and the selected cutoff. A separate
scientific reviewer uses the existing claim rules. Interactive findings and
numerical readiness checks are labelled separately from accepted claims.

In Research tools, **Custom study · prepare with agent** opens a conversation
to choose physics, geometry and diagnostics. **Starter presets** execute an
installed starting configuration; they do not limit the general executor's
questions. `run_command` defaults to `kind="command"` for analysis, plotting,
compilation and inspection; the agent supplies `kind="simulation"` for solver
or numerical integration runs. This category is recorded independently of
declared output files. Older untyped custom executions appear in Commands;
their original receipts remain unchanged. Hosted commands show only their
retained outputs, while local commands that use a shared project folder keep
that distinction visible.

Optional native examples use an operator-owned `tools_registry` file. An entry
is admitted only after qualification through the same recorded experiment launcher
under the public service account. Binaries and templates are pinned by hash; the
agent may supply only validated scalar parameters. Runtime changes require
requalification. A solver installation is not advertised as arbitrary physics:
each entry declares its application, geometry, model assumptions and numerical range.

The initial native set contains FLASH Sod (1D), Orszag–Tang MHD (2D) and Sedov
(RZ); WarpX CUDA Langmuir-wave examples in 1D, 2D, RZ and 3D; and the CHERAB,
Raysect and IMAS analytic diagnostics demo. FLASH radiation research builds are
preserved separately until their inputs and analysis have a qualified hosted
entry. GPU examples serialize through a service-owned lease. Every native
experiment preserves the realized input, diagnostic source, executable identity,
metrics, plot, provenance and raw-output archive. Reduced energy totals are
selected by their header labels; an open RZ boundary is not described as a closed
energy balance. Numerical readiness does not itself approve a scientific claim.

Results belong to the visitor's session. Artifact downloads check ownership and
the recorded hash. Browser text is rendered as text rather than executable HTML.
Signed-in state and logs remain on the host; operators manage account retention
and backups. Guest scientific content follows the cleanup policy above.

## Existing GitHub Pages domain

A GitHub Pages path such as `drawingsword.com/simjecture/` can host an introduction
and a link or redirect. GitHub Pages cannot run the Python application. A separate
hostname such as `simjecture.drawingsword.com` can route to the application while
the root domain continues to serve the personal site.

Cloudflare's free named-tunnel custom hostname requires the domain to be managed
on Cloudflare. Preserve the existing GitHub Pages and mail records if moving DNS.
Quick Tunnels provide temporary HTTPS preview addresses and are not a permanent
deployment: a restarted connector may receive a different hostname.

See [Cloudflare setup](https://developers.cloudflare.com/tunnel/get-started/).

## Connect an Aliyun-registered domain

Registration can stay at Aliyun. Add the domain to Cloudflare on the Free plan,
then replace its nameservers in Aliyun's **domain registration** console:
**域名列表 → 管理 → DNS管理 → DNS修改**. The separate **云解析 DNS → 解析设置**
page edits individual records and is not the nameserver control. Use the exact
two nameservers assigned to the domain in Cloudflare.

An empty new domain can proceed through **Add records later**. Once nameservers
are active, authorize `cloudflared tunnel login`, create a named tunnel, and route
the apex and `www` hostnames to it. Configure ingress to the loopback public
listener with an `http_status:404` fallback, and supervise the connector under the
same unprivileged deployment account. Give each concurrently running connector a
different explicit loopback metrics port.

Set `public_origin` to the canonical HTTPS address after confirming the named
tunnel works. The public app redirects the matching `www` hostname to that origin.
Verify HTTPS, visitor admission, queue execution and artifact retrieval through
the domain before retiring the temporary preview. Tunnel credentials stay private
and are independent of the model key. DNS delegation and website records do not
change requirements associated with the actual hosting region.

See [Aliyun's nameserver instructions](https://help.aliyun.com/zh/dws/user-guide/modify-dns-server)
and [Cloudflare Tunnel DNS records](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/dns/).
