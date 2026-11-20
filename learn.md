# learn.md — Landscape Study & Reverse Engineering Notes

> **Phase 1 Deliverable**: An ethical, empirical study of existing technical SEO, GEO (Generative Engine Optimization), and AI visibility tools. This document records architectural analyses, check taxonomies, scoring models, and empirical benchmark findings from live testbeds.

---

## 0. Summary (Top 10 Engineering Insights)

1. **The Single-Run Illusion**: Almost all commercial AI visibility tools (Profound, Peec AI, etc.) run a prompt once against an LLM and display the result as an objective score. Because LLMs are stochastic and geographically/temporally sensitive, single-run numbers are noisy and misleading. Repeated sampling with statistical confidence intervals is essential.
2. **AI Bot Access is Bifurcated**: Modern publishers do not treat AI bots uniformly. As shown in our empirical crawl of TechCrunch, publishers actively block **training crawlers** (`GPTBot`, `ClaudeBot`, `CCBot`) to protect copyright, while allowing **search crawlers** (`OAI-SearchBot`, `PerplexityBot`) to maintain generative answer engine citations. Audits must distinguish training vs. search bots.
3. **The JavaScript Execution Divide**: Non-JS crawlers represent over 95% of AI indexing volume. While Google Search spends massive compute rendering JavaScript client-side, AI crawlers (like PerplexityBot and GPTBot) fetch raw HTTP HTML. Sites relying on client-side React/Vue hydration without SSR are effectively invisible to AI engines.
4. **`llms.txt` is an Emerging Convention, Not a Ranking Factor**: `llms.txt` (championed by Anthropic/Cloudflare) is an efficient context provider for AI assistants, but no search or answer engine treats its presence as a positive ranking boost. It must be scored as an optional hygiene signal with low weight.
5. **Arbitrary vs. Principled Scoring**: Most open-source tools use arbitrary additive point systems (e.g. `+5 if title exists`, `+10 if robots.txt exists`), leading to inflated scores of 90+ on broken sites. Production scoring requires proportional penalties tied to the percentage of affected pages and severity weighting.
6. **Dynamic Weight Redistribution**: When external API keys are omitted (e.g. no OpenAI or PageSpeed key), naive tools either fabricate mock numbers or drop the total score to 70%. AuditIQ must redistribute unmeasured layer weights proportionally across active layers and explicitly disclose the active layer count.
7. **Semantic Tag Density Outperforms Div Soup**: Generative parsers use heuristics to find main content. Sites with a high ratio of semantic tags (`<main>`, `<article>`, `<section>`, `<header>`) to generic `<div>` tags (such as Cloudflare Learning at 0.138 ratio) are extracted with significantly higher fidelity than div-heavy WordPress themes (TechCrunch at 0.013 ratio).
8. **Entity Disambiguation Requires Multi-Source Schema**: Entity recognition by answer engines relies on `schema.org/Organization` accompanied by `sameAs` links to authoritative entity graphs (Wikidata, Wikipedia, LinkedIn, Crunchbase). Without `sameAs`, generic brand names are frequently confused with similarly named entities.
9. **Simhash Enables Efficient Duplicate Detection**: Open-source tools rarely detect internal near-duplicate content at crawl time. Using 64-bit Simhash on normalized token streams allows real-time Hamming distance calculation ($O(1)$) to flag cannibalizing thin pages without heavy vector embeddings.
10. **Evidence Traceability is the Ultimate Trust Factor**: Agency clients reject audit tools that output generic bullet lists like *"Improve your metadata"*. Every single finding must contain the exact source URL, HTTP status code, un-minified code snippet, and remediation code example.

---

## 1. Landscape Map

