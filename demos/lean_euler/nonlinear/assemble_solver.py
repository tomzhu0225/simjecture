"""Assemble the nonlinear solver proof components for the bounded checker."""

from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENTS = [
    "Admissible.lean",
    "PrimitiveEnergy.lean",
    "ConservativePrimitive.lean",
    "DiscreteEnergy.lean",
    "EnergyBounds.lean",
    "VariableEnergy.lean",
    "GridSobolev.lean",
    "CoefficientBounds.lean",
    "VariableStability.lean",
    "Entropy.lean",
    "EntropyConvexity.lean",
    "EntropyDynamics.lean",
]


def assemble(destination):
    imports, bodies = [], []
    for name in COMPONENTS:
        lines = (HERE / "formal" / name).read_text().splitlines()
        for line in lines:
            if line.startswith("import ") and line not in imports:
                imports.append(line)
        bodies.append("\n".join(line for line in lines if not line.startswith("import ")))
    Path(destination).write_text(
        ("\n".join(imports) + "\n\n" + "\n\n".join(bodies)).rstrip() + "\n"
    )


if __name__ == "__main__":
    import sys

    assemble(sys.argv[1])
