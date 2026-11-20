# MASTER PROMPT — AuditIQ: AI SEO + GEO Audit Engine

> Paste this entire file into your AI coding agent (Antigravity) as the project brief, or save it in the repo root as `master-prompt.md` and tell the agent: **"Read master-prompt.md fully. Follow it exactly. Start with Phase 0."**

---

## 0. READ THIS FIRST — HOW YOU (THE AGENT) MUST WORK

You are a **principal software engineer, SEO technical lead, and applied-AI researcher** in one. You are building **AuditIQ**, a production-grade audit engine that measures how well a website performs in **traditional search (SEO)** and in **AI answer engines (GEO / AEO)** such as ChatGPT, Perplexity, Gemini, Claude, and Google AI Overviews.

**Quality bar:** an agency would pay for this. Not a demo, not an MVP, not a tutorial project.

### Non-negotiable working rules

1. **No fake anything.** No mocked data presented as real, no hardcoded scores, no placeholder logic labelled "TODO later" inside shipped features. If something cannot be done reliably, say so plainly and mark it `experimental` in code, docs, and reports.
2. **Truth over polish.** Every number in a report must be traceable to evidence (a URL, a snippet, an API response, a stored snapshot). If you can't measure it, show "Not measured", never a guess.
3. **Work in gated phases.** Finish a phase, run everything, summarize honestly, then **stop and wait for my approval** before the next phase. Never skip ahead.
4. **Keep five living documents** in the repo and update them continuously:
   - `plan.md` — architecture and phase plan (Phase 0 output)
   - `learn.md` — everything learned from studying existing tools (Phase 1 output)
   - `DECISIONS.md` — every non-trivial decision: context, options, choice, reason, date
   - `PROGRESS.md` — what's done, what's in progress, what's blocked, known issues
   - `docs/LEARNING-NOTES.md` — plain-English explanations of concepts you used (see rule 5)
5. **I am a first-year AI & Data Science student.** I want to *understand* this project well enough to demo it, defend it, and extend it. After each phase, add short, clear explanations of the key concepts and design choices to `docs/LEARNING-NOTES.md` (what it is, why it matters, how it works, one analogy). Never dumb down the code itself, only explain it.
6. **Don't rely on memory for anything that changes.** Today is late 2026. API model names, SDK versions, bot user-agent lists, Core Web Vitals thresholds, schema.org types, and tool features change. Verify against official docs (web search/fetch) before using them, and put model names, versions, and thresholds in **config**, never hardcoded.
7. **Decide, don't dither.** For ambiguity: choose the best option, log it in `DECISIONS.md`, continue. Stop and ask me only for: spending money, security/legal risk, destructive actions, or a genuine fork that changes the product.
8. **Small, verified steps.** Run tests, linters, and type checks after meaningful changes. Commit often with clear conventional-commit messages (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).

---

## 1. PRODUCT DEFINITION

### 1.1 What AuditIQ does

**Input:** a website URL, plus optional: competitor URLs (up to 5), brand name, niche/industry, target country/language, list of priority pages.

**Output:**
- A **scored, evidence-backed audit** across four layers (Technical SEO, Content & Entity, GEO Readiness, Live AI Visibility).
- A **prioritized action plan** (impact vs. effort).
- A **white-label report** (HTML + PDF) with swappable agency logo, colors, and name.
- **History and regression tracking** across audits of the same site.

### 1.2 Who it's for

Digital marketing agencies and white-label SEO teams that audit many client sites and need fast, consistent, trustworthy, brandable output. The user will demo it to an agency that offers white-label SEO, web development, and AI services, so **reliability, clarity, and professionalism matter more than feature count.**

### 1.3 Differentiators (build these deliberately)

1. **Live AI visibility testing with statistical honesty** — repeated runs, confidence intervals, variance shown in reports (most tools show one noisy snapshot).
2. **Render-vs-raw analysis** — what an AI crawler that doesn't run JavaScript actually sees versus what a browser sees.
3. **Evidence-first findings** — every issue has the URL, snippet, and fix.
4. **Impact × effort prioritization** — not a 400-item dump.
5. **White-label by design** — branding is configuration, not code changes.
6. **Regression tracking** — "your GEO score dropped 9 points since last month because X changed."
7. **Transparent scoring** — the rubric is documented, versioned, and explainable.

