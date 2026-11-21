"""Multi-engine trial runner and empirical visibility aggregator."""

import asyncio
from collections import Counter

from pydantic import BaseModel, Field

from auditiq.visibility.engine import BaseAnswerEngine, EngineQueryResponse
from auditiq.visibility.generator import GeneratedQuery
from auditiq.visibility.providers.anthropic_engine import AnthropicEngine
from auditiq.visibility.providers.gemini_engine import GeminiEngine
from auditiq.visibility.providers.mock import MockAnswerEngine
from auditiq.visibility.providers.openai_engine import OpenAIEngine
from auditiq.visibility.providers.perplexity_engine import PerplexityEngine
from auditiq.visibility.stats import WilsonScoreInterval, compute_wilson_interval


class VisibilitySummary(BaseModel):
    brand_name: str
    target_domain: str
    active_engines: list[str] = Field(default_factory=list)
    total_evaluations: int = 0
    mention_rate: WilsonScoreInterval
    citation_rate: WilsonScoreInterval
    share_of_voice: float = 0.0
    top_cited_domains: list[tuple[str, int]] = Field(default_factory=list)
    average_latency_ms: float = 0.0
    responses: list[EngineQueryResponse] = Field(default_factory=list)


class VisibilityRunner:
    """Coordinates parallel query execution across configured answer engines."""

    def __init__(
        self,
        engines: list[BaseAnswerEngine] | None = None,
        use_mock_fallback: bool = False,
    ) -> None:
        if engines is not None:
            self.engines = engines
        else:
            candidates: list[BaseAnswerEngine] = [
                OpenAIEngine(),
                PerplexityEngine(),
                GeminiEngine(),
                AnthropicEngine(),
            ]
            active = [e for e in candidates if e.is_available()]
            if not active and use_mock_fallback:
                active = [MockAnswerEngine()]
            self.engines = active

    def has_available_engines(self) -> bool:
        return any(e.is_available() for e in self.engines)

    async def run(
        self,
        queries: list[GeneratedQuery],
        concurrency: int = 3,
    ) -> VisibilitySummary:
        if not self.engines or not queries:
            empty_interval = compute_wilson_interval(0, 0)
            target = queries[0].target_domain if queries else "unknown"
            brand = queries[0].expected_brand if queries else "unknown"
            return VisibilitySummary(
                brand_name=brand,
                target_domain=target,
                mention_rate=empty_interval,
                citation_rate=empty_interval,
            )

        target_domain = queries[0].target_domain
        brand_name = queries[0].expected_brand
        sem = asyncio.Semaphore(concurrency)

        async def _run_single(engine: BaseAnswerEngine, q: GeneratedQuery) -> EngineQueryResponse:
            async with sem:
                return await engine.query(
                    query_text=q.query,
                    brand_name=q.expected_brand,
                    target_domain=q.target_domain,
                    archetype=q.archetype,
                )

        tasks = []
        for engine in self.engines:
            for q in queries:
                tasks.append(_run_single(engine, q))

        results: list[EngineQueryResponse] = await asyncio.gather(*tasks)

        # Aggregate statistics
        total = len(results)
        mentions = sum(1 for r in results if r.brand_mentioned)
        citations = sum(1 for r in results if r.domain_cited)

        mention_interval = compute_wilson_interval(mentions, total)
        citation_interval = compute_wilson_interval(citations, total)

        # Count cited domains
        domain_counter: Counter[str] = Counter()
        latencies = []
        for r in results:
            latencies.append(r.latency_ms)
            for d in r.cited_domains:
                domain_counter[d] += 1

        top_domains = domain_counter.most_common(10)
        avg_lat = round(sum(latencies) / max(1, len(latencies)), 1)
        sov = round((mentions / max(1, total)) * 100, 1)

        return VisibilitySummary(
            brand_name=brand_name,
            target_domain=target_domain,
            active_engines=[e.name for e in self.engines],
            total_evaluations=total,
            mention_rate=mention_interval,
            citation_rate=citation_interval,
            share_of_voice=sov,
            top_cited_domains=top_domains,
            average_latency_ms=avg_lat,
            responses=results,
        )
