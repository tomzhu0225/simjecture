"""Assemble self-contained Lean source for the bounded checker (no local imports)."""

from pathlib import Path

HERE = Path(__file__).resolve().parent


def assemble(destination: Path) -> None:
    imports, bodies = [], []
    for name in (
        "ShearEuler.lean",
        "Grid.lean",
        "Recovery.lean",
        "Optimality.lean",
        "Work.lean",
        "Certificate.lean",
        "Machines.lean",
    ):
        lines = (HERE / name).read_text().splitlines()
        for line in lines:
            if line.startswith("import ") and line not in imports:
                imports.append(line)
        bodies.append("\n".join(line for line in lines if not line.startswith("import ")))
    destination.write_text(("\n".join(imports) + "\n\n" + "\n\n".join(bodies)).rstrip() + "\n")


if __name__ == "__main__":
    import sys

    assemble(Path(sys.argv[1]))
