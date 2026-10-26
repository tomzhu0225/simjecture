#!/usr/bin/env bash
set -euo pipefail
package_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
release_version="$(cat "$package_root/VERSION")"
if [[ $# -ne 0 ]]; then
  echo 'Setup takes no options. DSH was removed; use minimal research.' >&2
  exit 2
fi
for command_name in python3 bwrap; do
  command -v "$command_name" >/dev/null || { echo "Missing prerequisite: $command_name (see INSTALL.md)" >&2; exit 1; }
done
python3 -m venv "$package_root/.venv"
"$package_root/.venv/bin/python" -m pip install "$package_root/packages/simjecture-${release_version}-py3-none-any.whl[workspace]"
printf 'Setup complete. Log in with your chosen native agent CLI, then run ./launch.sh\n'
