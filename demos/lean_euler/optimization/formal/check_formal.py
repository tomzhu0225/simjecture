"""Check the exact 3D cache model and the restricted scheduling cost model."""

import json
from pathlib import Path

from lean_check import check

THEOREMS = {
    "EulerCache.lean": [
        "EulerCache.face_consistency",
        "EulerCache.step_equivalence",
        "EulerCache.admissible_step_equivalence",
        "EulerCache.trajectory_equivalence",
        "EulerCache.cached_conservation",
    ],
    "CacheSchedule.lean": [
        "CacheSchedule.reference_legal",
        "CacheSchedule.cold_use_rejected",
        "CacheSchedule.evicted_use_rejected",
        "CacheSchedule.cache_optimal",
        "CacheSchedule.saves_two_evaluations_per_cell",
        "CacheSchedule.cached_library_cost",
        "CacheSchedule.reference_library_cost",
        "CacheSchedule.weighted_cache_optimal",
        "CacheSchedule.weighted_saving",
        "CacheSchedule.weighted_strict_improvement",
    ],
}
results = {
    name: check(name, names, output=Path(name).stem, timeout=90) for name, names in THEOREMS.items()
}
Path("formal-results.json").write_text(json.dumps(results, indent=2) + "\n")
assert all(result["checked"] for result in results.values()), results
