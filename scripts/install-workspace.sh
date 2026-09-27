#!/usr/bin/env bash
# Simjecture's public Linux/WSL installer. No Git, Python, uv or CLI agent required.
set -euo pipefail
SIMJECTURE_VERSION=0.5.2rc2
simjecture_install_dir="${SIMJECTURE_INSTALL_DIR:-$HOME/simjecture}"
simjecture_python="${SIMJECTURE_PYTHON:-3.12}"
simjecture_start=1
simjecture_system=1
simjecture_port=8765
while (($#)); do
  case "$1" in
    --no-start) simjecture_start=0; shift ;;
    --no-system-packages) simjecture_system=0; shift ;;
    --port) simjecture_port="${2:?Provide a port}"; shift 2 ;;
    --help)
      cat <<'HELP'
Install Simjecture and start its localhost GUI (Linux / WSL).
Usage: bash install.sh [--no-start] [--port 8765] [--no-system-packages]
SIMJECTURE_INSTALL_DIR selects the permanent installation/results folder (default ~/simjecture).
Python 3.12 and uv are installed automatically. On Debian/Ubuntu, apt installs
Bubblewrap and PRoot when root or sudo is available. Restricted root installations
use a dedicated non-root account and /srv/simjecture by default, with a warning.
Other hosts can configure their experiment execution backend separately.
The web server binds to localhost. SSH forwarding instructions are printed.
HELP
      exit 0 ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done
