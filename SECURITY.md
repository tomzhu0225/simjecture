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