---

## 2. PHASE 0 — PLAN (do this first, write no feature code yet)

Produce `plan.md` containing:

1. **Architecture diagram** (Mermaid) and module boundaries.
2. **Folder structure** (full tree).
3. **Data models** (entities, fields, relationships).
4. **Check catalogue skeleton** (IDs and names; see Section 7).
5. **Scoring rubric draft** (see Section 8).
6. **API and CLI design.**
7. **Dependency list** with a one-line justification each, and license for each.
8. **Risk register** (technical, legal, cost, accuracy) with mitigations.
9. **Test and validation strategy.**
10. **Phase timeline** with acceptance criteria per phase.
11. **Open questions for me** (keep it to the ones that truly matter).

Also create the repo skeleton: `README.md` stub, `.gitignore`, `.env.example`, `pyproject.toml`, `Makefile` (or task runner), pre-commit config (ruff, mypy), the five living documents, and an empty `NOTICE.md` (for open-source attribution).

**STOP. Wait for my approval of `plan.md`.**

---

## 3. PHASE 1 — STUDY THE LANDSCAPE → `learn.md`

> Before designing the final product, **study how existing tools work** and record what you learn. This is the "reverse engineering" phase. It is strictly about **understanding, not copying.**

### 3.1 The rules of ethical reverse engineering

**ALLOWED (do all of this):**
- Read the **source code** of open-source projects and run them locally.
- Read their documentation, changelogs, issues, and blog posts about methodology.
- Run tools on **public websites** and study their outputs, formats, and scoring.
- Observe the HTTP requests **your own run** makes (user-agents, request patterns) with a proxy or logging.
- **Black-box compare**: run commercial tools' *free tiers or free web tools* and the open-source tools on the same site; compare outputs to find accuracy gaps.
- Read official specifications and documentation (Google Search Central, schema.org, robots.txt RFC 9309, llms.txt proposal, bot documentation from OpenAI, Anthropic, Perplexity, Google, etc.).

**NOT ALLOWED (never do these):**
- Decompile, deobfuscate, or unpack proprietary software or minified proprietary frontend code.
- Bypass paywalls, licenses, logins, rate limits, or bot protection.
- Call or scrape private/undocumented APIs of commercial products.
- Copy proprietary code, text, UI, or scoring tables.
- Copy open-source code verbatim without checking its license and recording attribution in `NOTICE.md`. Default policy: **learn the idea, write original code.**

If in doubt, don't — log the doubt in `DECISIONS.md` and ask me.

### 3.2 Study targets

Verify each exists and check its **license, last-commit date, and activity** before investing time. Use GitHub search and topic pages (`generative-engine-optimization`, `ai-visibility`, `answer-engine-optimization`, `seo-audit`, `llms-txt`) to find *additional* current projects. Prioritize the best 6–10 by quality, not star count.

**Open-source GEO/AEO (read the code):**
- **GEO Optimizer** (`Auriti-Labs/geo-optimizer-skill`, MIT) — CLI/library/MCP server; AI-readiness scoring, history, regression detection, citation checks.
- **OranGEO AI Visibility Skill** (MIT) — robots/llms.txt checks, buyer-prompt generation, readiness scoring.
- **GetCito** — open-source AI visibility / AEO tracking.
- **`geo-audit`** (PyPI, stdlib-only) — minimal 20-point page audit; good for understanding the smallest viable version.
- Any open-source, self-hosted, bring-your-own-key AI visibility monitors you find on GitHub.

**Open-source technical SEO / web quality (read the code):**
- **Lighthouse** (Google) — metrics, audits, scoring curves.
- **Crawlee** and/or **Scrapy** — crawl architecture, queues, politeness, retries.
- **advertools** — SEO-focused crawling/analysis in Python.
- **extruct** — structured data extraction (JSON-LD, microdata, RDFa).
- Any maintained open-source SEO auditor or sitemap/redirect/link-checker you find.

