"""Check explicit conjunctive numerical bounds before an expensive repair test."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AcceptanceBound(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    metric: str = Field(min_length=1, description="Case-qualified observable, e.g. S2000.rate")
    lower: float | None = None
    upper: float | None = None

    @model_validator(mode="after")
    def bounded(self):
        if not self.metric.strip() or (self.lower is None and self.upper is None):
            raise ValueError("Supply a metric and at least one inclusive bound")
        return self


def acceptance_bounds(values):
    """Bounds for the same metric are ANDed; distinct cases must use distinct names.

    This checks feasibility only, not the physical meaning or observed satisfaction.
    Natural-language acceptance rules remain the independent reviewer's responsibility.
    """
    bounds = [AcceptanceBound.model_validate(value).model_dump() for value in values]
    intersections = {}
    for bound in bounds:
        low, high = intersections.get(bound["metric"], (float("-inf"), float("inf")))
        if bound["lower"] is not None:
            low = max(low, bound["lower"])
        if bound["upper"] is not None:
            high = min(high, bound["upper"])
        if low > high:
            raise ValueError(f"Empty acceptance intersection for {bound['metric']}: {low} > {high}")
        intersections[bound["metric"]] = low, high
    return bounds
