"""Data models representing crawled pages, link graphs, and snapshots."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class IndexabilityStatus(StrEnum):
    INDEXABLE = "indexable"
    NOINDEX = "noindex"
    CANONICALISED = "canonicalised"
    REDIRECTED = "redirected"
    CLIENT_ERROR = "client_error"
    SERVER_ERROR = "server_error"
    BLOCKED_ROBOTS = "blocked_robots"


class RedirectHop(BaseModel):
    url: str
    status_code: int


class LinkEdge(BaseModel):
    source_url: str
    target_url: str
    anchor_text: str = ""
    is_internal: bool = True
    is_nofollow: bool = False


class PageSnapshot(BaseModel):
    url: str
    status_code: int
    headers: dict[str, str] = Field(default_factory=dict)
    raw_html: str = ""
    rendered_html: str | None = None
    ttfb_ms: float = 0.0
    elapsed_ms: float = 0.0
    content_type: str = ""
    depth: int = 0
    redirect_chain: list[RedirectHop] = Field(default_factory=list)
    is_rendered: bool = False
    inlinks_count: int = 0
    outlinks: list[str] = Field(default_factory=list)
    title: str = ""
    meta_description: str = ""
    canonical_url: str = ""
    h1s: list[str] = Field(default_factory=list)
    headings_hierarchy: list[dict[str, Any]] = Field(default_factory=list)
    word_count: int = 0
    is_sitemap_discovered: bool = False
    error: str | None = None


class CrawlResult(BaseModel):
    start_url: str
    base_domain: str
    pages: dict[str, PageSnapshot] = Field(default_factory=dict)
    sitemap_urls: set[str] = Field(default_factory=set)
    robots_txt_content: str | None = None
    robots_txt_status: int | None = None
    crawl_duration_sec: float = 0.0
    total_urls_discovered: int = 0
    total_pages_crawled: int = 0
