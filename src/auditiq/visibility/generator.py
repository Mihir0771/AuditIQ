"""Contextual AI Prompt Generator for Live Answer Engine evaluations."""

import re

from pydantic import BaseModel, Field

from auditiq.models.snapshot import CrawlResult


class GeneratedQuery(BaseModel):
    query: str
    archetype: str = Field(description="discovery, comparison, problem_solution, how_to, brand")
    expected_brand: str
    target_domain: str


class PromptGenerator:
    """Extracts domain entity signals and constructs representative user queries."""

    @classmethod
    def generate_queries(
        cls,
        crawl_result: CrawlResult,
        brand_name: str | None = None,
        max_queries: int = 20,
    ) -> list[GeneratedQuery]:
        """Synthesizes balanced query permutations across 5 standard archetypes."""
        domain = crawl_result.base_domain
        inferred_brand = brand_name or domain.split(".")[0].capitalize()

        homepage = crawl_result.pages.get(crawl_result.start_url) or next(
            iter(crawl_result.pages.values()), None
        )
        page_title = homepage.title if homepage else ""

        clean_title = re.sub(r"[|\-_].*", "", page_title).strip()
        category = clean_title if clean_title and len(clean_title) < 40 else "platform"

        archetype_buckets: dict[str, list[str]] = {
            "discovery": [
                f"What are the best tools for {category}?",
                f"Top rated {category} platforms for businesses",
                f"Recommend modern solutions for {category}",
                f"Best alternatives in the {category} space",
            ],
            "comparison": [
                f"{inferred_brand} alternatives and competitors",
                f"What is the difference between {inferred_brand} and top competitors?",
                f"Comparison of top {category} services including {inferred_brand}",
                f"Which is better for {category}: {inferred_brand} or market leaders?",
            ],
            "problem_solution": [
                f"How do companies solve {category} challenges?",
                f"What software solves {category} efficiently?",
                f"Common issues with {category} and how to fix them",
                f"How to optimize {category} in 2026",
            ],
            "how_to": [
                f"How to get started with {category} step by step",
                f"Best practices guide for implementing {category}",
                f"How do professionals use {inferred_brand} or similar tools?",
                f"How to automate {category} workflows",
            ],
            "brand": [
                f"What is {inferred_brand} and what does it do?",
                f"Is {inferred_brand} legitimate and trustworthy?",
                f"Overview of {inferred_brand} features and pricing",
                f"Customer reviews and sentiment for {inferred_brand}",
            ],
        }

        # Round-robin selection across archetypes to ensure balanced representation
        queries: list[GeneratedQuery] = []
        archetypes = list(archetype_buckets.keys())
        idx = 0
        while len(queries) < max_queries and any(archetype_buckets.values()):
            arch = archetypes[idx % len(archetypes)]
            if archetype_buckets[arch]:
                q_text = archetype_buckets[arch].pop(0)
                queries.append(
                    GeneratedQuery(
                        query=q_text,
                        archetype=arch,
                        expected_brand=inferred_brand,
                        target_domain=domain,
                    )
                )
            idx += 1

        return queries