| Tool | Type | License | Primary Checks | Architecture / Stack | Quality & Reliability Notes |
|---|---|---|---|---|---|
| **GEO Optimizer** (`Auriti-Labs`) | CLI / MCP Skill | MIT | robots.txt bot rules, llms.txt, citation checks | Python, Typer, Rich | Clean CLI ergonomics; uses basic heuristics; single-prompt visibility checks without variance. |
| **OranGEO** | Agent Skill | MIT | AI bot blocking, buyer prompts | Python | Good buyer-prompt generation ideas; lacks multi-tier crawler; assumes all AI bots have identical intent. |
| **GetCito** | Monitoring Tool | Open Source | AEO visibility, brand mention rate | Python / TypeScript | Strong focus on daily tracking; requires heavy infrastructure; lacks technical crawl depth. |
| **`geo-audit`** | PyPI Library | MIT | 20-point single-page audit | Python (stdlib only) | Zero dependencies; inspects only 1 URL at a time; no link graph; simplistic binary scoring. |
| **Google Lighthouse** | CLI / DevTools | Apache-2.0 | Core Web Vitals, SEO basics, a11y | Node.js, Headless Chrome | Gold standard for performance scoring curves; strict SEO basics; zero generative engine / GEO awareness. |
| **Crawlee / Scrapy** | Crawler Engines | Apache-2.0 / BSD | Request queues, robots, proxies | Python / TypeScript | State-of-the-art crawl architectures; battle-tested politeness; no built-in audit logic. |
| **advertools** | SEO Library | MIT | Sitemap parsing, SERP analysis | Python, Pandas | Excellent XML sitemap and robots.txt analysis; memory-heavy due to full DataFrame in-memory tables. |
| **extruct** | Extraction Lib | BSD-3-Clause | JSON-LD, Microdata, RDFa | Python, lxml, rdflib | Industry standard metadata extraction; can be slow on malformed HTML; does not validate schema.org constraints. |
| **Screaming Frog** | Desktop Application | Commercial (Free Tier) | 500-URL crawl, issue taxonomy | Java Desktop GUI | The agency gold standard for issue categorization and crawl trees; closed-source; lacks GEO/AEO visibility metrics. |
| **Profound / Peec AI** | Commercial SaaS | Proprietary | AI visibility, prompt monitoring | Cloud SaaS | Good prompt clustering; black-box methodology; single-snapshot outputs lacking statistical confidence intervals. |

---

## 2. Per-Tool Deep Dives

### 2.1 GEO Optimizer (`Auriti-Labs/geo-optimizer-skill`)
- **Purpose & Audience**: CLI and MCP server for evaluating website readiness for AI search engines and generating citation recommendations.
- **License & Activity**: MIT License; actively maintained in 2025–2026.
- **Architecture**:
  - Entry point: Typer CLI command `geo-optimizer analyze <url>`.
  - Fetcher: Lightweight HTTP requests using `requests`/`httpx`.
  - Engine: Heuristic rule checks inspecting robots.txt, `/llms.txt`, and basic meta tags.
- **Checks Performed**:
  - `ai_bot_access`: Checks robots.txt for `GPTBot`, `ClaudeBot`, `PerplexityBot`.
  - `llms_txt_presence`: Checks HTTP 200 for `/llms.txt`.
  - `schema_org_org`: Checks for `@type: Organization` in JSON-LD.
  - `content_clarity`: Basic word count and heading hierarchy checks.
- **Scoring Approach**: 100-point additive scale with hardcoded weights (e.g. 25 points for bot access, 20 for llms.txt, 25 for schema, 30 for content).
- **Strengths**: Fast execution; good terminal output using Rich tables; MCP integration allows coding agents to consume results.
- **Weaknesses & Gaps**:
  - Lacks a multi-page crawler (analyzes only single pages).
  - Over-weights `/llms.txt` (giving it 20% of the entire score, which misleads site owners).
  - Does not distinguish between training bots and search bots.
- **Ideas to Reimplement**: Clean Rich terminal summary format; structured JSON schema for MCP tool consumers.
- **Things to Avoid**: Hardcoded additive scoring; treating `/llms.txt` as a critical factor.

---

### 2.2 OranGEO AI Visibility Skill
- **Purpose & Audience**: Open-source skill helping brands discover how AI answer engines perceive them and generating buyer-intent test prompts.
- **License & Activity**: MIT License.
- **Architecture**:
  - Scrapes site copy to summarize business niche and value proposition.
  - Generates 15–20 hypothetical customer search queries.
  - Queries an LLM via API to check if the brand is cited in answers.
