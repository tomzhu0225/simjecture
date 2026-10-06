# Security policy

## Supported versions

This is a research project, not a hardened multi-tenant service. Report issues
against the exact package version and Git commit, and identify the execution
backend. Stable releases and previews can have different security-relevant
features. The repository does not promise a long-term security-maintenance window
for older releases. Check current release notes and maintainer guidance before
deploying sensitive workloads.

## Reporting a vulnerability

Do not open a public issue for credential exposure, sandbox escape, arbitrary
host execution, or another security-sensitive defect. Use a private contact
method published by the repository maintainer, or GitHub's **Report a vulnerability**
option if the repository offers it. If neither is available, request a private
reporting channel without including vulnerability details. In the private report,
include a minimal reproduction, affected commit, and impact assessment when possible.

## Credentials and execution boundaries

Keep provider credentials out of prompts, source control, shared artifacts and
public test fixtures. CLI agents use their own credential stores. The built-in
workspace connection stores its user-supplied key in a private mode-0600 server
file; protect that file and backups, and never publish the workspace directory.

Numerical experiments default to network-isolated Bubblewrap with a clean child
environment. This does not enclose the native research agent, which retains its
host tools and is a trusted same-account process. Explicit cooperative PRoot and
native process execution are **not OS security boundaries**: host networking is
shared and declared read-only inputs are checked rather than protected against
hostile same-account code. Native execution has direct host filesystem access;
reference runtime/source protection depends on host permissions. Run cooperative code only on a
dedicated non-root account without unrelated sensitive files. See
[restricted hosts](docs/how-to/restricted-containers.md) for probe requirements.
Do not treat either a successful benchmark or an execution receipt as a security
certification for hostile code.

## Local web boundary

The `simjecture web` interface is a loopback-only operator tool, not a hosted or multi-user
service. Do not expose it through a public port or reverse proxy. Use SSH port
forwarding for remote access. Mutating requests require the per-process browser
control token, and agent-authored artifacts are delivered under a restrictive
content-security policy. Use `simjecture web --read-only` when reviewing a record;
review record contents for private data before sharing them.

## Optional hosted service

`simjecture serve` is a separate, quota-controlled tenant service introduced in
0.6.0. It shares presentation assets with the operator workspace, not its API or
control token. Projects, uploads, jobs and verified artifact downloads check
visitor/account ownership. Model and installation settings remain operator-owned.
GitHub identity is verified server-side; owner privileges require an explicitly
configured immutable account ID. OAuth client credentials remain in RAM and must
be provisioned again after a restart.

General code execution is opt-in and requires a separately commissioned Linux
broker and a private Unix HTTP gateway. The broker drops to a reserved job UID and
enforces Landlock, seccomp and resource limits before executing code. It fails
closed, kills all processes using that UID before collecting files, rejects
symbolic/hard links and reads console output through its original descriptors.
Never expose the gateway's trusted client-address path over a localhost TCP port
that scientific jobs can access.

This namespace-independent profile is not a network namespace, a hardware GPU
partition or an external security certification. Protect other network services
on the dedicated host. Keep application/configuration code operator-owned, and
exclude credentials and unrelated personal data from allowed scientific source
roots. See [server deployment](docs/how-to/public-trials.md) for configuration,
guest cleanup, identity, budgets and qualification requirements.
