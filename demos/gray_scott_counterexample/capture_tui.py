#!/usr/bin/env python3
"""Capture the current TUI projection of the immutable recorded run."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from conjecture_solver.tui.app import ConjectureSolverApp

DEMO_DIRECTORY = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--record",
        type=Path,
        default=DEMO_DIRECTORY / "record",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=150)
    parser.add_argument("--height", type=int, default=48)
    return parser.parse_args()


async def capture(args: argparse.Namespace) -> None:
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    app = ConjectureSolverApp(args.record.resolve())
    async with app.run_test(size=(args.width, args.height)) as pilot:
        await pilot.pause()
        app.save_screenshot(filename=output.name, path=str(output.parent))
    print(output)


def main() -> int:
    asyncio.run(capture(parse_args()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
