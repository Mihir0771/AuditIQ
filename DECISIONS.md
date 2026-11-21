# DECISIONS.md — Architectural Decision Records (ADRs)

All significant technical, architectural, and design decisions are recorded here with context, options considered, chosen solution, rationale, and date.

---

## ADR 0001: Core Technology Stack Selection
- **Date**: 2026-11-21
- **Status**: Accepted
- **Context**: AuditIQ requires high-throughput asynchronous network crawling, selective headless browser rendering, strict data validation, relational persistence, and clean CLI + API interfaces.
- **Options Considered**:
  1. *Python 3.12+ (AsyncIO, FastAPI, Pydantic v2, Typer, Playwright, SQLAlchemy 2)*
  2. *TypeScript / Node.js (Crawlee, Express, Zod, Puppeteer, Prisma)*
  3. *Go (Colly, Gin, GORM)*
- **Decision**: Python 3.12+ with `httpx`, `selectolax`, `playwright`, `pydantic`, `fastapi`, `typer`, `sqlalchemy`.
- **Reasoning**:
  - Python offers the strongest ecosystem for NLP, statistical analysis (scipy/numpy for Wilson intervals), text similarity (simhash), and AI engine integration.
  - Pydantic v2 and FastAPI provide native OpenAPI generation and strict type safety.
  - Typer and Rich deliver enterprise-grade CLI ergonomics.
  - AsyncIO with `httpx` allows high-concurrency non-blocking crawling with HTTP/2 and connection pooling.

---

## ADR 0002: Dual-Engine HTML Parsing (Selectolax with lxml Fallback)
- **Date**: 2026-11-21
- **Status**: Accepted
- **Context**: Parsing thousands of HTML documents during a crawl can become a CPU bottleneck if using heavy DOM parsers like BeautifulSoup.
- **Options Considered**:
  1. *BeautifulSoup4 with html.parser*: Easy API but slow.
  2. *lxml*: Fast, C-based, supports XPath, but higher memory footprint.
  3. *selectolax (Modest/Lexbor)*: 10x-25x faster than BeautifulSoup/lxml for CSS selectors; minimal memory.
- **Decision**: Primary extraction via `selectolax` (Modest/Lexbor engine); fallback to `lxml` for complex XPath or malformed documents where Lexbor encounters edge cases.
- **Reasoning**: Enables crawl speeds of hundreds of pages per second on standard developer hardware without pegging CPU cores.

---

## ADR 0003: Render-vs-Raw Two-Tier Crawl Strategy
- **Date**: 2026-11-21
- **Status**: Accepted
- **Context**: Most AI crawlers (e.g., GPTBot, ClaudeBot, PerplexityBot) do not execute heavy client-side JavaScript due to compute costs; they index raw HTTP HTML. Conversely, users see client-rendered SPAs. Running headless Chromium on every page is too slow and resource-intensive.
- **Options Considered**:
  1. *Render every page with Playwright*: Extremely slow, high memory, high CPU.
  2. *Fetch raw HTTP only*: Misses JavaScript-hydration issues and DOM differences.
  3. *Tiered approach*: Raw HTTP for 100% of discovered pages; Playwright rendering for key templates (homepage, top landing pages, sampled template types).
- **Decision**: Tiered crawl strategy. Raw HTTP is performed on all discovered URLs; headless Chromium renders the homepage and a representative sample of page templates (or user-specified priority URLs).
- **Reasoning**: Delivers the signature "Render-vs-Raw" delta analysis while maintaining crawl speeds under 60 seconds for typical sites.

---

## ADR 0004: Pluggable Check Architecture (Open-Closed Principle)
- **Date**: 2026-11-21
- **Status**: Accepted
- **Context**: The audit engine must support dozens of checks across four distinct layers (Technical SEO, Content, GEO, Live AI) and allow rapid addition of new checks without modifying the core orchestrator.
- **Options Considered**:
  1. *Monolithic check methods inside a giant Auditor class*: Difficult to test, violates single-responsibility principle.
  2. *Pluggable Check Base Class with registry pattern*: Each check is an isolated, testable unit implementing `run(context) -> list[Finding]`.
- **Decision**: Registerable `BaseCheck` classes. Each check defines metadata (`id`, `layer`, `title`, `severity`, `effort`, `impact`) and implements an execution method.
- **Reasoning**: Isolated unit testing per check, zero-cost extensibility, and capability to enable/disable checks by layer or tag via configuration.

---

