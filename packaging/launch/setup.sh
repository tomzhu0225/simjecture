#!/usr/bin/env bash
set -euo pipefail
package_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
release_version="$(cat "$package_root/VERSION")"
for command_name in python3 node npm bwrap; do
  command -v "$command_name" >/dev/null || { echo "Missing prerequisite: $command_name (see INSTALL.md)" >&2; exit 1; }
done
node -e 'const [major, minor] = process.versions.node.split(".").map(Number); if (!((major === 22 && minor >= 19) || major >= 24)) { console.error("DSH requires Node 22.19+ (22.x) or 24+"); process.exit(1); }'
python3 -m venv "$package_root/.venv"
"$package_root/.venv/bin/python" -m pip install "$package_root/packages/simjecture-${release_version}-py3-none-any.whl[dsh]"
mkdir -p "$package_root/run-state"
npm install --prefix "$package_root/run-state/dsh-runtime" --no-audit --no-fund @deepseek-ai/dsh@0.1.5-rc.2
export DSH_HOME="$package_root/run-state/dsh"
export PATH="$package_root/.venv/bin:$package_root/run-state/dsh-runtime/node_modules/.bin:$PATH"
dsh plugin --profile simjecture add @deepseek-ai/dsh-headless@0.1.5-rc.2
dsh plugin --profile simjecture add "$package_root/packages/simjecture-dsh-bundle-${release_version}.tgz"
printf 'Setup complete. Export DEEPSEEK_API_KEY in your terminal, then run ./launch.sh\n'