if [[ ! "$simjecture_port" =~ ^[0-9]{1,5}$ ]] || ((10#$simjecture_port < 1 || 10#$simjecture_port > 65535)); then
  echo 'Choose a port between 1 and 65535.' >&2; exit 2
fi
simjecture_port=$((10#$simjecture_port))
if [[ "$(uname -s)" != Linux ]]; then
  echo 'Run this installer inside Linux or WSL.' >&2; exit 1
fi
if [[ -L "$simjecture_install_dir" || ( -e "$simjecture_install_dir" && ! -f "$simjecture_install_dir/.simjecture-bootstrap" ) ]]; then
  echo "Destination already exists and is not installer-managed: $simjecture_install_dir" >&2
  echo 'Choose an unused folder with SIMJECTURE_INSTALL_DIR; existing work will not be overwritten.' >&2
  exit 1
fi
simjecture_scratch="$(mktemp -d)"
trap 'rm -rf -- "$simjecture_scratch"' EXIT
trap 'echo "Installation interrupted or failed. Saved research is preserved; rerun to retry." >&2' ERR
simjecture_fetch() {
  if command -v curl >/dev/null 2>&1; then
    curl --fail --location --show-error --silent --retry 2 "$1" -o "$2"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "$1" -O "$2"
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c 'import sys, urllib.request; urllib.request.urlretrieve(sys.argv[1], sys.argv[2])' "$1" "$2"
  else
    echo 'Install curl or wget to download the release.' >&2; return 1
  fi
}
simjecture_source="${SIMJECTURE_SOURCE_DIR:-}"
if [[ -z "$simjecture_source" && -n "${BASH_SOURCE[0]:-}" ]]; then
  simjecture_candidate="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
  if [[ -f "$simjecture_candidate/pyproject.toml" && -f "$simjecture_candidate/uv.lock" ]]; then
    simjecture_source="$simjecture_candidate"
  fi
fi
if [[ -z "$simjecture_source" ]]; then
  simjecture_release="${SIMJECTURE_RELEASE_BASE:-https://github.com/tomzhu0225/simjecture/releases/download/v$SIMJECTURE_VERSION}"
  simjecture_archive="simjecture-$SIMJECTURE_VERSION-workspace.tar.gz"
  echo "[1/4] Downloading Simjecture $SIMJECTURE_VERSION…"
  simjecture_fetch "$simjecture_release/$simjecture_archive" "$simjecture_scratch/$simjecture_archive"
  simjecture_fetch "$simjecture_release/SHA256SUMS" "$simjecture_scratch/SHA256SUMS"
  awk -v name="$simjecture_archive" '$2 == name {print}' "$simjecture_scratch/SHA256SUMS" > "$simjecture_scratch/checksum"
  [[ -s "$simjecture_scratch/checksum" ]] || { echo 'Release checksum is missing.' >&2; exit 1; }
  (cd "$simjecture_scratch" && sha256sum --check checksum)
  mkdir "$simjecture_scratch/source"
  tar -xzf "$simjecture_scratch/$simjecture_archive" -C "$simjecture_scratch/source" --strip-components=1 --no-same-owner
  simjecture_source="$simjecture_scratch/source"
else
  echo "[1/4] Using supplied Simjecture source: $simjecture_source"
fi
for simjecture_item in pyproject.toml uv.lock src skills capabilities environments; do
  [[ -e "$simjecture_source/$simjecture_item" ]] || { echo "Incomplete source: $simjecture_item is missing" >&2; exit 1; }
done
# Namespace-restricted root logins need a non-root execution account. Handle
# this before installing Python, so nothing depends on traversing /root.
if [[ "$EUID" == 0 ]] && ! { command -v bwrap >/dev/null 2>&1 && bwrap --unshare-all --ro-bind / / /bin/true >/dev/null 2>&1; }; then
  if ! command -v proot >/dev/null 2>&1 && ((simjecture_system)) && command -v apt-get >/dev/null 2>&1; then
    apt-get update && apt-get install -y bubblewrap proot
  fi
  if command -v proot >/dev/null 2>&1 && command -v useradd >/dev/null 2>&1 && command -v runuser >/dev/null 2>&1; then
    simjecture_service_user=simjecture
    simjecture_service_home=/var/lib/simjecture
    if ! id "$simjecture_service_user" >/dev/null 2>&1; then
      useradd --system --create-home --home-dir "$simjecture_service_home" --shell /usr/sbin/nologin "$simjecture_service_user"
    fi
    [[ "$(id -u "$simjecture_service_user")" != 0 && "$(getent passwd "$simjecture_service_user" | cut -d: -f6)" == "$simjecture_service_home" ]] || {
      echo 'The simjecture account already exists with another home; choose a normal user installation.' >&2; exit 1;
    }
    if [[ -z "${SIMJECTURE_INSTALL_DIR:-}" ]]; then
      simjecture_install_dir=/srv/simjecture
    fi
    simjecture_install_dir="$(realpath -m "$simjecture_install_dir")"
    case "$simjecture_install_dir" in /root|/root/*)
      echo 'Non-root execution cannot access /root. Choose SIMJECTURE_INSTALL_DIR=/srv/simjecture.' >&2; exit 1;;
    esac
    if [[ -e "$simjecture_install_dir" ]]; then
      [[ -f "$simjecture_install_dir/.simjecture-bootstrap" && -f "$simjecture_install_dir/.service-user" && "$(cat "$simjecture_install_dir/.service-user")" == "$simjecture_service_user" ]] || {
        echo "Existing installation left unchanged: $simjecture_install_dir. Choose an unused installation folder." >&2; exit 1;
      }
    fi
    mkdir -p "$simjecture_install_dir"
    simjecture_service_cleanup() {
      if [[ -f "$simjecture_install_dir/.root-launcher.previous" ]]; then
        mv -T "$simjecture_install_dir/.root-launcher.previous" "$simjecture_install_dir/start-workspace"
      else
        rm -f -- "$simjecture_install_dir/start-workspace"
      fi
      chown root:"$simjecture_service_user" "$simjecture_install_dir"
      [[ -z "${simjecture_stage:-}" ]] || rm -rf -- "$simjecture_stage"
      rm -rf -- "$simjecture_scratch"
    }
    trap simjecture_service_cleanup EXIT
    chown "$simjecture_service_user:$simjecture_service_user" "$simjecture_install_dir"
    chmod 750 "$simjecture_install_dir"
    printf 'Simjecture bootstrap installation\n' > "$simjecture_install_dir/.simjecture-bootstrap"
    chown "$simjecture_service_user:$simjecture_service_user" "$simjecture_install_dir/.simjecture-bootstrap"
    printf '%s\n' "$simjecture_service_user" > "$simjecture_install_dir/.service-user"
    if [[ -f "$simjecture_install_dir/start-workspace" ]]; then
      mv "$simjecture_install_dir/start-workspace" "$simjecture_install_dir/.root-launcher.previous"
    fi
    simjecture_stage="$(mktemp -d "$simjecture_service_home/installer-source.XXXXXX")"
    tar -C "$simjecture_source" --exclude='.git' --exclude='.venv' --exclude='artifacts' \
      --exclude='.private' --exclude='.runtime' --exclude='__pycache__' --exclude='node_modules' \
      -cf - pyproject.toml uv.lock README.md LICENSE src skills capabilities environments integrations scripts \
      | tar -xf - -C "$simjecture_stage"
    chown -R "$simjecture_service_user:$simjecture_service_user" "$simjecture_stage"
    simjecture_child_env=("HOME=$simjecture_service_home" "USER=$simjecture_service_user" "LOGNAME=$simjecture_service_user" "PATH=$simjecture_service_home/.local/bin:/usr/local/bin:/usr/bin:/bin" "LANG=C.UTF-8" "SIMJECTURE_SOURCE_DIR=$simjecture_stage" "SIMJECTURE_INSTALL_DIR=$simjecture_install_dir" "SIMJECTURE_PYTHON=$simjecture_python" "SIMJECTURE_SSH_LOGIN=${SIMJECTURE_SSH_LOGIN:-${SUDO_USER:-root}}")
    for simjecture_env_name in HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY http_proxy https_proxy all_proxy no_proxy SSH_CONNECTION SIMJECTURE_SSH_HOST; do
      [[ -z "${!simjecture_env_name:-}" ]] || simjecture_child_env+=("$simjecture_env_name=${!simjecture_env_name}")
    done
    echo "Namespace isolation is unavailable. Installing under the dedicated $simjecture_service_user account in $simjecture_install_dir."
    echo 'WARNING: Cooperative PRoot execution is not a security sandbox; use trusted code only.'
    if ! (cd "$simjecture_service_home" && runuser -u "$simjecture_service_user" -- env -i "${simjecture_child_env[@]}" bash "$simjecture_stage/scripts/install-workspace.sh" --no-start --no-system-packages --port "$simjecture_port"); then
      exit 1
    fi
    mv -T "$simjecture_install_dir/start-workspace" "$simjecture_install_dir/.workspace-launcher"
    {
      printf '#!/usr/bin/env bash\nset -euo pipefail\n'
      printf 'if [[ "$EUID" == 0 ]]; then exec runuser -u %q -- %q "$@"; fi\n' "$simjecture_service_user" "$simjecture_install_dir/.workspace-launcher"
      printf 'exec %q "$@"\n' "$simjecture_install_dir/.workspace-launcher"
    } > "$simjecture_install_dir/start-workspace"
    printf '%s\n' "$simjecture_service_user" > "$simjecture_install_dir/.service-user"
    chown root:"$simjecture_service_user" "$simjecture_install_dir" "$simjecture_install_dir/start-workspace" "$simjecture_install_dir/.service-user"
    chmod 750 "$simjecture_install_dir"
    chmod 755 "$simjecture_install_dir/start-workspace"
    rm -f -- "$simjecture_install_dir/.root-launcher.previous"
    rm -rf -- "$simjecture_stage" "$simjecture_scratch"
    trap - EXIT
    if ((simjecture_start)); then
      exec "$simjecture_install_dir/start-workspace" --port "$simjecture_port" --no-open
    fi
    exit 0
  fi
fi
mkdir -p "$simjecture_install_dir"
simjecture_install_dir="$(cd "$simjecture_install_dir" && pwd)"
printf 'Simjecture bootstrap installation\n' > "$simjecture_install_dir/.simjecture-bootstrap"
simjecture_app="$simjecture_install_dir/app/$SIMJECTURE_VERSION"
if [[ ! -f "$simjecture_app/.source-complete" ]]; then
  mkdir -p "$simjecture_app"
  tar -C "$simjecture_source" --exclude='.git' --exclude='.venv' --exclude='artifacts' \
    --exclude='.private' --exclude='.runtime' --exclude='__pycache__' --exclude='node_modules' \
    -cf "$simjecture_scratch/source-copy.tar" \
    pyproject.toml uv.lock README.md LICENSE src skills capabilities environments integrations scripts
  tar -xf "$simjecture_scratch/source-copy.tar" -C "$simjecture_app"
  touch "$simjecture_app/.source-complete"
fi
mkdir -p "$simjecture_install_dir/.runtime" "$simjecture_install_dir/artifacts"
if [[ ! -e "$simjecture_app/.runtime" ]]; then
  ln -s "$simjecture_install_dir/.runtime" "$simjecture_app/.runtime"
fi
echo '[2/4] Preparing uv and Python…'
if command -v uv >/dev/null 2>&1; then
  simjecture_uv="$(command -v uv)"
elif [[ -x "$HOME/.local/bin/uv" ]]; then
  simjecture_uv="$HOME/.local/bin/uv"
else
  simjecture_fetch https://astral.sh/uv/install.sh "$simjecture_scratch/install-uv.sh"
  UV_NO_MODIFY_PATH=1 UV_INSTALL_DIR="$HOME/.local/bin" sh "$simjecture_scratch/install-uv.sh"
  simjecture_uv="$HOME/.local/bin/uv"
fi
"$simjecture_uv" python install "$simjecture_python"
echo '[3/4] Installing locked Simjecture dependencies…'
"$simjecture_uv" sync --project "$simjecture_app" --python "$simjecture_python" --frozen --extra workspace --no-dev
if [[ -x "$simjecture_app/.venv/bin/python" ]]; then
  "$simjecture_app/.venv/bin/python" -c 'import importlib.metadata,sys; v=importlib.metadata.version("simjecture"); assert v == sys.argv[1], f"Source version {v} does not match installer {sys.argv[1]}"' "$SIMJECTURE_VERSION"
fi

echo '[4/4] Checking numerical execution setup…'
if ((simjecture_system)) && { ! command -v bwrap >/dev/null 2>&1 || ! command -v proot >/dev/null 2>&1; }; then
  if command -v apt-get >/dev/null 2>&1; then
    if [[ "$EUID" == 0 ]]; then
      apt-get update && apt-get install -y bubblewrap proot || echo 'Bubblewrap installation failed; check execution readiness in the GUI.' >&2
    elif command -v sudo >/dev/null 2>&1; then
      echo 'Your system may ask for a sudo password to install Bubblewrap.'
      sudo apt-get update && sudo apt-get install -y bubblewrap proot || echo 'Bubblewrap installation failed; check execution readiness in the GUI.' >&2
    else
      echo 'An administrator must install Bubblewrap for recorded experiments.' >&2
    fi
  else
    echo 'Install Bubblewrap with your Linux package manager for recorded experiments.' >&2
  fi
fi
if [[ -x "$simjecture_app/.venv/bin/python" ]]; then
  "$simjecture_app/.venv/bin/python" - <<'PY'
from conjecture_solver.execution import select_execution_backend
probe = select_execution_backend()
print('Numerical execution: ' + probe['backend'] if probe['available'] else 'GUI available; numerical execution needs attention: ' + probe['reason'])
if probe.get('warning'):
    print('WARNING: ' + probe['warning'])
if probe.get('fallback_unavailable'):
    print('Cooperative fallback unavailable: ' + probe['fallback_unavailable'])
    print('On namespace-restricted hosts, install/run under a dedicated non-root account with PRoot.')
PY
fi
# Activate only after the environment is installed successfully. Earlier versions and results remain.
printf '%s\n' "$SIMJECTURE_VERSION" > "$simjecture_install_dir/.current-version.new"
mv "$simjecture_install_dir/.current-version.new" "$simjecture_install_dir/.current-version"
cat > "$simjecture_install_dir/start-workspace" <<'START'
#!/usr/bin/env bash
set -euo pipefail
simjecture_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
simjecture_version="$(cat "$simjecture_root/.current-version")"
cd "$simjecture_root/app/$simjecture_version"
exec .venv/bin/simjecture web --runs-root "$simjecture_root/artifacts" "$@"
START
chmod +x "$simjecture_install_dir/start-workspace"
printf '\nInstalled Simjecture %s in: %s\nPermanent results: %s/artifacts/projects\n' "$SIMJECTURE_VERSION" "$simjecture_install_dir" "$simjecture_install_dir"
printf 'Restart later: %q --port %s\n' "$simjecture_install_dir/start-workspace" "$simjecture_port"
echo 'In the GUI, add your API endpoint/key or choose an already-installed CLI. No CLI agent is required.'
simjecture_web_args=()
if [[ -n "${SSH_CONNECTION:-}" ]]; then
  read -r _ _ simjecture_server simjecture_ssh_port <<< "$SSH_CONNECTION"
  simjecture_login="${SIMJECTURE_SSH_LOGIN:-$(id -un)}"
  simjecture_host="${SIMJECTURE_SSH_HOST:-$simjecture_server}"
  echo 'On your LOCAL computer, open another terminal and run:'
  printf '  ssh -o ExitOnForwardFailure=yes -p %q -N -L 8766:127.0.0.1:%s %q\n' "$simjecture_ssh_port" "$simjecture_port" "$simjecture_login@$simjecture_host"
  echo 'Then open http://localhost:8766. If SSH uses a public relay/NAT, substitute the same host and port you used to log in.'
  echo 'If local port 8766 is occupied, change only the first port in -L to another free port (for example 8876), then open http://localhost:8876.'
  simjecture_web_args+=(--no-open)
fi
if ((simjecture_start)); then
  printf 'Starting server at http://127.0.0.1:%s (localhost only). Keep this terminal open.\n' "$simjecture_port"
  rm -rf -- "$simjecture_scratch"
  trap - EXIT
  exec "$simjecture_install_dir/start-workspace" --port "$simjecture_port" "${simjecture_web_args[@]}"
fi
