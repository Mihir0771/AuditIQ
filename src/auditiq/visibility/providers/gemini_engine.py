"""Google Gemini Live Answer Engine integration with Google Search Grounding."""

import os
import re
import time

import httpx

from auditiq.visibility.engine import BaseAnswerEngine, EngineQueryResponse


class GeminiEngine(BaseAnswerEngine):
    """Executes search queries against Google Gemini with Google Search Grounding."""

    def __init__(self, model: str = "gemini-2.0-flash") -> None:
        super().__init__(name="gemini")
        self.model = model
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")

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
                error="GOOGLE_API_KEY / GEMINI_API_KEY is not configured.",
            )

        start_time = time.perf_counter()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                f"Answer concisely with up-to-date real-world facts: {query_text}. "
                                "Cite relevant tools, services, or websites."
                            )
                        }
                    ]
                }
            ],
            "tools": [{"googleSearch": {}}],  # Google Search grounding for live citations
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400},
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            candidates = data.get("candidates", [])
            raw_text = ""
            cited_urls: list[str] = []

            if candidates:
                cand = candidates[0]
                content = cand.get("content", {})
                parts = content.get("parts", [])
                raw_text = "".join(p.get("text", "") for p in parts)

                # Extract grounding metadata (search chunks)
                grounding = cand.get("groundingMetadata", {})
                chunks = grounding.get("groundingChunks", [])
                for chunk in chunks:
                    web = chunk.get("web", {})
                    uri = web.get("uri")
                    if uri:
                        cited_urls.append(uri)

            latency = round((time.perf_counter() - start_time) * 1000, 1)

            # Extract domains from cited URLs
            cited_domains = list(
                {re.sub(r"^www\.", "", u.split("/")[2]) for u in cited_urls if "/" in u}
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
                cited_urls=cited_urls,
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
                error=f"Gemini request failed: {e}",
            )
