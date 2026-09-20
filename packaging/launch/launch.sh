#!/usr/bin/env bash
set -euo pipefail
package_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -x "$package_root/.venv/bin/simjecture" || ! -x "$package_root/run-state/dsh-runtime/node_modules/.bin/dsh" ]]; then
  echo 'Run ./setup.sh first (see INSTALL.md).' >&2
  exit 1
fi
export DSH_HOME="$package_root/run-state/dsh"
export PATH="$package_root/.venv/bin:$package_root/run-state/dsh-runtime/node_modules/.bin:$PATH"
mkdir -p "$package_root/campaigns"
cd "$package_root/campaigns"
exec "$package_root/.venv/bin/simjecture" web "$@"
