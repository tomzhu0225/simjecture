#!/usr/bin/env bash
set -euo pipefail
prefix=""
project_root=""
while (($#)); do
  case "$1" in
    --prefix) prefix="$2"; shift 2 ;;
    --project-root) project_root="$2"; shift 2 ;;
    --jobs) shift 2 ;;
    --repair) shift ;;
    *) echo "Unsupported argument: $1" >&2; exit 2 ;;
  esac
done
[[ -n "$prefix" && -n "$project_root" ]] || exit 2
[[ "$(uname -s)-$(uname -m)" = Linux-x86_64 ]] || {
  echo 'This pinned binary recipe supports Linux x86_64.' >&2; exit 2;
}
mkdir -p "$prefix"
prefix="$(cd "$prefix" && pwd)"
project_root="$(cd "$project_root" && pwd)"
# Isolated decompressor: no system package or default Lean toolchain changes.
python3 -m venv "$prefix/bootstrap"
"$prefix/bootstrap/bin/python" -m pip install --disable-pip-version-check zstandard==0.25.0
archive="$prefix/bootstrap/lean-4.24.0-linux.tar.zst"
if [[ ! -f "$archive" ]]; then
  curl -fL --retry 3 -o "$archive.part" https://github.com/leanprover/lean4/releases/download/v4.24.0/lean-4.24.0-linux.tar.zst
  mv "$archive.part" "$archive"
fi
printf '%s  %s\n' b14f5e5159219dd1a1956c3b806813319f5e94ccd5bdfd56f54520609a5bb5ec "$archive" | sha256sum -c -
mkdir -p "$prefix/toolchain" "$prefix/share" "$prefix/bin"
"$prefix/bootstrap/bin/python" - "$archive" "$prefix/toolchain" <<'PY'
import sys, tarfile
from pathlib import Path
import zstandard
with open(sys.argv[1], 'rb') as source:
    with zstandard.ZstdDecompressor().stream_reader(source) as stream:
        with tarfile.open(fileobj=stream, mode='r|') as archive:
            for member in archive:
                parts = Path(member.name).parts[1:]
                if not parts:
                    continue
                member.name = str(Path(*parts))
                archive.extract(member, sys.argv[2], filter='data')
PY
if [[ ! -d "$prefix/mathlib/.git" ]]; then
  git clone --depth 1 --branch v4.24.0 https://github.com/leanprover-community/mathlib4.git "$prefix/mathlib"
fi
[[ "$(git -C "$prefix/mathlib" rev-parse HEAD)" = f897ebcf72cd16f89ab4577d0c826cd14afaafc7 ]] || {
  echo 'Unexpected Mathlib revision; inspect the runtime before retrying.' >&2; exit 2;
}
export PATH="$prefix/toolchain/bin:$PATH"
cache_targets=(
  Mathlib/Algebra/BigOperators/Group/Finset/Basic.lean
  Mathlib/Data/Real/Basic.lean
  Mathlib/Tactic/Ring.lean
  Mathlib/Tactic/NormNum.lean
  Mathlib/Tactic/FieldSimp.lean
  Mathlib/Data/Rat/Cast/Order.lean
  Mathlib/Data/Real/Sqrt.lean
  Mathlib/Algebra/BigOperators/Fin.lean
  Mathlib/Data/Finset/Card.lean
  Mathlib/Data/Fintype/Card.lean
  Mathlib/Algebra/Order/BigOperators/Group/Finset.lean
  Mathlib/Algebra/BigOperators/Ring/Finset.lean
  Mathlib/Analysis/SpecialFunctions/Trigonometric/Deriv.lean
  Mathlib/Tactic/Linarith.lean
  Mathlib/Analysis/Calculus/BumpFunction/InnerProduct.lean
  Mathlib/Analysis/Calculus/ContDiff/RCLike.lean
  Mathlib/Analysis/Calculus/Deriv/Prod.lean
  Mathlib/Analysis/Calculus/Deriv/Pow.lean
  Mathlib/Analysis/Calculus/FDeriv/Prod.lean
  Mathlib/Data/Fin/VecNotation.lean
  Mathlib/Data/Fintype/Pi.lean
  Mathlib/Data/Real/Archimedean.lean
  Mathlib/Tactic/FinCases.lean
  Mathlib/Tactic/FunProp.lean
  Mathlib/Tactic/LinearCombination.lean
  Mathlib/Analysis/Calculus/ContDiff/Operations.lean
  Mathlib/Analysis/Calculus/Deriv/Add.lean
  Mathlib/Analysis/Calculus/Deriv/Mul.lean
  Mathlib/Analysis/Calculus/Deriv/Comp.lean
  Mathlib/Analysis/Normed/Group/Constructions.lean
  Mathlib/Analysis/Normed/Field/Basic.lean
  Mathlib/Tactic/Positivity.lean
  Mathlib/Data/Finset/Lattice/Fold.lean
  Mathlib/Analysis/Calculus/Deriv/Inv.lean
  Mathlib/Algebra/BigOperators/Intervals.lean
  Mathlib/Algebra/Order/BigOperators/Ring/Finset.lean
  Mathlib/Analysis/SpecialFunctions/Log/Deriv.lean
  Mathlib/Analysis/Convex/Deriv.lean
  Mathlib/Analysis/Convex/Jensen.lean
)
(cd "$prefix/mathlib" && lake exe cache get "${cache_targets[@]}")
cp "$project_root/src/conjecture_solver/lean_check.py" "$prefix/share/lean_check.py"
cp --remove-destination "$(readlink -f "$(command -v python3)")" "$prefix/bin/python"
chmod +x "$prefix/bin/python"
python3 - "$prefix" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path
p = Path(sys.argv[1])
record = {
  'lean_version': subprocess.check_output([str(p/'toolchain/bin/lean'), '--version'], text=True).strip(),
  'lean_archive_sha256': 'b14f5e5159219dd1a1956c3b806813319f5e94ccd5bdfd56f54520609a5bb5ec',
  'mathlib_revision': 'f897ebcf72cd16f89ab4577d0c826cd14afaafc7',
  'mathlib_manifest_sha256': hashlib.sha256((p/'mathlib/lake-manifest.json').read_bytes()).hexdigest(),
  'scope': 'Lean/Mathlib theorem checking; no solver qualification',
}
(p/'share/build-record.json').write_text(json.dumps(record, indent=2)+'\n')
PY
