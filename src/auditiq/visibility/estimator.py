"""Pre-run token and USD cost estimation for Live AI Visibility testing."""

import os

from pydantic import BaseModel, Field


class CostEstimate(BaseModel):
    total_queries: int
    engines_count: int
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    max_budget_usd: float = Field(default=2.00)
    is_within_budget: bool = True
    details_per_engine: dict[str, float] = Field(default_factory=dict)


class BudgetEstimator:
    """Calculates expected API spend and enforces user budget ceilings."""

    DEFAULT_MAX_BUDGET = float(os.getenv("AUDITIQ_MAX_BUDGET_USD_PER_AUDIT", "2.00"))

    # Approximate cost per query (input + output + web search grounding)
    ENGINE_QUERY_COST = {
        "mock": 0.0,
        "openai": 0.004,  # GPT-4o-mini with search grounding
        "perplexity": 0.005,  # Sonar online search query
        "gemini": 0.002,  # Gemini 2.0 Flash with Google Search grounding
        "anthropic": 0.003,  # Claude 3.5 Haiku
    }

    @classmethod
    def estimate(
        cls,
        num_queries: int,
        engines: list[str],
        max_budget_usd: float | None = None,
    ) -> CostEstimate:
        budget = max_budget_usd if max_budget_usd is not None else cls.DEFAULT_MAX_BUDGET
        per_engine: dict[str, float] = {}
        total_cost = 0.0

        for eng in engines:
            unit_cost = cls.ENGINE_QUERY_COST.get(eng.lower(), 0.005)
            engine_cost = unit_cost * num_queries
            per_engine[eng] = round(engine_cost, 4)
            total_cost += engine_cost

        # Approximate tokens (average 50 input tokens per query, 350 output tokens per answer)
        input_tokens = num_queries * len(engines) * 50
        output_tokens = num_queries * len(engines) * 350

        return CostEstimate(
            total_queries=num_queries,
            engines_count=len(engines),
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            estimated_cost_usd=round(total_cost, 4),
            max_budget_usd=budget,
            is_within_budget=total_cost <= budget,
            details_per_engine=per_engine,
        )