**Commercial tools (black-box only, free tiers/free tools/public docs):**
- Screaming Frog (free tier, 500 URLs) — study its crawl **outputs** and issue taxonomy.
- Google Search Console, PageSpeed Insights, Rich Results Test, Schema Markup Validator.
- Semrush/Ahrefs free site-audit or free webmaster tools — compare issue taxonomy and severity.
- AI-visibility SaaS products (e.g. Profound, Peec AI, and similar) — **public marketing pages, docs, and blog methodology only.**

### 3.3 Study method (for each target)

1. Clone/install it (in an isolated virtual environment). Read README, license, structure.
2. Trace the main flow: entry point → fetch → parse → checks → scoring → output.
3. List **every check it performs**, with its pass/fail logic and weighting.
4. Run it on the **same 5 benchmark sites** (see 3.4) and save outputs in `research/outputs/<tool>/`.
5. Note strengths, weaknesses, false positives, missing coverage, and performance.
6. Record **ideas to reimplement** (in your own words and code) and **mistakes to avoid**.

### 3.4 Benchmark set

Choose **5 diverse public sites** and record them in `research/benchmarks.md`: one static/simple site, one WordPress site, one JavaScript-heavy SPA, one eCommerce site, and one large content/blog site. Use only polite, rate-limited, read-only access. Reuse this same set in Phase 6 validation.

### 3.5 Required structure of `learn.md`

```
# learn.md — Research Notes

## 0. Summary (10 bullets: the most important things learned)
## 1. Landscape map (table: tool | type | license | what it checks | quality notes)
## 2. Per-tool deep dives (repeat for each tool)
   - Purpose & audience
   - License & activity
   - Architecture (flow diagram or bullet trace)
   - Complete check list (ID/name/logic/weight)
   - Scoring approach
   - Output formats
   - Strengths
   - Weaknesses / false positives / gaps
   - Ideas to reimplement (original code)
   - Things to avoid
## 3. Master check catalogue (merged, de-duplicated, with sources)
## 4. Scoring approaches compared (what's arbitrary vs. principled)
## 5. Black-box comparison results (tool outputs on the benchmark sites)
## 6. Gap analysis — what NO tool does well (our opportunity)
## 7. AI crawler & bot reference table (verified from official docs, with dates)
## 8. GEO signals: evidence vs. folklore (what is actually supported by documentation or research, and what is speculation)
## 9. Decisions this research led to (link to DECISIONS.md)
## 10. Attribution & license notes
```

