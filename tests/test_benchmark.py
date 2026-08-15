from __future__ import annotations

import pytest

from conjecture_solver.benchmarks.kinetic_sufficiency import (
    build_problem,
    run_kinetic_sufficiency_benchmark,
)
from conjecture_solver.models import PropositionClass


def test_planted_pair_has_equal_low_order_moments() -> None:
    result = run_kinetic_sufficiency_benchmark()

    assert result.moments_match
    assert result.maxwellian.moments.density == pytest.approx(1.0)
    assert result.two_stream.moments.density == pytest.approx(1.0)
    assert result.maxwellian.moments.mean_velocity == pytest.approx(0.0)
    assert result.two_stream.moments.mean_velocity == pytest.approx(0.0)
    assert result.maxwellian.moments.variance == pytest.approx(1.0)
    assert result.two_stream.moments.variance == pytest.approx(1.0)


def test_planted_pair_falsifies_predictive_sufficiency() -> None:
    result = run_kinetic_sufficiency_benchmark()

    assert result.hypothesis.proposition_class is PropositionClass.PREDICTIVE_SUFFICIENCY
    assert result.maxwellian.classification == "damped"
    assert result.two_stream.classification == "unstable"
    assert result.maxwellian.mode.growth_rate == pytest.approx(-0.1533594669, abs=1e-8)
    assert result.two_stream.mode.growth_rate == pytest.approx(0.1781158111, abs=1e-8)
    assert result.maxwellian.mode.dielectric_residual < 1e-8
    assert result.two_stream.mode.dielectric_residual < 1e-8
    assert result.witness.falsifies


def test_problem_is_preregistered_at_one_wavenumber() -> None:
    hypothesis, _ = build_problem()
    assert hypothesis.domain.fixed_parameters["wavenumber"] == 0.5
    with pytest.raises(ValueError, match="preregistered"):
        run_kinetic_sufficiency_benchmark(wavenumber=0.4)

