"""Statistical confidence interval calculations for AI answer engine evaluations."""

import math

from pydantic import BaseModel, Field


class WilsonScoreInterval(BaseModel):
    """Wilson Score Confidence Interval for binomial proportion measurement."""

    point_estimate: float = Field(description="Empirical observed proportion (k / n)")
    lower_bound: float = Field(description="Lower bound of 95% confidence interval")
    upper_bound: float = Field(description="Upper bound of 95% confidence interval")
    sample_size: int = Field(description="Total trials (n)")
    successes: int = Field(description="Total successful occurrences (k)")
    confidence: float = 0.95

    @property
    def display(self) -> str:
        """Formatted human-readable string with sample size disclosure."""
        if self.sample_size == 0:
            return "0.0% (n=0)"
        pct = round(self.point_estimate * 100, 1)
        low = round(self.lower_bound * 100, 1)
        high = round(self.upper_bound * 100, 1)
        return f"{pct}% (95% CI: {low}% - {high}%, n={self.sample_size})"


def compute_wilson_interval(
    successes: int,
    total: int,
    confidence: float = 0.95,
) -> WilsonScoreInterval:
    """Computes Wilson Score Interval for binomial proportion with continuity correction.

    Standard z for 95% confidence is 1.959964.
    Formula: (p_hat + z^2/(2n) +- z * sqrt(p_hat*(1-p_hat)/n + z^2/(4n^2))) / (1 + z^2/n)
    """
    if total <= 0:
        return WilsonScoreInterval(
            point_estimate=0.0,
            lower_bound=0.0,
            upper_bound=0.0,
            sample_size=0,
            successes=0,
            confidence=confidence,
        )

    # Standard normal quantile
    # For 95% confidence, alpha = 0.05, z = 1.959964
    z = 1.959964 if math.isclose(confidence, 0.95, rel_tol=1e-2) else 1.96

    p_hat = successes / total
    z2 = z * z
    denom = 1.0 + z2 / total
    center = (p_hat + z2 / (2.0 * total)) / denom
    radicand = (p_hat * (1.0 - p_hat) / total) + (z2 / (4.0 * total * total))
    half_width = (z * math.sqrt(max(0.0, radicand))) / denom

    lower = max(0.0, center - half_width)
    upper = min(1.0, center + half_width)

    return WilsonScoreInterval(
        point_estimate=p_hat,
        lower_bound=lower,
        upper_bound=upper,
        sample_size=total,
        successes=successes,
        confidence=confidence,
    )
