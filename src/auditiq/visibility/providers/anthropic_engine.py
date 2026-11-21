"""Anthropic Claude Live Answer Engine integration."""

import os
import re
import time

import httpx

from auditiq.visibility.engine import BaseAnswerEngine, EngineQueryResponse


class AnthropicEngine(BaseAnswerEngine):
    """Executes search queries against Anthropic Claude models."""

    def __init__(self, model: str = "claude-3-5-haiku-20241022") -> None:
        super().__init__(name="anthropic")
        self.model = model
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")

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
                error="ANTHROPIC_API_KEY is not configured.",
            )

        start_time = time.perf_counter()
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 400,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Answer this query objectively and concisely: {query_text}. "
                        "Mention relevant companies, software, or web tools."
                    ),
                }
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            content_blocks = data.get("content", [])
            raw_text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
            tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get(
                "output_tokens", 0
            )
            latency = round((time.perf_counter() - start_time) * 1000, 1)

            brand_pattern = re.compile(rf"\b{re.escape(brand_name)}\b", re.IGNORECASE)
            is_mentioned = bool(brand_pattern.search(raw_text))

            domain_pattern = re.compile(rf"\b{re.escape(target_domain)}\b", re.IGNORECASE)
            is_cited = bool(domain_pattern.search(raw_text))

            urls_found = re.findall(r"https?://[^\s)\]]+", raw_text)
            domains_found = list(
                {re.sub(r"^www\.", "", u.split("/")[2]) for u in urls_found if "/" in u}
            )

            return EngineQueryResponse(
                engine_name=self.name,
                query=query_text,
                archetype=archetype,
                raw_text=raw_text,
                cited_urls=urls_found,
                cited_domains=domains_found,
                brand_mentioned=is_mentioned,
                domain_cited=is_cited or target_domain in domains_found,
                mention_rank=1 if is_mentioned else None,
                sentiment="positive" if is_mentioned else "neutral",
                latency_ms=latency,
                tokens_used=tokens,
            )
        except Exception as e:
            return EngineQueryResponse(
                engine_name=self.name,
                query=query_text,
                archetype=archetype,
                raw_text="",
                error=f"Anthropic request failed: {e}",
            )
