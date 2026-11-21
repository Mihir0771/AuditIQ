# AuditIQ Master Check Catalogue

This document catalogs all **55 registered checks** across the four audit layers in AuditIQ, detailing their immutable check IDs, layer assignments, severity, impact, effort, and verification rationale.

---

## Layer 1: Technical SEO (`technical`) — 27 Checks

| Check ID | Title | Severity | Impact | Effort | Description & Rationale |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `TECH-ROBOTS-PRESENCE` | robots.txt Presence & Accessibility | HIGH | 4 | S | Verifies that `/robots.txt` is present and returns HTTP 200 without syntax errors. |
| `TECH-ROBOTS-BLOCKING` | Accidental Disallow All in robots.txt | CRITICAL | 5 | S | Detects dangerous `Disallow: /` directives that block all crawlers from the root. |
| `TECH-SITEMAP-PRESENCE` | XML Sitemap Discovery & Validity | HIGH | 4 | S | Discovers `/sitemap.xml` via robots.txt or standard paths and validates XML structure. |
| `TECH-SITEMAP-COVERAGE` | Sitemap URL Coverage Ratio | MEDIUM | 3 | M | Compares crawled internal URLs against declared sitemap URLs to identify missing entries. |
| `TECH-STATUS-4XX-5XX` | Client (4xx) & Server (5xx) HTTP Errors | CRITICAL | 5 | M | Identifies broken links, 404s, and server failures across internal discovery paths. |
| `TECH-REDIRECT-CHAINS` | Multi-Hop Redirect Chains & Loops | HIGH | 4 | M | Flags redirect paths exceeding 2 hops that waste crawl budget and dilute link equity. |
| `TECH-ORPHAN-PAGES` | Orphan Pages (0 Inlinks Discovered) | HIGH | 4 | M | Identifies pages listed in sitemaps that have zero incoming internal navigational links. |
| `TECH-CRAWL-DEPTH` | Deep Click Depth (> 4 Hops) | MEDIUM | 3 | M | Flags deep navigational architecture requiring more than 4 clicks from the homepage. |
| `TECH-CANONICAL-MISSING` | Missing rel='canonical' Link Tag | HIGH | 4 | S | Detects pages lacking a self-referential or designated canonical URL. |
| `TECH-CANONICAL-CONFLICT` | Canonical URL Mismatch / Conflict | HIGH | 4 | S | Detects pages where the declared canonical points to a 404, redirect, or external domain. |
| `TECH-NOINDEX-ACCIDENTAL` | Accidental noindex on Production Pages | CRITICAL | 5 | S | Flags `<meta name="robots" content="noindex">` tags present on indexable production pages. |
| `TECH-HTTP-CONSISTENCY` | Mixed Content & Insecure HTTP Links | HIGH | 4 | S | Identifies insecure `http://` internal links or mixed passive/active content. |
| `TECH-WWW-CONSISTENCY` | Subdomain & Hostname Canonicalization | MEDIUM | 3 | S | Verifies consistent enforcement between `www.` and root domain redirects. |
| `TECH-TITLE-MISSING` | Missing or Empty <title> Tag | HIGH | 5 | S | Identifies pages missing `<title>` tags essential for SERP snippets and entity identification. |
| `TECH-TITLE-LENGTH` | Title Tag Length Hygiene (30–65 chars) | LOW | 2 | S | Flags titles that are truncated by SERP pixel limits (>65 chars) or too brief (<30 chars). |
| `TECH-META-DESC-MISSING` | Missing Meta Description | MEDIUM | 3 | S | Detects pages lacking `<meta name="description">` tags used for search snippet generation. |
| `TECH-META-DESC-LENGTH` | Meta Description Length (70–160 chars) | LOW | 2 | S | Flags meta descriptions exceeding 160 characters or falling below 70 characters. |
| `TECH-H1-MISSING-MULTI` | Missing or Multiple <h1> Headings | HIGH | 3 | S | Ensures exactly one primary `<h1>` landmark exists per document for topical hierarchy. |
| `TECH-HEADING-SKIPS` | Heading Level Sequence Skips | LOW | 2 | S | Identifies broken semantic heading sequences (e.g. `<h1>` jumping directly to `<h3>`). |
| `TECH-IMAGE-ALT-MISSING` | Images Missing Descriptive alt Attributes | MEDIUM | 3 | M | Flags content images lacking descriptive alternative text required for screen readers and AI vision. |
| `TECH-URL-HYGIENE` | Clean URL Hygiene (Uppercase/Parameters) | LOW | 2 | S | Identifies uppercase characters, spaces, or session tracking parameters in canonical paths. |
| `TECH-SCHEMA-SYNTAX` | JSON-LD Structured Data Syntax Validity | HIGH | 4 | S | Parses all `<script type="application/ld+json">` blocks and flags JSON syntax errors. |
| `TECH-SCHEMA-TYPES` | Schema.org Type Diversity & Relevance | MEDIUM | 3 | S | Verifies presence of rich Schema types (`Organization`, `Article`, `Product`, `WebSite`). |
| `TECH-PERF-PAGE-SIZE` | Heavy Document Payload (> 2.5 MB) | MEDIUM | 3 | M | Flags uncompressed HTML documents exceeding recommended bandwidth budgets. |
| `TECH-PERF-TTFB` | Server Time To First Byte (TTFB < 600ms) | HIGH | 4 | M | Measures server response latency; flags slow backend generation exceeding 600ms. |
| `TECH-PERF-VIEWPORT` | Mobile Responsive Viewport Meta Tag | HIGH | 4 | S | Verifies `<meta name="viewport" content="width=device-width, initial-scale=1">`. |
| `TECH-SECURITY-HEADERS` | Core HTTP Security Headers (HSTS, CSP) | MEDIUM | 3 | S | Checks for `Strict-Transport-Security`, `X-Content-Type-Options`, and `Content-Security-Policy`. |