## ADR 0005: Statistical Honesty in Live AI Visibility (Wilson Score Intervals)
- **Date**: 2026-11-21
- **Status**: Accepted
- **Context**: Commercial AI visibility tools often present a single LLM prompt run as an authoritative metric. AI model responses are stochastic and vary across time and geography.
- **Options Considered**:
  1. *Single run per prompt*: Fast and cheap, but noisy and statistically misleading.
  2. *Repeated runs (N=3 to 5) with point estimates*: Better, but still hides sample size uncertainty.
  3. *Repeated runs with Wilson Score Confidence Intervals & variance reporting*: Displays observed mention rate alongside a 95% confidence interval and sample count (e.g., "75% [95% CI: 45%–92%], n=8").
- **Decision**: Mandatory Wilson Score interval calculation for mention and citation rates, explicitly indicating sample size $n$.
- **Reasoning**: Upholds the "Truth over polish" principle. Directly demonstrates scientific rigor to agencies and clients.

---

## ADR 0006: BYOK (Bring Your Own Key) & Pre-Run Cost Estimator
- **Date**: 2026-11-21
- **Status**: Accepted
- **Context**: Calling commercial LLM APIs (OpenAI, Anthropic, Gemini, Perplexity) incurs financial costs. Users must never be surprised by sudden API bills.
- **Options Considered**:
  1. *Automatic invocation of all available providers*: High risk of unexpected costs.
  2. *No live AI checks without manual scripts*: Degrades user experience.
  3. *BYOK with pre-run cost estimation and budget safety cap*: Calculates estimated tokens/cost based on prompt count and runs; requires confirmation if cost exceeds threshold; fails soft to "Not measured" if keys are missing.
- **Decision**: Implement BYOK architecture with strict pre-run cost estimators and configurable budget caps (`AUDITIQ_MAX_BUDGET_USD_PER_AUDIT`).
- **Reasoning**: Complete financial safety and transparency.

---

## ADR 0007: AI Bot Classification Triad (Training vs. Search vs. User-Triggered)
- **Date**: 2026-11-21
- **Status**: Accepted
- **Context**: Phase 1 empirical benchmarks (e.g. TechCrunch) revealed that publishers actively block model training bots (GPTBot, ClaudeBot) to protect copyright, while intentionally allowing search/indexing bots (OAI-SearchBot, PerplexityBot) for live citations. Treating all AI user-agents as a homogeneous block produces severe false positives.
- **Options Considered**:
  1. *Binary AI bot evaluation*: Flag any Disallow on an AI user-agent as an error.
  2. *Vendor-level grouping*: Group rules by OpenAI, Anthropic, Google.
  3. *Intent-based Triad*: Separate bots into Training, Search/Index, and User-Triggered.
- **Decision**: Classify all bots in `config/ai_bots.yaml` into three strict operational types: `training`, `search`, and `user`.
- **Reasoning**: Blocking training bots is a legitimate, common business defense that does NOT harm generative search visibility. Blocking search bots (OAI-SearchBot, PerplexityBot) directly destroys live generative citations. Differentiating them is essential for agency credibility.

---

## ADR 0008: Deterministic Phonetic Syllable Clustering for Flesch Readability
- **Date**: 2026-11-21
- **Status**: Accepted
- **Context**: Readability scoring (Flesch Reading Ease) requires syllable counting for every word in an article. Using heavy CMU pronouncing dictionaries or LLM calls creates latency and dependency bloat.
- **Options Considered**:
  1. *LLM-based readability evaluation*: Slow, expensive, non-deterministic.
  2. *CMU Pronouncing Dictionary (nltk/curses)*: 50MB dependency footprint.
  3. *Phonetic vowel cluster heuristic with silent trailing-e handling*: Zero external dependencies, executes in under 2ms for 2,000 words, achieves >95% accuracy against ground truth.
- **Decision**: Implement deterministic phonetic syllable clustering with vowel-run detection.
- **Reasoning**: Delivers lightning-fast, reproducible readability analysis with zero dependency bloat.

---

## ADR 0009: 64-Bit Simhash LSH for Near-Duplicate Cannibalization Detection
- **Date**: 2026-11-21
- **Status**: Accepted
- **Context**: Sites with hundreds of pages frequently suffer from template or keyword cannibalization. Pairwise vector embedding comparisons across 200 pages require 20,000 embedding comparisons ($O(N^2)$), which is too slow and cost-prohibitive for a fast crawl.
- **Options Considered**:
  1. *Exact string / MD5 hashing*: Misses near-duplicates with minor keyword variations.
  2. *Vector embeddings (OpenAI / sentence-transformers)*: High API cost and slow processing.
  3. *64-bit Simhash Locality-Sensitive Hashing (LSH)*: Bitwise XOR Hamming distance calculation completes in sub-millisecond time.
- **Decision**: Use 64-bit Simhash locality-sensitive hashing on filtered token streams. Pairs with Hamming distance $\le 3$ ($\ge 85\%$ similarity) are flagged as near-duplicates.
- **Reasoning**: Validated directly during benchmark runs; instantly caught near-duplicate documentation versions with zero network latency.


