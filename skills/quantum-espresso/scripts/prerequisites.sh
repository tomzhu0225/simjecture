# Shared, read-only prerequisites for the QE deployment entry points.
qe_fail() { echo "QE setup blocked: $*" >&2; exit 2; }
qe_platform() {
    command -v uname >/dev/null || qe_fail "Missing uname. Install your Linux coreutils package and retry."
    [[ "$(uname -s)" = Linux && "$(uname -m)" = x86_64 ]] ||
        qe_fail "Supported platform: Linux x86_64, including configured WSL2. Use that environment and retry; Windows/macOS/ARM are not supported by this lock."
    for tool in findmnt readlink mkdir ln basename; do
        command -v "$tool" >/dev/null || qe_fail "Missing $tool. Install Linux coreutils and util-linux using your distribution package manager, then retry."
    done
}
qe_python() {
    # The operator passes the interpreter already running Simjecture. Explicit
    # overrides remain authoritative; never silently fall back from a bad one.
    local app_environment="${UV_PROJECT_ENVIRONMENT:-}"
    if [[ -n "$app_environment" ]]; then
        [[ "$app_environment" = /* ]] || app_environment="$project_root/$app_environment"
        [[ -x "$app_environment/bin/python" ]] ||
            qe_fail "Invalid UV_PROJECT_ENVIRONMENT: $app_environment has no executable bin/python. Correct the environment path or prepare that target with UV_PROJECT_ENVIRONMENT set and uv sync --frozen, then retry."
        app_environment="$(cd "$app_environment" && pwd -P)"
        export UV_PROJECT_ENVIRONMENT="$app_environment"
    fi
    bootstrap_python="${SIMJECTURE_BOOTSTRAP_PYTHON:-}"
    if [[ -z "$bootstrap_python" ]]; then
        app_environment="${UV_PROJECT_ENVIRONMENT:-$project_root/.venv}"
        [[ "$app_environment" = /* ]] || app_environment="$project_root/$app_environment"
        if [[ -x "$app_environment/bin/python" ]]; then
            bootstrap_python="$app_environment/bin/python"
        else
            bootstrap_python=python3
        fi
    fi
    if [[ "$bootstrap_python" == */* && "$bootstrap_python" != /* && ! -x "$bootstrap_python" && -x "$project_root/$bootstrap_python" ]]; then
        bootstrap_python="$project_root/$bootstrap_python"
    fi
    command -v "$bootstrap_python" >/dev/null ||
        qe_fail "Missing application Python: $bootstrap_python. Prepare Python >=3.11 with the Simjecture base installer, or set SIMJECTURE_BOOTSTRAP_PYTHON to an existing application Python executable; retry after setup. See docs/getting-started/installation.md."
    bootstrap_python="$(command -v "$bootstrap_python")"
    [[ "$bootstrap_python" = /* ]] || bootstrap_python="$PWD/$bootstrap_python"
    bootstrap_python="$(cd "${bootstrap_python%/*}" && pwd -P)/${bootstrap_python##*/}"
    "$bootstrap_python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' ||
        qe_fail "Application Python must run and be >=3.11. Repair the application environment with uv sync --frozen, or configure SIMJECTURE_BOOTSTRAP_PYTHON, then retry."
    export SIMJECTURE_BOOTSTRAP_PYTHON="$bootstrap_python"
}
