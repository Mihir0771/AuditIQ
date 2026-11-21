"""Multi-engine trial runner and empirical visibility aggregator with exponential backoff."""

import asyncio
import logging
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

logger = logging.getLogger("auditiq.visibility.runner")


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
    """Coordinates parallel query execution across configured answer engines

    with retry and backoff protection against rate limits (HTTP 429) and network timeouts.
    """

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
                # Up to 3 attempts with exponential backoff on transient errors
                for attempt in range(3):
                    try:
                        return await engine.query(
                            query_text=q.query,
                            brand_name=q.expected_brand,
                            target_domain=q.target_domain,
                            archetype=q.archetype,
                        )
                    except Exception as e:
                        logger.warning(
                            "Visibility query to engine '%s' failed (attempt %d/3): %s",
                            engine.engine_name,
                            attempt + 1,
                            e,
                        )
                        if attempt < 2:
                            await asyncio.sleep(1.0 * (2**attempt))
                        else:
                            # Return safe fallback response so gather never fails
                            return EngineQueryResponse(
                                query=q.query,
                                engine_name=engine.engine_name,
                                raw_text=f"Error contacting {engine.engine_name}: {e}",
                                error=str(e),
                                brand_mentioned=False,
                                domain_cited=False,
                                latency_ms=0.0,
                            )
                return EngineQueryResponse(
                    query=q.query,
                    engine_name=engine.engine_name,
                    raw_text="Max retry attempts exceeded",
                    error="Max retry attempts exceeded",
                    brand_mentioned=False,
                    domain_cited=False,
                    latency_ms=0.0,
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
        all_cited: list[str] = []
        for r in results:
            all_cited.extend(r.cited_domains)

        top_domains = Counter(all_cited).most_common(10)

        # Competitive Share of Voice
        target_citations = sum(1 for r in results if r.domain_cited)
        competitor_citations = len(all_cited)
        total_market_citations = target_citations + competitor_citations
        sov = (
            round((target_citations / total_market_citations) * 100.0, 1)
            if total_market_citations > 0
            else 0.0
        )

        latencies = [r.latency_ms for r in results if r.latency_ms > 0]
        avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0.0

        return VisibilitySummary(
            brand_name=brand_name,
            target_domain=target_domain,
            active_engines=[e.engine_name for e in self.engines],
            total_evaluations=total,
            mention_rate=mention_interval,
            citation_rate=citation_interval,
            share_of_voice=sov,
            top_cited_domains=top_domains,
            average_latency_ms=avg_latency,
            responses=results,
        )
