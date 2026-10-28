"""Frozen execution settings for prospective parked-workflow collection."""

from __future__ import annotations

import math

DEFAULTS = dict(
    worker_prompt="inherited",
    parent_turn_limit=4,
    maximum_parallel_workflows=2,
    minimum_gap_seconds=0.0,
)


def settings(value=None):
    result = DEFAULTS | (value or {})
    if set(result) != set(DEFAULTS):
        raise ValueError("Unknown workflow collection setting")
    if result["worker_prompt"] not in {"inherited", "task_protocol"}:
        raise ValueError("Unknown worker prompt control")
    limit = result["parent_turn_limit"]
    parallel = result["maximum_parallel_workflows"]
    gap = result["minimum_gap_seconds"]
    if type(limit) is not int or not 1 <= limit <= 12:
        raise ValueError("Parent-turn limit must be an integer from 1 to 12")
    if type(parallel) is not int or parallel not in {1, 2}:
        raise ValueError("Require one or two parallel workflows")
    if type(gap) not in {int, float} or not math.isfinite(gap) or not 0 <= gap <= 600:
        raise ValueError("Require a finite inter-workflow gap from 0 to 600 seconds")
    if gap and parallel != 1:
        raise ValueError("An inter-workflow gap requires serial collection")
    return result


def block_wall_seconds(count, configuration):
    """Conservative admission bound, including a gap before every serial trial."""
    config = settings(configuration)
    return (
        math.ceil(count / config["maximum_parallel_workflows"]) * 760
        + count * config["minimum_gap_seconds"]
        + 60
    )


def check_schedule(controllers, configuration):
    config = settings(configuration)
    events = []
    for row in controllers:
        start, end = row["started_at"], row["ended_at"]
        if not all(type(t) in {int, float} and math.isfinite(t) for t in [start, end]):
            raise ValueError("Invalid workflow execution interval")
        if start >= end:
            raise ValueError("Invalid workflow execution interval")
        events.extend([(start, 1), (end, -1)])
    active = 0
    for _, change in sorted(events):
        active += change
        if active > config["maximum_parallel_workflows"]:
            raise ValueError("Recorded workflows exceed the frozen concurrency limit")
    if config["maximum_parallel_workflows"] == 1:
        ordered = sorted(controllers, key=lambda r: r["started_at"])
        for previous, following in zip(ordered[:-1], ordered[1:], strict=True):
            if following["started_at"] - previous["ended_at"] < config["minimum_gap_seconds"]:
                raise ValueError("Recorded workflows violate the frozen inter-workflow gap")
