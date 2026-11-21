"""Directed internal link graph engine and orphan page detector."""

from collections import deque

from pydantic import BaseModel, ConfigDict, Field


class LinkGraph(BaseModel):
    """Represents the internal hyperlink structure of a crawled website."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    start_url: str
    inlinks: dict[str, set[str]] = Field(default_factory=dict)
    outlinks: dict[str, set[str]] = Field(default_factory=dict)
    anchor_texts: dict[str, dict[str, str]] = Field(default_factory=dict)
    depths: dict[str, int] = Field(default_factory=dict)

    def add_edge(self, source_url: str, target_url: str, anchor_text: str = "") -> None:
        """Adds a directed link from source_url to target_url."""
        if source_url == target_url:
            return  # Ignore self-links in topological calculations

        if source_url not in self.outlinks:
            self.outlinks[source_url] = set()
        self.outlinks[source_url].add(target_url)

        if target_url not in self.inlinks:
            self.inlinks[target_url] = set()
        self.inlinks[target_url].add(source_url)

        if anchor_text:
            if target_url not in self.anchor_texts:
                self.anchor_texts[target_url] = {}
            self.anchor_texts[target_url][source_url] = anchor_text.strip()

    def compute_depths(self) -> None:
        """Computes shortest crawl click depth from start_url using Breadth-First Search (BFS)."""
        self.depths.clear()
        if not self.start_url:
            return

        queue: deque[tuple[str, int]] = deque([(self.start_url, 0)])
        self.depths[self.start_url] = 0
        visited = {self.start_url}

        while queue:
            current_url, current_depth = queue.popleft()
            for neighbor in self.outlinks.get(current_url, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_depth = current_depth + 1
                    self.depths[neighbor] = new_depth
                    queue.append((neighbor, new_depth))

    def get_inlinks_count(self, url: str) -> int:
        """Returns the number of unique internal pages linking to this URL."""
        return len(self.inlinks.get(url, set()))

    def get_outlinks_count(self, url: str) -> int:
        """Returns the number of unique internal pages this URL links to."""
        return len(self.outlinks.get(url, set()))

    def find_orphan_pages(self, sitemap_urls: set[str], crawled_urls: set[str]) -> set[str]:
        """Identifies orphan pages: URLs in the sitemap or crawl list that receive 0 internal inlinks."""
        all_known = sitemap_urls.union(crawled_urls)
        orphans: set[str] = set()

        for url in all_known:
            if url == self.start_url:
                continue
            if len(self.inlinks.get(url, set())) == 0:
                orphans.add(url)

        return orphans
