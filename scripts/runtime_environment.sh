# Sourced by solver installers after argument validation.
# The application Python performs downloads; compiler/runtime packages remain local.
bootstrap_python="${SIMJECTURE_BOOTSTRAP_PYTHON:-python3}"
"$bootstrap_python" "$project_root/scripts/prepare_runtime.py" "$runtime_profile" "$prefix"
export CONDA_PREFIX="$prefix"
export PATH="$prefix/bin:$PATH"
# Conda compiler activation selects the matching sysroot and link libraries.
set +u
for activation in "$prefix"/etc/conda/activate.d/*.sh; do
    [[ ! -f "$activation" ]] || source "$activation"
done
set -u
python="$prefix/bin/python"