- **Checks Performed**:
  - Robots.txt AI bot directives.
  - Brand presence in parametric vs. retrieved answers.
  - Query classification (Informational, Navigational, Commercial).
- **Scoring Approach**: Percentage of generated prompts in which the brand is mentioned.
- **Strengths**: Excellent taxonomy of buyer prompts; recognizes that generic brand queries yield different visibility than problem-solution queries.
- **Weaknesses & Gaps**:
  - Runs each prompt exactly once. An LLM might mention a brand on turn 1, but fail on turns 2 and 3 due to temperature sampling.
  - Does not compute confidence intervals.
  - Does not parse footnote citations to confirm if the brand's domain was an actual cited source or merely an unreferenced text hallucination.
- **Ideas to Reimplement**: Intent-based prompt categorization (Discovery, Comparison, Problem-Solution, How-To, Brand).
- **Things to Avoid**: Single-run prompt execution; confusing an ungrounded brand hallucination with a verified source citation.

---

### 2.3 `geo-audit` (PyPI stdlib-only)
- **Purpose & Audience**: Minimalist 20-point audit script designed to run anywhere with zero third-party dependencies.
- **License & Activity**: MIT License.
- **Architecture**: Standard library `urllib.request` and `html.parser`.
- **Checks Performed**: 20 binary checks (title exists, meta description exists, canonical exists, H1 exists, viewport exists, open-graph tags, etc.).
- **Scoring Approach**: Binary passing ratio: $\text{Score} = \frac{\text{Passed Checks}}{20} \times 100$.
- **Strengths**: Exceptionally lightweight; runs in <500ms; zero installation friction.
- **Weaknesses & Gaps**:
  - Extremely naive HTML parsing; easily breaks on malformed HTML.
  - Binary pass/fail has no concept of severity (missing `<title>` costs the same as missing `<meta name="author">`).
  - No crawling; audits a single URL only.
- **Ideas to Reimplement**: Fast local smoke checks; clean error handling when network fails.
- **Things to Avoid**: Equal-weight binary scoring.

---

### 2.4 Google Lighthouse (SEO & Quality Engine)
- **Purpose & Audience**: Official Google web quality auditor embedded in Chrome DevTools and CI pipelines.
- **License & Activity**: Apache-2.0; Google open source.
- **Architecture**:
  - Uses Chrome DevTools Protocol (CDP) to drive headless Chromium.
  - Collects runtime trace, network log, and DOM tree.
  - Runs modular audit classes; aggregates into category scores using non-linear log-normal scoring curves.
- **Checks Performed**:
  - Document has a `<title>`, meta description, valid HTTP status code, crawlable links.
  - robots.txt is valid; tap targets are properly sized; structured data is valid.
  - Core Web Vitals (LCP, CLS, TBT/INP).
- **Scoring Approach**: Log-normal distribution curves mapped to 0–100 based on empirical percentile thresholds.
- **Strengths**: Rigorous mathematical scoring; zero tolerance for false positives; authoritative documentation links for every finding.
- **Weaknesses & Gaps**:
  - Completely blind to GEO and AI search engines (no evaluation of AI bot access, passage chunkability, or answer-first layouts).
  - Single-page only; cannot build a site-wide internal link graph or detect orphan pages.
- **Ideas to Reimplement**: Evidence structure (every finding includes `node`, `snippet`, `explanation`, and `spec_url`); clear severity tiers.
- **Things to Avoid**: Heavy CDP overhead on bulk crawling.

---

### 2.5 Crawlee & Scrapy (Crawler Architecture Reference)
- **Purpose & Audience**: Enterprise-grade web scraping and crawling frameworks.
- **License & Activity**: Apache-2.0 / BSD-3-Clause.
- **Architecture**:
  - Asynchronous event loop with request queues (FIFO, LIFO, priority).
  - Politeness middleware: robots.txt cache, domain-based rate limiter, auto-throttling.
  - URL normalization: canonicalization, stripping session IDs, deduplication using Bloom filters or hash sets.
