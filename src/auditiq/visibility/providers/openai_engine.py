"""OpenAI Live Answer Engine integration."""

import os
import re
import time

import httpx

from auditiq.visibility.engine import BaseAnswerEngine, EngineQueryResponse


class OpenAIEngine(BaseAnswerEngine):
    """Executes search queries against OpenAI models."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        super().__init__(name="openai")
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY", "")

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
                error="OPENAI_API_KEY is not configured.",
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
                    "content": (
                        "You are a helpful search assistant. Answer the user's question directly with concise, "
                        "objective facts and cite relevant product names, companies, and source domains where appropriate."
                    ),
                },
                {"role": "user", "content": query_text},
            ],
            "temperature": 0.2,
            "max_tokens": 400,
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            raw_text = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            latency = round((time.perf_counter() - start_time) * 1000, 1)

            # Analyze text for brand mention
            brand_pattern = re.compile(rf"\b{re.escape(brand_name)}\b", re.IGNORECASE)
            is_mentioned = bool(brand_pattern.search(raw_text))

            # Analyze text for domain citation
            domain_pattern = re.compile(rf"\b{re.escape(target_domain)}\b", re.IGNORECASE)
            is_cited = bool(domain_pattern.search(raw_text))

            # Extract any URLs mentioned
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
                error=f"OpenAI request failed: {e}",
            )
