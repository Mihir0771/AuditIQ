# AuditIQ Architecture & System Design Specification

This document provides a complete technical walkthrough of the **AuditIQ** architecture, data flow, component interactions, and execution guarantees.

---

## 1. System Overview & Component Graph

AuditIQ is engineered as a decoupled, multi-tier intelligence pipeline capable of executing deterministic web crawling, selective headless Chromium rendering, multi-engine AI visibility trials, and responsive report generation.

```mermaid
flowchart TD
    UserCLI["CLI (Typer & Rich)"] --> AppRouter
    WebUI["Interactive Web Dashboard"] --> AppRouter
    ClientAPI["External REST Clients"] --> AppRouter

    subgraph ServerLayer ["Server & API Tier"]
        AppRouter["FastAPI Application (src/auditiq/server/app.py)"]
        JobManager["JobManager & SSE Broadcaster (src/auditiq/server/jobs.py)"]
        AppRouter --> JobManager
    end

    subgraph CrawlerTier ["Polite Crawler Engine (src/auditiq/crawler/)"]
        JobManager --> Engine["HttpCrawler (asyncio BFS Loop)"]
        Engine --> SSRF["SSRF Protection Filter"]
        Engine --> Robots["RFC 9309 RobotsTxtParser"]
        Engine --> Sitemap["XML Sitemap Recursive Parser"]
        Engine --> SelectiveRenderer["Headless Chromium Renderer (Playwright)"]
        Engine --> LinkGraph["Directed Link Graph (Depth & Orphans)"]
    end

    subgraph CheckTier ["Audit Check Registry (src/auditiq/checks/)"]
        CheckRegistry["CheckRegistry (Pluggable BaseCheck)"]
        TechSuite["Layer 1: Technical SEO (27 checks)"]
        ContentSuite["Layer 2: Content & Entity (13 checks)"]
        GeoSuite["Layer 3: GEO Readiness (11 checks)"]
        LiveSuite["Layer 4: Live AI Visibility (4 checks)"]

        CheckRegistry --> TechSuite
        CheckRegistry --> ContentSuite
        CheckRegistry --> GeoSuite
        CheckRegistry --> LiveSuite
    end

    subgraph VisibilityTier ["Live AI Visibility Engine (src/auditiq/visibility/)"]
        PromptGen["PromptGenerator (5 Archetypes)"]
        BudgetEst["BudgetEstimator (USD & Tokens)"]
        Runner["VisibilityRunner (Trial Concurrency)"]
        StatsEngine["Wilson Score Confidence Intervals (z=1.96)"]
        
        LiveSuite --> Runner
        Runner --> PromptGen
        Runner --> BudgetEst
        Runner --> StatsEngine
        
        Runner --> OpenAI["OpenAI (GPT-4o-mini)"]
        Runner --> Perplexity["Perplexity (Sonar)"]
        Runner --> Gemini["Google Gemini (Search Grounding)"]
        Runner --> Claude["Anthropic (Claude 3.5 Haiku)"]
        Runner --> MockAI["Deterministic Mock Engine"]
    end

    subgraph ScoringTier ["Scoring & Remediation Engine (src/auditiq/scoring/)"]
        ScoringEngine["Composite Scoring (v2026.1)"]
        WeightDist["Proportional Weight Redistribution"]
        Eisenhower["Eisenhower 4-Quadrant Prioritization"]
        Regression["Regression & History Comparison Engine"]

        ScoringEngine --> WeightDist
        ScoringEngine --> Eisenhower
        ScoringEngine --> Regression
    end

    subgraph DeliveryTier ["Reporting & Export Delivery (src/auditiq/reports/)"]
        HTMLGen["Jinja2 HTML Generator (White-Label)"]
        PDFGen["Playwright Headless Chromium PDF Generator"]
        Exporters["JSON & CSV Structured Exporters"]
    end

    Engine --> CheckRegistry
    CheckRegistry --> ScoringEngine
    ScoringEngine --> DeliveryTier
```

---

## 2. Asynchronous Crawl & Render Pipeline

### The Two-Tier Strategy (ADR 0003)
Most traditional search engines evaluate JavaScript with massive compute clusters. However, AI crawlers (like `GPTBot`, `ClaudeBot`, and `PerplexityBot`) almost exclusively fetch raw HTML payloads to minimize token latency and compute costs.

AuditIQ mirrors this asymmetry through a **two-tier crawl**:
1. **Tier 1 (Raw HTTP, 100% of discovered pages)**: High-speed async `httpx` stream with gzip/brotli compression, HTTP/2 multiplexing, and RFC 9309 robots compliance.
2. **Tier 2 (Headless DOM, sampled templates)**: Renders a sample of distinct page templates (`--render-sample`, default 5) using headless Chromium to compute the exact **Render-vs-Raw differential** (detecting CSR text loss and dynamic JavaScript-hydrated links).

### Crawl Execution Sequence

