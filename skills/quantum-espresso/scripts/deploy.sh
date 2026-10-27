#!/usr/bin/env bash
set -euo pipefail
project_root=""
runtime_base=""
uv="uv"
bubblewrap_dir=""
while (($#)); do
    case "$1" in
        --project-root|--runtime-base|--uv|--bubblewrap-dir)
            [[ $# -ge 2 && -n "$2" ]] || { echo "Missing value for $1" >&2; exit 2; }
            case "$1" in
                --project-root) project_root="$2" ;;
                --runtime-base) runtime_base="$2" ;;
                --uv) uv="$2" ;;
                --bubblewrap-dir) bubblewrap_dir="$2" ;;
            esac
            shift 2 ;;
        *) echo "Unsupported argument: $1" >&2; exit 2 ;;
    esac
done
[[ -n "$project_root" ]] || { echo "Supply --project-root with a Simjecture source checkout" >&2; exit 2; }
project_root="$(cd "$project_root" && pwd)"
source "$project_root/skills/quantum-espresso/scripts/prerequisites.sh"
qe_platform
if [[ "$uv" == */* && "$uv" != /* && ! -x "$uv" && -x "$project_root/$uv" ]]; then
    uv="$project_root/$uv"
fi
command -v "$uv" >/dev/null || qe_fail "Missing uv: $uv. Prepare uv/Python with the Simjecture base installer (docs/getting-started/installation.md), add uv to PATH or pass --uv /absolute/path/to/uv (PowerShell: -Uv), then retry."
uv="$(command -v "$uv")"
[[ "$uv" = /* ]] || uv="$PWD/$uv"
uv="$(cd "${uv%/*}" && pwd -P)/${uv##*/}"
"$uv" --version >/dev/null || qe_fail "uv cannot run. Repair uv or pass --uv /absolute/path/to/uv, then retry."
bootstrap_override="${SIMJECTURE_BOOTSTRAP_PYTHON:-}"
qe_python
if [[ -z "${UV_PROJECT_ENVIRONMENT:-}" ]]; then
    [[ -n "$bootstrap_override" || -x "$project_root/.venv/bin/python" ]] ||
        qe_fail "No existing application environment. Prepare it with uv sync --frozen or set UV_PROJECT_ENVIRONMENT to an existing environment, then retry."
    # Preserve a selected virtual environment, including its symlinked Python;
    # resolving the executable itself could incorrectly select the system prefix.
    selected_python="$(command -v "$bootstrap_python")"
    [[ "$selected_python" = /* ]] || selected_python="$PWD/$selected_python"
    selected_bin="$(cd "${selected_python%/*}" && pwd -P)"
    [[ "$selected_bin" = */bin && -x "$selected_bin/python" ]] ||
        qe_fail "Set UV_PROJECT_ENVIRONMENT to the existing application environment with bin/python, then retry."
    export UV_PROJECT_ENVIRONMENT="${selected_bin%/bin}"
fi
application_python="$UV_PROJECT_ENVIRONMENT/bin/python"
if [[ -n "$bubblewrap_dir" ]]; then
    if [[ "$bubblewrap_dir" != /* && ! -x "$bubblewrap_dir/bwrap" && -x "$project_root/$bubblewrap_dir/bwrap" ]]; then
        bubblewrap_dir="$project_root/$bubblewrap_dir"
    fi
    [[ -x "$bubblewrap_dir/bwrap" ]] || qe_fail "Configured Bubblewrap is not executable. Install the distribution bubblewrap package or correct --bubblewrap-dir, then retry."
    bubblewrap_dir="$(cd "$bubblewrap_dir" && pwd -P)"
    export PATH="$bubblewrap_dir:$PATH"
fi
command -v bwrap >/dev/null || qe_fail "Missing Bubblewrap. Install your distribution's bubblewrap package (Debian/Ubuntu: sudo apt install bubblewrap), or pass --bubblewrap-dir /existing/bin. Ask the administrator if installation is restricted; retry after setup."
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$project_root"
"$application_python" -c 'import conjecture_solver.cli' ||
    qe_fail "Application packages are unavailable. Run uv sync --frozen in this checkout (with UV_PROJECT_ENVIRONMENT set to your chosen environment), then retry."
# Reuse the application's package and namespace diagnostics; no solver or install.
SIMJECTURE_DEFAULT_EXECUTION_BACKEND=bubblewrap "$application_python" -m conjecture_solver doctor --profile core --project-root "$project_root" ||
    qe_fail "Core prerequisites failed; follow the doctor remedies above and retry. For namespace restrictions ask your administrator; this wrapper does not change host policy."
local_prefix="$project_root/.runtime/quantum-espresso-7.4"
if [[ -e "$local_prefix" || -L "$local_prefix" ]]; then
    if [[ -n "$runtime_base" && "$(readlink -m "$local_prefix")" != "$(readlink -m "$runtime_base/quantum-espresso-7.4")" ]]; then
        qe_fail "Existing QE runtime left unchanged; choose its current runtime base."
    fi
else
    runtime_base="${runtime_base:-$HOME/.local/share/simjecture/$(basename "$project_root")/runtime}"
    [[ "$runtime_base" = /* ]] || qe_fail "Runtime base must be an absolute Linux path."
fi
# Check the resolved target's native filesystem and reserve before creating links.
check_prefix="$local_prefix"
if [[ ! -e "$local_prefix" && ! -L "$local_prefix" ]]; then
    check_prefix="$runtime_base/quantum-espresso-7.4"
fi
"$bootstrap_python" "$project_root/skills/quantum-espresso/scripts/finalize_runtime.py" --check-disk "$check_prefix"
if [[ ! -e "$local_prefix" && ! -L "$local_prefix" ]]; then
    mkdir -p "$runtime_base" "$project_root/.runtime"
    ln -s "$runtime_base/quantum-espresso-7.4" "$local_prefix"
fi
"$uv" run --frozen simjecture install quantum-espresso --project-root "$project_root" --jobs 1
"$uv" run --frozen simjecture doctor --profile quantum-espresso --project-root "$project_root"