---

## Layer 2: Content & Entity Quality (`content`) — 13 Checks

| Check ID | Title | Severity | Impact | Effort | Description & Rationale |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `CONT-FLESCH-READING-EASE` | Flesch Reading Ease Comprehension | MEDIUM | 3 | M | Calculates syllable-to-sentence ratio; flags dense, bureaucratic text (<30 ease). |
| `CONT-WALL-OF-TEXT` | Paragraph Length Hygiene (<150 words) | LOW | 2 | S | Flags dense monolithic paragraphs lacking breathing room and visual whitespace. |
| `CONT-THIN-CONTENT` | Thin Content Detection (<250 words) | HIGH | 4 | M | Identifies low-word-count doorway or placeholder pages providing negligible value. |
| `CONT-SENTENCE-VARIETY` | Sentence Length Variety & Rhythm | LOW | 2 | S | Flags monotonous repetitive sentence structures that impair comprehension. |
| `CONT-ANSWER-FIRST` | Answer-First Inverted Pyramid Layout | HIGH | 4 | M | Verifies that key answers or value propositions appear in the first 100 words of the body. |
| `CONT-QUESTION-SUBHEADINGS` | Question-Intent Subheading Hierarchy | MEDIUM | 3 | S | Detects question-framed headings (Who/What/Why/How) matching conversational voice intent. |
| `CONT-FAQ-SCHEMA` | FAQPage / Q&A Structured Data Markup | MEDIUM | 3 | S | Verifies Schema.org `FAQPage` markup formatting for direct SERP accordion integration. |
| `CONT-FACT-DENSITY` | Factual Evidence & Numerical Density | HIGH | 4 | M | Detects empirical figures, percentages, dates, and currency values that AI engines quote. |
| `CONT-OUTBOUND-CITATIONS` | Authoritative Outbound Source Citations | MEDIUM | 3 | S | Verifies external citations linking to authoritative sources (.edu, .gov, peer-reviewed, wiki). |
| `CONT-AUTHOR-BYLINE` | Visible Author Byline & E-E-A-T Proof | HIGH | 4 | S | Checks for named author bylines, credentials, and links to author bio profile pages. |
| `CONT-TRUST-PAGES` | Essential Trust Pages (About, Contact, Privacy) | HIGH | 4 | S | Verifies existence of linked About Us, Contact, and Privacy Policy transparency pages. |
| `CONT-CONTENT-FRESHNESS` | Content Freshness & Publication Dates | MEDIUM | 3 | S | Identifies `datePublished` / `dateModified` timestamps; flags stale unmaintained pages. |
| `CONT-SIMHASH-DUPLICATE` | Simhash Near-Duplicate Cannibalization | HIGH | 4 | M | Uses 64-bit Simhash LSH Hamming distance to flag $\ge 85\%$ near-duplicate page pairs. |