```mermaid
sequenceDiagram
    participant JM as JobManager / CLI
    participant Crawler as HttpCrawler
    participant SSRF as SSRF Validator
    participant Robots as RobotsTxtParser
    participant Sitemap as SitemapParser
    participant Web as Target Web Server
    participant Playwright as Headless Chromium

    JM->>Crawler: crawl(start_url, max_pages=30, depth=3)
    Crawler->>SSRF: validate_url_safety(start_url)
    SSRF-->>Crawler: Safe (Public IP)
    Crawler->>Web: GET /robots.txt
    Web-->>Crawler: 200 OK (Robots rules)
    Crawler->>Robots: parse(rules, ai_bot_matrix)
    Crawler->>Web: GET /sitemap.xml
    Web-->>Crawler: 200 OK (Sitemap index)
    Crawler->>Sitemap: parse_recursive()
    Crawler->>Crawler: Seed BFS queue (start_url + sitemap URLs)
    
    loop BFS Crawl Loop
        Crawler->>Robots: is_allowed(url)
        alt Allowed
            Crawler->>Web: GET page (httpx)
            Web-->>Crawler: 200 OK (Raw HTML)
            alt Template Sampled for Rendering
                Crawler->>Playwright: render_page(url)
                Playwright-->>Crawler: Rendered DOM + Screenshot
            end
            Crawler->>Crawler: Extract internal outlinks & update LinkGraph
        else Disallowed
            Crawler->>Crawler: Record 403 Robots Block
        end
    end
    
    Crawler->>Crawler: Compute LinkGraph depths & orphan nodes
    Crawler-->>JM: CrawlResult Snapshot
```

---

## 3. Pluggable Check Framework

All checks inherit from the abstract base class `BaseCheck` (`src/auditiq/checks/base.py`):

```python
class BaseCheck(ABC):
  id: str  # Immutable code, e.g. "GEO-BOT-ACCESS"
  layer: AuditLayer  # TECHNICAL, CONTENT, GEO_READINESS, LIVE_VISIBILITY
  title: str
  severity: Severity  # CRITICAL, HIGH, MEDIUM, LOW, INFO
  effort: Effort  # S, M, L
  impact: int  # 1 to 5 scale
  why_it_matters: str
  fix_guidance: str
  references: list[str]

  async def run_site(self, context: SiteContext) -> list[Finding]:
    ...

  async def run_page(self, context: PageContext) -> list[Finding]:
    ...
```

### Execution Flow:
1. `CheckRegistry.run_checks()` registers all checks across selected layers.
2. `run_site` executes concurrently across the entire `CrawlResult` (evaluating sitemaps, robots.txt, `/llms.txt`, and site-wide duplicate cannibalization).
3. `run_page` executes concurrently across every individual `PageSnapshot` (evaluating metadata, heading hierarchy, content readability, schema syntax, and render differentials).
4. Results are normalized into immutable `Finding` objects with structured evidence dictionaries.

---

## 4. Live AI Visibility Engine Architecture

The Live Visibility layer simulates real-world user intent queries against generative answer engines to calculate empirical visibility.

### 5-Archetype Intent Generation
Rather than guessing random keywords, `PromptGenerator` extracts brand name, primary page title, and meta descriptions, generating 20–30 queries balanced evenly across 5 intent buckets:
1. **Discovery**: *"What are the top rated [Category] platforms for businesses?"*
2. **Comparison**: *"[Brand] alternatives and competitors"*, *"[Brand] vs top market leaders"*
3. **Problem-Solution**: *"How do companies solve [Category] challenges?"*
4. **How-To**: *"How to get started with [Category] step by step guide"*
5. **Brand Direct**: *"What is [Brand] and what does it do?"*, *"Is [Brand] legitimate?"*

### Statistical Confidence Guarantee
LLMs are stochastic: identical queries yield different outputs across runs. Single-shot prompts produce noisy, unreliable data.
AuditIQ applies the **Wilson Score Interval** formula with 95% confidence ($z=1.95996$):
$$\text{Lower, Upper} = \frac{\hat{p} + \frac{z^2}{2n} \pm z \sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$
Every visibility report explicitly discloses both the empirical proportion and the sample size (e.g. `65.0% [95% CI: 45.2% - 81.3%, n=20]`).

---

## 5. Security & SSRF Defense

AuditIQ protects enterprise networks against Server-Side Request Forgery (SSRF) via `src/auditiq/crawler/ssrf.py`:
- Parses and resolves all hostnames to IPv4/IPv6 addresses via `socket.getaddrinfo()`.
- Verifies that target IPs do not fall into private, loopback, link-local, carrier-grade NAT, or cloud metadata ranges (`169.254.169.254`, `127.0.0.1`, `10.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12`).
- Restricts protocols strictly to `http://` and `https://` (blocking `file://`, `ftp://`, `gopher://`).
- Validates redirect target locations before dispatching subsequent requests.

---

## 6. Real-Time Server-Sent Events (SSE) Architecture

When a client launches an audit via `POST /api/v1/audits`:
1. `JobManager` creates an `AuditJob` with a unique deterministic SHA-256 ID and starts an async background task.
2. The client opens an `EventSource` connection to `/api/v1/audits/{id}/stream`.
3. The crawler and check engines dispatch atomic progress updates into an `asyncio.Queue`.
4. The SSE handler yields real-time JSON frames:
   ```json
   data: {"status": "crawling", "progress_pct": 35, "message": "Crawled (7/20): https://example.com/pricing"}
   ```
5. When the audit completes, the queue yields a completion frame and closes the connection cleanly.
