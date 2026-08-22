# Security policy

## Supported version

The latest commit on `main` is supported during the 0.1 research-preview phase.

## Reporting a vulnerability

Do not open a public issue for credential exposure, sandbox escape, arbitrary
host execution, or another security-sensitive defect. Contact the maintainer
privately through the GitHub account associated with this repository. Include a
minimal reproduction, affected commit, and impact assessment when possible.

## Credential boundary

Provider credentials belong only in process environment variables or an
untracked local secret manager. They must never be written into prompts,
workspaces, run artifacts, documentation examples, tests, or Git history. The
agent sandbox intentionally receives no provider credentials or host network
namespace.

## Local web boundary

The version 0.1.1 web interface is a loopback-only operator tool, not a hosted
or multi-user service. It must not be exposed through a reverse proxy or public
port. Mutating requests require the per-process browser control token, and
agent-authored artifacts are delivered under a restrictive content-security
policy. Use `simjecture web --read-only` when presenting or reviewing a record.