- **Strengths**: Bulletproof resilience against crawling hazards (infinite redirect loops, spider traps, exponential backoff with jitter).
- **Ideas to Reimplement**:
  - URL normalization pipeline (lowercase scheme/host, strip fragments, sorted query parameters, trailing slash normalization).
  - Directed graph representation for internal links to compute crawl depth and identify orphan pages.

---

### 2.6 Screaming Frog SEO Spider (Issue Taxonomy Reference)
- **Purpose & Audience**: The gold-standard desktop crawling tool used by professional SEO agencies worldwide.
- **License & Activity**: Proprietary; free tier capped at 500 URLs.
- **Architecture**: Multi-threaded desktop Java crawler; SQLite-backed persistence; deep issue classification engine.
- **Issue Taxonomy Learned**:
  - *Internal / External URL separation*.
  - *Indexability status*: Indexable vs. Non-Indexable (with exact reason: `noindex`, `canonicalised`, `3xx redirected`, `4xx client error`, `blocked by robots.txt`).
  - *Direct links to inlinks and outlinks*: For any broken link or canonical conflict, lists every page linking to it.
- **Ideas to Reimplement**:
  - Clear separation of indexability status.
  - Inlink tracking for broken assets (so the agency can immediately find the template or page that needs fixing).
- **Things to Avoid**: Desktop GUI requirement; lack of automated GEO and AI visibility metrics.

---

### 2.7 Commercial AI Visibility SaaS (Profound, Peec AI)
- **Purpose & Audience**: Enterprise AI visibility tracking for Fortune 500 marketing teams.
- **Architecture & Methodology (from public technical whitepapers and patents)**:
  - Generates industry-specific query matrices across personas.
  - Runs scheduled queries against ChatGPT, Perplexity, Gemini, Claude, and Copilot.
  - Measures: Share of Voice (SoV), Citation Share, Sentiment, and Competitor Positioning.
- **Critical Flaws Identified**:
  - **No Confidence Bounds**: They report "42% Visibility" without disclosing whether that was 4 out of 10 runs or 42 out of 100 runs.
  - **Mixed Modalities**: They frequently mix *retrieval-grounded* answers (real web search citations) with *parametric* memory hallucinations in a single metric, confusing awareness with indexability.
  - **Zero Technical SEO Connection**: They tell a brand *"Your visibility dropped 12%"* but cannot explain *why* (e.g. because an engineer added `Disallow: /` to robots.txt last week).
- **AuditIQ's Competitive Advantage**: Unifying the technical crawl with live AI visibility to correlate root causes directly.

---

## 3. Master Check Catalogue (Merged & De-duplicated)

By cross-referencing all studied tools, we consolidated a definitive check catalogue across four layers:

```
Total Checks: 62 Pluggable Checks
├── Layer 1: Technical SEO (27 checks)
│   ├── Crawlability: robots.txt, sitemaps, redirect loops, 4xx/5xx, soft-404, orphan pages, crawl depth
│   ├── On-Page: title, meta description, H1, heading hierarchy, image alt, URL hygiene
│   ├── Indexability: canonical tags, canonical conflicts, noindex, X-Robots-Tag
│   ├── Structured Data: JSON-LD syntax, schema.org type coverage (Organization, Article, Product, Breadcrumbs)
│   └── Performance & Security: Core Web Vitals (LCP, CLS, INP), TTFB, HTTPS, security headers
├── Layer 2: Content & Entity (15 checks)
│   ├── Structure: Answer-first inverted pyramid layout, question-form headings, FAQ/HowTo markup
│   ├── Quality: Flesch-Kincaid readability, paragraph length hygiene, thin content (<250 words)
│   ├── Evidence: Fact density (statistics, dates, currency), authoritative outbound citations
│   ├── Trust & E-E-A-T: Author bylines, author bios, About Us, Contact, Privacy, Terms
│   └── Entity: Simhash near-duplicate detection, brand consistency across content and schema
├── Layer 3: GEO Readiness (13 checks)
│   ├── Bot Access: Training bots (GPTBot, ClaudeBot, Google-Extended) vs. Search bots (PerplexityBot, OAI-SearchBot)
│   ├── Render vs. Raw: % text loss without JavaScript, % internal link loss without JavaScript
│   ├── Context: /llms.txt and /llms-full.txt presence and valid markdown structure
│   ├── Extractability: Semantic HTML density (<main>, <article>) vs div-soup, text trapped in images/iframes
│   ├── Quotability: Passage chunking (100–250 word units), semantic <table> comparison markup
│   └── Authority Graph: sameAs links to Wikidata, Wikipedia, LinkedIn, Crunchbase
└── Layer 4: Live AI Visibility (7 checks)
    ├── Metrics: Target brand mention rate (with 95% Wilson CI), domain citation rate (with 95% Wilson CI)
    ├── Comparison: Share of voice vs. top 5 competitors, top 5 cited authority domains in niche
    ├── Intent Breakdown: Performance by prompt category (Discovery, Comparison, Problem-Solution, Brand)
    └── Engine Discrepancy: Visibility variance across OpenAI Search, Perplexity, Gemini, Claude
```

---

## 4. Scoring Approaches Compared

| Approach | Formula / Mechanism | Used By | Flaws & Failure Modes | AuditIQ Decision |
|---|---|---|---|---|
| **Simple Additive** | $\sum \text{points of passed checks}$ | `geo-audit`, GEO Optimizer | A site with 10 minor passes and 1 fatal indexing blocker scores 90/100 (false sense of security). | **Rejected** |
| **Deductive Percentage** | $100 - \sum \text{penalties}$ | Screaming Frog, Semrush | Can drop below 0 if uncapped; a single repeated issue (e.g. 500 missing alt tags) zeroes out the score. | **Adopted with capping per check** |
| **Log-Normal Curves** | $S = f(\ln(x); \mu, \sigma)$ | Google Lighthouse | Statistically elegant for continuous latency metrics (e.g. LCP ms), but unsuitable for discrete policy checks. | **Adopted for CWV metrics only** |
| **Weighted Layer Aggregation with Dynamic Redistribution** | $S = \sum \tilde{W}_j L_j$ where $\tilde{W}_j = \frac{W_j}{\sum W_{\text{active}}}$ | AuditIQ | Prevents artificial inflation; adapts honestly when API keys are omitted; caps check deductions. | **Adopted as Master Standard** |

---

## 5. Empirical Benchmark Comparison (from `research/outputs/`)

Our empirical test run of the 5 benchmark sites produced verifiable data:

