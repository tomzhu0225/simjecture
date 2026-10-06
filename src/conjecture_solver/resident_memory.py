"""Linux resident-memory accounting for jobs with large GPU address reservations."""

from contextlib import suppress
from pathlib import Path


def process_tree_rss(pid):
    pending, seen, total = [pid], set(), 0
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        root = Path("/proc") / str(current)
        try:
            for line in (root / "status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    total += int(line.split()[1]) * 1024
                    break
            # A child may be forked by any thread, rather than the main thread.
            for task in (root / "task").iterdir():
                with suppress(FileNotFoundError, ProcessLookupError):
                    pending.extend(int(value) for value in (task / "children").read_text().split())
        except (FileNotFoundError, ProcessLookupError):
            pass  # Short-lived children can disappear between observations.
    return total
