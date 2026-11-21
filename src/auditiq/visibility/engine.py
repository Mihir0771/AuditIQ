"""Base interface and data models for AI Answer Engine query runners."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class EngineQueryResponse(BaseModel):
    """Normalized response from an individual AI engine query."""

    engine_name: str
    query: str
    archetype: str = "general"
    raw_text: str
    cited_urls: list[str] = Field(default_factory=list)
    cited_domains: list[str] = Field(default_factory=list)
    brand_mentioned: bool = False
    domain_cited: bool = False
    mention_rank: int | None = None
    sentiment: str = "neutral"  # positive, neutral, negative
    latency_ms: float = 0.0
    tokens_used: int = 0
    error: str | None = None


class BaseAnswerEngine(ABC):
    """Abstract base class for generative AI answer engine integrations."""

    def __init__(self, name: str) -> None:
        self.name = name

    @property
    def engine_name(self) -> str:
        """Alias for name for backward compatibility."""
        return self.name

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the engine's credentials or mock environment are active."""
        pass

    @abstractmethod
    async def query(
        self,
        query_text: str,
        brand_name: str,
        target_domain: str,
        archetype: str = "general",
    ) -> EngineQueryResponse:
        """Executes a single search/generation query and extracts visibility signals."""
        pass
