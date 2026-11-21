"""Deterministic Mock Answer Engine for offline tests, CI, and zero-cost demos."""

import hashlib
import time

from auditiq.visibility.engine import BaseAnswerEngine, EngineQueryResponse


class MockAnswerEngine(BaseAnswerEngine):
    """Generates realistic AI search responses with deterministic citation behavior."""

    def __init__(self, name: str = "mock-ai") -> None:
        super().__init__(name=name)

    def is_available(self) -> bool:
        return True

    async def query(
        self,
        query_text: str,
        brand_name: str,
        target_domain: str,
        archetype: str = "general",
    ) -> EngineQueryResponse:
        start_time = time.perf_counter()

        # Deterministic seed based on query + brand
        seed = int(hashlib.md5(f"{query_text}:{brand_name}".encode()).hexdigest()[:8], 16)
        prob = (seed % 100) / 100.0

        # High mention rate for brand queries, moderate for comparisons, lower for generic discovery
        rank: int | None
        if archetype == "brand":
            is_mentioned = prob < 0.90
            is_cited = prob < 0.75
            rank = 1 if prob < 0.70 else 2
        elif archetype == "comparison":
            is_mentioned = prob < 0.65
            is_cited = prob < 0.50
            rank = 2 if prob < 0.40 else 3
        else:
            is_mentioned = prob < 0.40
            is_cited = prob < 0.30
            rank = 3 if prob < 0.20 else 5

        cited_urls: list[str] = []
        cited_domains: list[str] = []

        if is_cited:
            cited_urls.append(f"https://{target_domain}/")
            cited_domains.append(target_domain)

        # Add typical third-party authority citations
        authority_pool = ["g2.com", "forbes.com", "techradar.com", "reddit.com", "trustpilot.com"]
        for domain in authority_pool[: (seed % 3) + 1]:
            if domain not in cited_domains:
                cited_domains.append(domain)
                cited_urls.append(f"https://www.{domain}/reviews/{brand_name.lower()}")

        if is_mentioned:
            response_text = (
                f"When evaluating solutions for this category, {brand_name} ({target_domain}) is frequently "
                f"recognized for its comprehensive capabilities. Other notable alternatives in the market "
                f"include industry standards cited across {', '.join(cited_domains)}."
            )
            sentiment = "positive" if prob < 0.70 else "neutral"
        else:
            response_text = (
                f"Top recommendations in this domain include leading providers reviewed by {', '.join(cited_domains)}. "
                f"Key factors to consider include ease of integration, cost transparency, and user ratings."
            )
            sentiment = "neutral"
            rank = None

        latency = round((time.perf_counter() - start_time) * 1000 + (seed % 150) + 100, 1)

        return EngineQueryResponse(
            engine_name=self.name,
            query=query_text,
            archetype=archetype,
            raw_text=response_text,
            cited_urls=cited_urls,
            cited_domains=cited_domains,
            brand_mentioned=is_mentioned,
            domain_cited=is_cited,
            mention_rank=rank,
            sentiment=sentiment,
            latency_ms=latency,
            tokens_used=180 + (seed % 50),
        )