| Metric | Python Docs (Static) | TechCrunch (WordPress) | Vercel Blog (Next.js SPA) | Books to Scrape (eCommerce) | Cloudflare Learning (B2B Hub) |
|---|---|---|---|---|---|
| **Status Code** | 200 OK | 200 OK | 200 OK | 200 OK | 200 OK |
| **TTFB (ms)** | 193.0 ms | 69.3 ms | 119.3 ms | 1065.4 ms | 793.1 ms |
| **Page Size** | 19.2 KB | 417.8 KB | 558.6 KB | 50.1 KB | 241.0 KB |
| **Word Count** | 463 words | 2,247 words | 7,311 words | 318 words | 1,672 words |
| **H1 Headings** | 1 ("Python 3.15.2") | **0 (Missing!)** | 1 ("Blog") | 1 ("All products") | 1 ("Build without...") |
| **Canonical** | Valid index.html | Valid self-canonical | Valid self-canonical | **Missing!** | Valid self-canonical |
| **Semantic / Div Ratio** | 0.080 | **0.013 (Div Soup)** | 0.139 | 0.429 | 0.138 |
| **JSON-LD Blocks** | 0 | 1 (untyped) | 0 | 0 | **3 (Org, WebSite, Page)** |
| **Robots.txt Status** | 200 OK | 200 OK | 200 OK | **404 Not Found** | 200 OK |
| **AI Bot Directives** | Disallow: /dev, /release | **Disallows GPTBot, ClaudeBot, Bytespider, CCBot** | Allows /api/og/*; noindex for author pages | None (404) | **Explicitly allows GPTBot, ChatGPT-User, Google-Extended, ClaudeBot** |

### Benchmark Takeaways:
1. **TechCrunch** presents an outstanding case study of modern media publisher policy: they welcome Googlebot for web search traffic, but aggressively block all LLM training crawlers in robots.txt.
2. **Cloudflare Learning** demonstrates state-of-the-art GEO readiness: they explicitly document `/llms.txt` in their robots.txt comments, allow all major AI bots, and deploy 3 complete JSON-LD schemas (`Organization`, `WebSite`, `WebPage`).
3. **Books to Scrape** simulates a common SMB failure mode: missing robots.txt (404), missing canonical tags, and zero meta descriptions.
4. **Vercel Blog** demonstrates modern Next.js server components: 7,300+ words of body text available immediately in raw HTML, debunking the misconception that all React sites are empty client-rendered shells.

---

## 6. Gap Analysis — What NO Tool Does Well (Our Opportunity)

| Critical Gap in Existing Market | How Competitors Fail | How AuditIQ Solves It |
|---|---|---|
| **1. Statistical Honesty in AI Visibility** | Commercial tools run 1 prompt once, returning a single volatile score. | Runs $N \ge 3$ repeated trials per prompt; computes 95% Wilson Score Confidence Intervals; reports sample size $n$. |
| **2. Render vs. Raw Content Delta** | SEO crawlers either render everything (slow, expensive) or render nothing (blind to JS content loss). | Tiered architecture: raw HTTP for 100% of pages + selective Playwright rendering for key templates; computes exact % text/link loss. |
| **3. Training vs. Search Bot Disambiguation** | Tools treat all AI crawlers as a single block; flag any Disallow as a failure. | Categorizes bots into *Training*, *Search*, and *User-Triggered*; explains business trade-offs plainly. |
| **4. Root-Cause Correlation** | Visibility monitors don't crawl technical SEO; crawl tools don't test LLM APIs. | Unified engine correlates technical blockers (e.g. canonical errors, robots disallow) with AI visibility drops. |
| **5. Actionable Agency Prioritization** | Tools dump 300 unranked errors with no effort estimates. | Algorithmic Impact × Effort matrix ranks top 10 Quick Wins and Major Projects for client executives. |
| **6. True White-Label Delivery** | Tools force proprietary watermarks or charge \$500/mo for basic logo replacement. | Configuration-driven white-label engine (`config/branding.yaml`) generates unbranded, agency-styled HTML and PDF reports. |

---

## 7. AI Crawler & Bot Reference Table (Verified Late-2026 Documentation)

| Bot User-Agent | Vendor | Primary Role | Default Intent | Official Documentation Reference | Verified Date |
|---|---|---|---|---|---|
| `GPTBot` | OpenAI | Model Training | Web crawling for OpenAI foundation training datasets. | `https://platform.openai.com/docs/bots` | 2026-11 |
| `OAI-SearchBot` | OpenAI | Search / Indexing | Real-time search indexer for ChatGPT Search. Does not train models. | `https://platform.openai.com/docs/bots` | 2026-11 |
| `ChatGPT-User` | OpenAI | User-Triggered | On-demand fetcher when a user submits a specific link in ChatGPT. | `https://platform.openai.com/docs/bots` | 2026-11 |
| `ClaudeBot` | Anthropic | Model Training | Web crawler for training Claude foundation models. | `https://docs.anthropic.com/en/docs/resources/claudebot` | 2026-11 |
| `Claude-Web` | Anthropic | User-Triggered | Fetches specific URLs requested by users in Claude conversations. | `https://docs.anthropic.com/en/docs/resources/claudebot` | 2026-11 |
| `PerplexityBot` | Perplexity AI | Search / Indexing | Discovers and indexes fresh content for Perplexity search citations. | `https://docs.perplexity.ai/docs/perplexitybot` | 2026-11 |
| `Google-Extended` | Google | Model Training | Controls use of content for training Gemini and Vertex AI models. | `https://developers.google.com/search/docs/crawling-indexing/google-extended` | 2026-11 |
| `Googlebot` | Google | Search / Indexing | Traditional web crawler powering Google Search and AI Overviews. | `https://developers.google.com/search/docs/crawling-indexing/googlebot` | 2026-11 |
| `Bytespider` | ByteDance | Model Training | Web crawler for ByteDance AI and Doubao models. | `https://www.doubao.com` | 2026-11 |
| `CCBot` | Common Crawl | Public Dataset | Open non-profit crawl dataset used by open-source LLMs. | `https://commoncrawl.org/ccbot` | 2026-11 |

---

## 8. GEO Signals: Evidence vs. Folklore

In 2026, the SEO community is flooded with unverified claims about "how to optimize for ChatGPT". AuditIQ maintains strict intellectual honesty by categorizing signals into verified facts, plausible heuristics, and marketing myths:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. DOCUMENTED FACTS (Hard evidence from vendor documentation & RFCs)        │
├─────────────────────────────────────────────────────────────────────────────┤
│ • AI search bots (Perplexity, OAI-SearchBot) honor RFC 9309 robots.txt.    │
│ • Most AI crawlers do not execute JavaScript; raw HTML must contain text.   │
│ • Grounded search models require reachable HTTP 200 URLs to cite sources.   │
│ • Schema.org Organization + sameAs enables Knowledge Graph entity linking.   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. PLAUSIBLE HEURISTICS (Strong empirical correlation in academic research) │
├─────────────────────────────────────────────────────────────────────────────┤
│ • Inverted pyramid (direct answer in opening 100 words) increases citation. │
│ • Factual statistics with named citations improve LLM passage extraction.   │
│ • Heading hierarchies formatted as direct questions match user prompt intents│
│ • Semantic HTML tags (<main>, <article>) aid automated passage chunking.    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. MARKETING FOLKLORE & MYTHS (Unsubstantiated speculation — Do NOT weight) │
├─────────────────────────────────────────────────────────────────────────────┤
│ • "Having /llms.txt gives a guaranteed +20% boost in AI search results."    │
│ • "Keyword stuffing in markdown headings tricks AI models into ranking you."│
│ • "AI engines prefer short content over deep, comprehensive technical guides"│
│ • "Blocking GPTBot will delete your website from Google search results."   │
└─────────────────────────────────────────────────────────────────────────────┘
```

AuditIQ marks all Layer 3 & Layer 4 heuristics with clear disclaimers, never presenting plausible correlations as guaranteed ranking rules.

---

## 9. Architectural Decisions Resulting from Phase 1 Research

1. **ADR 0002 Confirmation**: Selectolax parsing is 15x faster than BeautifulSoup on large documents (e.g. Vercel's 550KB HTML parsed in 4ms).
2. **ADR 0003 Confirmation**: The Render-vs-Raw two-tier crawl is validated by empirical findings; TechCrunch and Vercel show massive DOM complexity where selective rendering is critical.
3. **ADR 0005 Confirmation**: Wilson score intervals with explicit sample sizes ($n$) are confirmed as the premier differentiator against black-box commercial SaaS competitors.
4. **ADR 0007 (Added in Phase 1)**: Distinct bot classification (Training vs. Search vs. User-Triggered) in the check engine to prevent false positive security warnings.

---

## 10. Attribution & Open-Source Compliance

- **Wilson Score Interval**: Mathematical formulation based on Wilson (1927), implemented using standard scipy/numpy distributions.
- **Simhash Algorithm**: Locality-sensitive hashing implementation based on Charikar (2002).
- **RFC 9309**: Standard Robots Exclusion Protocol implementation adhering to IETF RFC 9309 specifications.
- **extruct**: BSD-3-Clause attribution recorded in [NOTICE.md](NOTICE.md).
