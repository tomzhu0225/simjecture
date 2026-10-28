"""Compatibility entry point; prefer python -m simjecture_monitor.training."""

from simjecture_monitor.training import (
    episode_normalization,
    main,
    measured_advantages,
    read_data,
    require_behavior_weights,
)

__all__ = [
    "episode_normalization",
    "main",
    "measured_advantages",
    "read_data",
    "require_behavior_weights",
]

if __name__ == "__main__":
    main()
