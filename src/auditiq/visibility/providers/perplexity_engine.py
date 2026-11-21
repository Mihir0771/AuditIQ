"""Perplexity Live Answer Engine integration with Sonar web search."""

import os
import re
import time

import httpx

from auditiq.visibility.engine import BaseAnswerEngine, EngineQueryResponse


class PerplexityEngine(BaseAnswerEngine):
    """Executes live search queries against Perplexity Sonar."""

    def __init__(self, model: str = "sonar") -> None:
        super().__init__(name="perplexity")
        self.model = model
        self.api_key = os.getenv("PERPLEXITY_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def query(
        self,
        query_text: str,
        brand_name: str,
        target_domain: str,
        archetype: str = "general",
    ) -> EngineQueryResponse:
        if not self.is_available():
            return EngineQueryResponse(
                engine_name=self.name,
                query=query_text,
                archetype=archetype,
                raw_text="",
                error="PERPLEXITY_API_KEY is not configured.",
            )

        start_time = time.perf_counter()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Be precise, direct, and cite authoritative sources for your recommendations.",
                },
                {"role": "user", "content": query_text},
            ],
            "max_tokens": 400,
        }

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            raw_text = data["choices"][0]["message"]["content"]
            citations = data.get("citations", [])
            latency = round((time.perf_counter() - start_time) * 1000, 1)

            cited_domains = list(
                {re.sub(r"^www\.", "", u.split("/")[2]) for u in citations if "/" in u}
            )

            brand_pattern = re.compile(rf"\b{re.escape(brand_name)}\b", re.IGNORECASE)
            is_mentioned = bool(brand_pattern.search(raw_text))

            domain_pattern = re.compile(rf"\b{re.escape(target_domain)}\b", re.IGNORECASE)
            is_cited = bool(domain_pattern.search(raw_text)) or target_domain in cited_domains

            return EngineQueryResponse(
                engine_name=self.name,
                query=query_text,
                archetype=archetype,
                raw_text=raw_text,
                cited_urls=citations,
                cited_domains=cited_domains,
                brand_mentioned=is_mentioned,
                domain_cited=is_cited,
                mention_rank=1 if is_mentioned else None,
                sentiment="positive" if is_mentioned else "neutral",
                latency_ms=latency,
            )
        except Exception as e:
            return EngineQueryResponse(
                engine_name=self.name,
                query=query_text,
                archetype=archetype,
                raw_text="",
                error=f"Perplexity request failed: {e}",
            )