---

## Layer 3: GEO Readiness (`geo_readiness`) — 11 Checks

| Check ID | Title | Severity | Impact | Effort | Description & Rationale |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `GEO-BOT-ACCESS` | AI Bot Access Matrix (Training vs. Search) | CRITICAL | 5 | S | Evaluates `robots.txt` access across the 3-way taxonomy; flags blocked search bots. |
| `GEO-FIREWALL-BLOCKS` | CDN / WAF Bot Challenge or 403 Page | CRITICAL | 5 | M | Detects Cloudflare or CloudFront managed challenge/CAPTCHA screens blocking crawlers. |
| `GEO-RENDER-DIFF-TEXT` | Client-Side Render Text Loss (Raw vs Headless) | HIGH | 5 | L | Measures text loss when JavaScript is unexecuted; flags CSR apps invisible to AI bots. |
| `GEO-RENDER-DIFF-LINKS` | Client-Side Render Link Discovery Loss | HIGH | 4 | M | Detects internal navigational links inserted exclusively via client JavaScript. |
| `GEO-SEMANTIC-HTML` | Semantic HTML Structure vs. Div Soup | MEDIUM | 3 | M | Computes ratio of semantic landmarks (`<main>`, `<article>`) vs. non-semantic `<div>` containers. |
| `GEO-TRAPPED-TEXT` | Text Trapped in Canvas, Iframes, or SVGs | MEDIUM | 4 | M | Flags critical information locked inside `<canvas>` or `<iframe>` without accessible DOM text. |
| `GEO-DATA-TABLES` | Data Presentation Semantics (Tables vs Grids) | LOW | 3 | S | Verifies that tabular statistics use semantic `<table>`, `<thead>`, and `<th>` elements. |
| `GEO-PASSAGE-CHUNKING` | RAG & AI Passage Chunkability (100–300 words) | MEDIUM | 4 | M | Analyzes text section sizes under subheadings for optimal vector embedding retrieval. |
| `GEO-LLMS-TXT` | /llms.txt Standard File for AI Agent Context | INFO | 3 | S | Checks for existence and valid Markdown formatting of `/llms.txt` and `/llms-full.txt`. |
| `GEO-ENTITY-SAMEAS` | Entity Disambiguation via JSON-LD sameAs | HIGH | 5 | S | Verifies Organization `sameAs` links pointing to Wikidata, Wikipedia, Crunchbase, LinkedIn. |
| `GEO-BOT-LATENCY` | Bot Response Latency (TTFB < 800ms) | HIGH | 4 | M | Checks crawler latency; flags response times exceeding real-time AI search timeout thresholds. |

---

## Layer 4: Live AI Visibility (`live_visibility`) — 4 Checks

| Check ID | Title | Severity | Impact | Effort | Description & Rationale |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `LIVE-MENTION-RATE` | Brand Mention Rate in Generative AI Answers | HIGH | 5 | L | Measures % of contextual search queries where the brand is recommended (95% Wilson CI). |
| `LIVE-CITATION-RATE` | Domain Citation Rate (Direct Source Backlinks) | HIGH | 5 | L | Measures % of queries where the domain is cited as an authoritative link (95% Wilson CI). |
| `LIVE-SHARE-OF-VOICE` | Competitive AI Share of Voice | MEDIUM | 4 | L | Computes proportion of total brand mentions won against competing products. |
| `LIVE-TOP-CITED-DOMAINS` | Top Cited Domain Authority Benchmark | INFO | 3 | M | Identifies third-party websites (G2, Reddit, Forbes) winning citation share for target topics. |