Be honest in section 8: GEO is a young field. Separate **documented facts** (e.g., a bot's published user-agent) from **plausible heuristics** and **marketing folklore**. Reports must label heuristics as heuristics.

### 3.5 Update plan

After `learn.md` is complete, **revise `plan.md`** to reflect what you learned (catalogue, scoring, architecture). Log the changes in `DECISIONS.md`.

**STOP. Summarize the top findings to me and wait for approval.**

---

## 4. TECH STACK (confirm versions against official docs)

| Concern | Choice |
|---|---|
| Language | Python 3.12+ (type hints everywhere) |
| HTTP | `httpx` (async), HTTP/2, connection pooling |
| HTML parsing | `selectolax` (fast) with `lxml` fallback |
| Rendering | Playwright (Chromium) for rendered DOM, screenshots, PDF |
| Structured data | `extruct` + custom validation |
| Models | Pydantic v2 |
| API | FastAPI + Uvicorn |
| CLI | Typer + Rich |
| DB | SQLAlchemy 2 + SQLite (dev) / Postgres-ready, Alembic migrations |
| Jobs | asyncio task queue first; design the interface so RQ/Celery can replace it |
| Reports | Jinja2 templates → HTML → PDF via Playwright |
| Frontend (Phase 5) | Next.js + TypeScript + Tailwind + a charting library |
| Testing | pytest, pytest-asyncio, respx (HTTP mocking), hypothesis (property tests), coverage |
| Quality | ruff, mypy (strict on core), pre-commit |
| Packaging | `uv` or `pip` with lockfile; Dockerfile + docker-compose |
| CI | GitHub Actions (lint, type, test, build) |

If you believe a different choice is clearly better, justify it in `DECISIONS.md` and proceed.

---

## 5. ARCHITECTURE PRINCIPLES

- **Pipeline design:** `Fetch → Parse → Extract → Check → Score → Report`. Each stage has a typed input/output.
- **Checks are plugins:** every check is a small class/function with `id`, `layer`, `title`, `severity`, `run(context) → list[Finding]`. Registering a new check must require **zero changes** to the core.
- **Findings are data, not strings:** `Finding{id, layer, severity, status, evidence[], why_it_matters, fix, effort, impact, references[]}`.
- **Snapshots are immutable:** store raw HTML (compressed), headers, fetch timestamps, and rendered DOM hashes so any finding can be re-verified.
- **Everything cacheable and resumable:** crawl state persists; interrupted audits resume.
- **Provider abstraction for AI engines:** one interface (`AnswerEngine.ask(prompt, options) → Answer{text, citations[], model, timestamp, raw}`) with adapters per provider. Adding a provider = one file.
- **Config over code:** thresholds, weights, model names, bot lists, and branding live in versioned YAML/TOML.
- **Observability:** structured logs (JSON), per-audit run ID, timing per stage, API cost tracking per audit.
- **Fail soft:** one failing check or provider must never crash the audit; record it as `error` with reason.

---

## 6. MODULES — DETAILED REQUIREMENTS

### 6.1 Crawler (Phase 2)

- Async, polite: **honor robots.txt** (RFC 9309), `crawl-delay` when present, configurable concurrency/rate limit, per-host limits.
- Custom identifying User-Agent (e.g. `AuditIQBot/1.0 (+contact-url)`), configurable.
- Discovery: start URL, sitemap(s) (including sitemap index and `robots.txt` sitemap directives), internal links. Normalize and dedupe URLs (trailing slash, case, tracking params, fragments).
- Limits: max pages, max depth, max total time, max response size. Sensible defaults (e.g. 200 pages).
- Handle: redirects (record full chains), timeouts, retries with exponential backoff and jitter, gzip/brotli, non-HTML content, soft-404s, canonicalization, `noindex`/`nofollow` (meta and header), `X-Robots-Tag`.
- Two fetch modes per page: **raw** (HTTP only) and **rendered** (Playwright), the latter used selectively (sample of key pages) to control cost/time.
- Build the **internal link graph**; compute depth, inlinks, orphan pages.
- Crawl is **resumable** and emits progress events.

### 6.2 Technical SEO Layer (Phase 2)

Implement the checks listed in Section 7.1, plus: Core Web Vitals via the PageSpeed Insights API (cached, key from env, quota-aware), mobile-friendliness signals, HTTPS/mixed content, security headers (informational), compression, caching headers, and image optimization signals.

### 6.3 Content & Entity Layer (Phase 3)

Implement Section 7.2. Use deterministic methods first (readability formulas, structure analysis, schema checks). Use an LLM **only** for tasks that need it (e.g. judging whether a page opens with a direct answer), and always: cache results, record the model and prompt version, show the reasoning snippet as evidence, and label as `ai-assisted`.

### 6.4 GEO Readiness Layer (Phase 4)

Implement Section 7.3. Core ideas:
- **AI bot access matrix:** for each known AI crawler user-agent, evaluate robots.txt allow/block for the site and key paths. Maintain the bot list in `config/ai_bots.yaml` with `source_url` and `verified_on` fields, **verified from each vendor's official documentation**. Distinguish **training crawlers**, **search/index crawlers**, and **user-triggered fetchers**, because blocking policies differ in meaning.
- **`llms.txt` check:** existence, format validity, usefulness. Treat it as an emerging, optional convention; do **not** over-weight it.
- **Render-vs-raw diff:** compare main-content text between raw HTML and rendered DOM. Report the percentage of meaningful content missing without JavaScript.
- **Chunkability & quotability:** headings hierarchy, passage length, self-contained definitions, lists/tables, explicit facts with sources, freshness signals.
- **Entity clarity:** consistent brand name, `Organization` schema, `sameAs` links, About/Contact/author pages, third-party presence signals (Wikipedia/Wikidata, LinkedIn, GitHub, review sites) — detected only from the site's own links and public data, never by scraping restricted sources.

### 6.5 Live AI Visibility Testing (Phase 4)

This is the signature feature. Build it rigorously.

**Prompt generation**
- From the site's content, niche, and location, generate **20–30 buyer-intent prompts** across categories: *discovery* ("best X for Y"), *comparison* ("A vs B"), *problem-solution*, *how-to*, *local* (if relevant), *brand* ("what is <brand>", "is <brand> good"), and *competitor* prompts.
- Prompts are **stored, editable, versioned**, and the user can add or remove them before running.

**Execution**
- Providers via the `AnswerEngine` interface, **BYOK** (keys from env). Prefer modes that return **real source citations** (web-search-enabled APIs). Clearly separate:
  - **Retrieval-based answers** (real citations; measures citation visibility), and
  - **Parametric answers** (model memory; measures brand awareness only).
  Never mix these in a single metric.
- Run each prompt **N times** (default 3–5) per provider to measure variance. Respect provider rate limits, with budget caps and a **cost estimator that shows the projected cost before running**.
- Store every raw answer as an immutable **snapshot** (provider, model, date, prompt, answer, citations).

**Metrics**
- **Mention rate:** % of runs where the brand is named (with a robust, tested matcher handling variants and aliases).
- **Citation rate:** % of runs where the brand's domain appears among cited sources.
- **Share of voice:** brand mentions vs. each competitor across the prompt set.
- **Position/prominence** where determinable.
- **Sentiment/framing** of brand mentions (LLM-assisted, labelled as such, with an evidence quote — keep quotes short).
- **Top cited domains** per topic (shows who AI engines trust in the niche).
- **Confidence intervals** (Wilson interval) on rates; show "n runs" next to every number. Flag low-sample results.

**Honesty requirements**
- Every visibility number shows provider, model, date, and run count.
- State clearly that AI answers vary by time, location, and user context.
- If no API keys are configured, the layer is `Not measured`, and the score redistributes (see Section 8) — never fabricated.

### 6.6 Scoring Engine (Phase 5)

See Section 8. Scores must be reproducible from stored findings, versioned (`scoring_version`), and explainable (each score links to the findings that moved it).

### 6.7 Reporting (Phase 5)

**Report sections:** cover; executive summary (plain language, max one page); score overview with layer breakdowns; top 10 prioritized actions (impact × effort matrix); GEO visibility results with charts and confidence ranges; detailed findings by layer, each with evidence and fix; methodology & limitations (honest); appendix (crawl stats, raw evidence, snapshot references).

**White-label config** (`branding.yaml`): agency name, logo, primary/secondary colors, fonts, footer text, contact info, optional "prepared for <client>" fields. **No hardcoded product branding in templates.**

Formats: HTML (self-contained), PDF, JSON (full machine-readable), CSV (findings). Print-quality design, accessible contrast, readable charts.

### 6.8 CLI (Phase 2 onward, grows each phase)

```
auditiq crawl <url> [--max-pages N] [--depth N]
auditiq audit <url> [--competitors a,b,c] [--brand "Name"] [--layers tech,content,geo,live] [--out dir]
auditiq prompts generate|list|edit <audit-id>
auditiq visibility run <audit-id> [--providers ...] [--runs N] [--budget USD]
auditiq report <audit-id> --format html|pdf|json|csv [--branding branding.yaml]
auditiq history <url>
auditiq compare <audit-id-a> <audit-id-b>
auditiq doctor            # checks env, keys, Playwright, config validity
```

### 6.9 API & Dashboard (Phase 5–6)

REST API: create audit, stream progress (SSE/WebSocket), fetch findings/scores/report, list history, compare audits, manage branding and prompt sets. OpenAPI docs auto-generated. Dashboard (Next.js): start an audit, live progress, score cards, findings explorer (filter by layer/severity/effort), visibility charts, history trends, report download. Clean, fast, accessible, mobile-friendly.

---

## 7. CHECK CATALOGUE (starting set — extend from `learn.md`)

Each check: `ID`, title, severity (critical/high/medium/low/info), evidence, fix, effort (S/M/L), and impact rationale.

### 7.1 Technical SEO (`TECH-*`)

- **Crawlability & indexing:** robots.txt presence/validity and accidental blocking of key paths; sitemap presence, validity, and coverage vs. crawl; `noindex` on important pages; `X-Robots-Tag`; canonical presence, self-reference, conflicts, and chains; redirect chains/loops; 4xx/5xx pages; soft-404s; orphan pages; crawl depth > 4; HTTP→HTTPS consistency; www/non-www consistency; mixed content.
- **On-page:** title missing/duplicate/too long or short; meta description missing/duplicate/length; H1 missing/multiple/duplicate; heading hierarchy skips; thin content; duplicate and near-duplicate content (simhash); image alt missing; broken internal/external links; excessive redirected internal links; anchor-text quality; URL hygiene (parameters, length, case).
- **International:** hreflang validity, reciprocity, language/region codes.
- **Structured data:** JSON-LD parse errors; invalid/missing required properties for detected types; type coverage by page template (Product, Article, FAQPage, BreadcrumbList, Organization, LocalBusiness, etc.).
- **Performance & UX:** LCP/INP/CLS from PageSpeed Insights (field data if available, lab otherwise — **label which**); render-blocking resources; image size/format; compression; caching headers; viewport meta; tap-target/readability basics.
- **Security hygiene (info):** HTTPS validity, HSTS, basic security headers.

### 7.2 Content & Entity (`CONT-*`)

- Answer-first structure (direct answer near the top of informational pages).
- Heading structure maps to real questions users ask; question-style headings; FAQ/HowTo content present and marked up where appropriate.
- Readability (Flesch-Kincaid or equivalent) vs. audience; paragraph and sentence length distribution.
- Evidence density: statistics, named sources, dates, outbound citations to authoritative sources.
- Authorship and trust signals: visible author, bio, credentials, About, Contact, policies, reviews/testimonials where applicable.
- Freshness: visible and structured published/modified dates; stale content flags.
- Topical coverage: internal linking between related pages; thin or cannibalizing pages.
- Brand/entity consistency: name, address, phone, descriptions across pages and schema.

### 7.3 GEO Readiness (`GEO-*`)

- AI crawler access matrix (training vs. search vs. user-fetcher), with plain-language explanation of what each policy means for the business.
- `llms.txt` / `llms-full.txt` presence and validity (low weight, labelled emerging).
- Server-side rendered content coverage (render-vs-raw diff) per template type.
- Content extractability: main-content detection works, semantic HTML (`main`, `article`, headings, lists, tables), no content trapped in images, iframes, or JS-only widgets.
- Passage quality: self-contained, quotable passages with explicit facts; definitions; comparison tables; step lists.
- Schema coverage supporting entity understanding (Organization, Person, Product, Article, FAQPage, `sameAs`).
- Bot-blocking by firewall/CDN: detect 403/429/challenge pages when fetching with AI bot user-agents (use the declared user-agent string only; **do not spoof IP ranges or bypass protections**; report as "possible block").
- Third-party presence signals (from the site's own outbound links and public data).
- Performance for bots: TTFB and page weight (bots time out).

### 7.4 Live Visibility (`LIVE-*`)

Mention rate, citation rate, share of voice, competitor gap, top cited domains, sentiment/framing, prompt-category performance, provider comparison, trend vs. previous audit.

---

## 8. SCORING RUBRIC

- **Layer scores (0–100):** Technical SEO, Content & Entity, GEO Readiness, Live Visibility.
- **Default weights:** Technical 25%, Content & Entity 20%, GEO Readiness 25%, Live Visibility 30%.
- If a layer is `Not measured` (e.g., no API keys), **redistribute weights proportionally** and show this explicitly in the report ("Overall score based on 3 of 4 layers").
- **Within a layer:** each check has a weight and a score in [0,1] (pass/partial/fail, graded by severity and by *share of pages affected*, not just presence). Penalties are capped per check so one repeated issue can't zero out a layer.
- **Severity multipliers** (critical > high > medium > low > info) live in config.
- **Grades:** map scores to A–F bands defined in config.
- Every score exposes **"what moved it"**: top contributors, positive and negative.
- Scoring is **versioned** (`scoring_version`) so history comparisons stay valid; a changed rubric triggers a visible notice in comparisons.
- Document the full rubric and rationale in `docs/scoring.md`. Where a weight is a judgment call rather than evidence-based, **say so**.

**Impact × effort prioritization:** compute `priority = impact × confidence ÷ effort`, group into "Quick wins", "Major projects", "Fill-ins", "Deprioritize". Top 10 actions go into the executive summary.

---

## 9. PHASES, GATES & ACCEPTANCE CRITERIA

| Phase | Deliverable | Gate (must be true before I approve) |
|---|---|---|
| **0** | `plan.md`, repo skeleton | Plan is coherent, risks covered, I approved |
| **1** | `learn.md`, `research/` outputs, updated `plan.md` | ≥6 tools studied; check catalogue merged; gap analysis written; legal/ethics rules followed |
| **2** | Crawler + Technical SEO layer + CLI (`crawl`, `audit --layers tech`) + JSON output | Runs on all 5 benchmark sites; tests pass; results match Lighthouse/Screaming Frog within documented tolerance |
| **3** | Content & Entity layer | Deterministic checks tested; any AI-assisted check cached, labelled, and evidenced |
| **4** | GEO readiness + Live AI visibility | Bot matrix verified against official docs; render-vs-raw works; live tests run with ≥2 providers, n-run variance and confidence intervals shown; cost estimator works |
| **5** | Scoring engine, reports (HTML/PDF/JSON/CSV), white-label branding, history/compare | Scores reproducible from findings; PDF looks professional; branding swap needs zero code changes |
| **6** | API, dashboard, Docker, CI, validation, docs, demo kit | Full validation report; ≥80% coverage on core; CI green; README + demo materials complete |

At the end of each phase: run the full test suite and linters; update `PROGRESS.md`, `DECISIONS.md`, `docs/LEARNING-NOTES.md`; give me a **plain summary**: what works, what's limited, what you're unsure about, and how to run it. Then **STOP and wait.**

---

## 10. TESTING & VALIDATION (how we prove it actually works)

1. **Unit tests** for every check, with passing and failing fixtures.
2. **Recorded-fixture crawler tests** (no live network in CI): use local test sites/servers that reproduce known issues (redirect loops, broken canonicals, missing alt text, JS-only content, robots blocks).
3. **Property-based tests** (hypothesis) for URL normalization, robots parsing, and score calculation invariants (scores always within 0–100, monotonic: fixing an issue never lowers a score).
4. **Golden-file tests** for scoring and report output, so unintended drift is caught.
5. **Statistical tests** for visibility metrics: verify Wilson interval math against known values.
6. **Validation script** `scripts/validate.py`: run AuditIQ on the 5+ benchmark sites and compare against Lighthouse (performance/SEO audits), Screaming Frog free tier (crawl issues), and `learn.md` tool outputs. Write results to `docs/validation.md` with **known discrepancies and explanations.** Accuracy claims in README must come from this file.
7. **Manual spot checks:** for 20 random findings, verify by hand that evidence is correct. Record the false-positive rate.
8. **Performance targets:** 100-page crawl + technical checks in a sensible time on a normal laptop; memory bounded; report generation under 30 seconds.
9. **Resilience tests:** timeouts, malformed HTML, huge pages, invalid robots.txt, provider outages, API rate limiting, invalid keys.

---

## 11. SECURITY, ETHICS, LEGAL

- **Secrets:** only via env/`.env` (never committed); `.env.example` documents every variable; redact keys in logs and reports.
- **SSRF protection:** when the API accepts URLs, block private/internal IP ranges, `localhost`, cloud metadata endpoints, and non-HTTP(S) schemes; re-validate after redirects.
- **Politeness:** respect robots.txt and rate limits by default; an explicit, logged `--ignore-robots` flag is allowed **only for sites the user owns**, with a warning.
- **No bypassing** of bot protection, logins, paywalls, or rate limits. No spoofing of other vendors' bots' IP ranges. Using a bot's *declared user-agent string* for robots.txt rule evaluation is fine; using it to impersonate that bot while fetching is not — fetch with AuditIQ's own user-agent unless the user explicitly opts in on their **own** site.
- **Client data:** audits store only public data. Never log full API responses containing keys. Provide a `purge` command to delete an audit and its snapshots.
- **Cost safety:** hard budget caps for paid AI APIs with a pre-run estimate and user confirmation.
- **Dependencies:** pin versions, run `pip-audit` (or equivalent) in CI, record licenses in `NOTICE.md`.
- **Honest claims:** the report must not promise rankings or AI citations. It reports measured readiness and observed visibility, with limitations stated.
- **Privacy:** don't send page content to third-party LLMs unless the user has enabled AI-assisted checks, and say exactly what is sent.

---

## 12. DOCUMENTATION & DEMO KIT (Phase 6)

- `README.md`: what it is, screenshots, quickstart (under 5 minutes), architecture diagram, usage examples, configuration reference, limitations, roadmap, license, contributing guide.
- `docs/`: `architecture.md`, `scoring.md`, `checks.md` (auto-generated from the registry), `validation.md`, `ai-visibility-methodology.md`, `adding-a-check.md`, `adding-a-provider.md`, `LEARNING-NOTES.md`.
- **Demo kit for me:**
  - `demo/sample-report.pdf` (generated from a benchmark site, branded as a neutral sample agency),
  - a **3-minute demo script** (talking points, what to click, what number to highlight),
  - a **one-page case study** template (problem → approach → result → measured time saved vs. manual audit),
  - a **"how to explain this project" cheat sheet**: likely questions an agency lead would ask (accuracy, data privacy, costs, limitations, how it differs from Semrush/Screaming Frog) with honest answers,
  - a **resume/LinkedIn bullet pack** and a **GitHub README banner/screenshots** checklist.
- Measure and document the **manual-vs-tool time comparison** (time a manual audit of a 50-page site vs. the tool). This number matters for my pitch.

---

## 13. CODE QUALITY STANDARDS

- Type hints everywhere; `mypy --strict` on core modules.
- Small functions, clear names, docstrings explaining *why*, not just *what*.
- No global mutable state; dependency injection for HTTP clients, clocks, and providers (testability).
- Errors are typed and carry context; no bare `except`.
- Logging is structured; no `print` in library code.
- Reasonable abstraction: don't over-engineer, but keep the plugin boundaries in Section 5 clean.
- Accessibility and responsive design for the dashboard and reports.
- Every public function/class used by others is tested.

---

## 14. ANTI-PATTERNS (do NOT do these)

- Don't produce a pretty UI over fake or random data.
- Don't claim "AI-powered" for what is a simple regex; label honestly.
- Don't hardcode scores, thresholds, model names, or bot lists in code.
- Don't treat GEO folklore as fact; label heuristics.
- Don't present a single AI answer as a stable truth.
- Don't dump 400 findings with no prioritization.
- Don't copy code from other projects without license compliance and attribution.
- Don't skip tests "to save time", and don't claim tests passed without running them.
- Don't move to the next phase without my approval.
- Don't leave the repo in a broken state at any commit on `main`.

---

## 15. FINAL INSTRUCTIONS

1. Read this entire file. Confirm you understand by replying with a **short summary of the mission, the phase order, and the three rules you consider most critical.**
2. Begin **Phase 0** immediately: create `plan.md` and the repo skeleton.
3. Then **STOP** and wait for my approval.
4. Throughout, remember the goal behind everything: I want to prove genuine skill to a real agency by showing a tool that is **accurate, honest, well-built, and useful**. A smaller feature set that is correct and polished beats a huge one that is flaky. When in doubt, choose correctness, evidence, and clarity.

**Begin.**
