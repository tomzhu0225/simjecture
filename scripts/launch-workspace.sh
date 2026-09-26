#!/usr/bin/env bash
# Launch from a source checkout; user research is permanent under artifacts/projects.
set -euo pipefail
simjecture_checkout="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if ! command -v uv >/dev/null 2>&1; then
  echo "Install uv first: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi
cd -- "$simjecture_checkout"
exec uv run --frozen --extra workspace simjecture web --runs-root "$simjecture_checkout/artifacts" "$@"
