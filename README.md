# AuditIQ — Production-Grade AI SEO & Generative Engine (GEO) Audit Platform

[![Build & Tests](https://img.shields.io/badge/tests-53%20passed-30D158.svg)]()
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-0A84FF.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688.svg)]()
[![Playwright](https://img.shields.io/badge/Playwright-Chromium%20Ready-2EAD33.svg)]()
[![Type Checking](https://img.shields.io/badge/mypy-strict%20clean-blueviolet.svg)]()
[![Code Style](https://img.shields.io/badge/code%20style-ruff-black.svg)]()
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)]()

> **AuditIQ** is an enterprise-ready dual audit engine engineered for digital growth agencies, technical SEO architects, and AI consultants. It evaluates websites simultaneously across traditional search (**Technical SEO & Content**) and generative answer engine visibility (**Generative Engine Optimization / GEO** across ChatGPT, Perplexity, Claude, Gemini, and Google AI Overviews).

---

## 🌟 Key Capabilities

1. **Dual-Engine Search Intelligence**: Evaluates foundational web health for traditional search engines while checking LLM retrieval, passage chunking, and AI crawler access.
2. **Apple Spatial Liquid Glass Dashboard**: High-performance, zero-CDN local web dashboard SPA featuring real-time Server-Sent Events (SSE) crawl streaming, animated SVG liquid gauges, and interactive findings filtering.
3. **Statistical Rigor with Wilson Score Intervals**: Employs asymmetric 95% Wilson Score Confidence Intervals ($z=1.96, n \ge 10$) with disclosed sample sizes for all live AI citation and mention metrics.
4. **Render-vs-Raw DOM Diffing**: Directly compares raw HTTP responses against headless Chromium rendered DOM to expose client-side JavaScript content evaporation.
5. **AI Bot Triad Taxonomy**: Distinguishes between *Training Crawlers* (`GPTBot`, `ClaudeBot`), *Search Indexers* (`OAI-SearchBot`, `PerplexityBot`), and *User-Triggered Fetchers* (`ChatGPT-User`) to eliminate false-positive warnings.
6. **64-Bit Simhash LSH Cannibalization**: Rapid Hamming distance evaluation detecting near-duplicate pages without heavy vector embedding latency.
7. **White-Label Agency Delivery**: Generates standalone HTML reports, print-ready headless Chromium PDFs with dynamic page numbering, CSV spreadsheets, and complete JSON records.
8. **Automated CI/CD Regression Gate**: Headless audit comparison engine (`auditiq compare`) detecting score drops and newly introduced issues between releases.

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────┐
│               Polite Async Crawler Loop                │
│  (httpx HTTP/2 + RFC 9309 Robots + Recursive Sitemaps) │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               Selective Headless Renderer              │
│       (Playwright Chromium / Raw-vs-Rendered Diff)     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│        Pluggable Check Registry (55 Checks)            │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ │
│  │ Technical SEO │ │ Content/Entity│ │ GEO Readiness │ │
│  │  (27 Checks)  │ │  (13 Checks)  │ │  (11 Checks)  │ │
│  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘ │
│          └─────────────────┼─────────────────┘         │
│                            ▼                           │
│              Live AI Visibility Engine (BYOK)          │
│         (OpenAI, Anthropic, Gemini, Perplexity, Mock)  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│          Scoring & Prioritization Engine               │
│  (Proportional Weight Redistribution + Eisenhower Quad) │
└──────────────────────────┬─────────────────────────────┘
                           │
         ┌─────────────────┴─────────────────┐
         ▼                                   ▼
┌───────────────────────┐         ┌───────────────────────┐
│ White-Label Exporters │         │ FastAPI & Web SPA UI  │
│ (HTML, PDF, JSON, CSV)│         │ (Apple Liquid Glass)  │
└───────────────────────┘         └───────────────────────┘
```

---

## 📋 The 4 Audit Layers & 55 Automated Checks

| Layer | Checks | Key Verifications |
| :--- | :--- | :--- |
| **1. Technical SEO** | 27 Checks | RFC 9309 robots.txt, XML sitemaps, status code integrity, canonical loops, `<title>` & meta tags, heading hierarchies, Schema.org syntax, TTFB latency, Core Web Vitals lab metrics. |
| **2. Content & Entity** | 13 Checks | Deterministic Flesch Reading Ease, paragraph length hygiene, thin content detection, answer-first inverted pyramid layout, question-form subheadings, factual evidence density, author E-E-A-T bylines, 64-bit Simhash near-duplicate cannibalization. |
| **3. GEO Readiness** | 11 Checks | 3-tier AI bot permissions matrix, render-vs-raw text & link evaporation diff, semantic HTML extractability ratio, RAG passage chunking density, `/llms.txt` and `/llms-full.txt` validation, entity disambiguation via `sameAs` Wikidata/LinkedIn. |
| **4. Live AI Visibility** | 4 Checks | Multi-engine prompt trials across 5 buyer archetypes, Brand Mention Rate (with 95% Wilson CI), Domain Citation Rate, Competitive Share of Voice, Top Cited Domains. |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+ (tested through Python 3.14)
- Playwright Chromium (`playwright install chromium`)

### Installation
```bash
# Clone the repository
git clone https://github.com/Mihir0771/AuditIQ.git
cd AuditIQ

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install package with development dependencies
pip install -e .
playwright install chromium
```

---

## 💻 CLI Commands

### 1. System Diagnostics (Doctor)
Verifies Python environment, 55 registered checks, configuration files, and Playwright Chromium headless availability:
```bash
python -m auditiq.cli doctor
```

### 2. Run a Full Dual-Engine Audit
Crawl a target website, execute all checks, calculate scores, and generate reports:
```bash
python -m auditiq.cli audit https://mihir.runs-on.dev --brand "Mihir" --layers tech,content,geo,live --mock-ai --max-pages 25 --out reports/
```

### 3. Launch the Interactive Web Dashboard & REST Server
Start the local FastAPI server with real-time SSE progress streaming and the Apple Liquid Glass web interface:
```bash
python -m auditiq.cli serve --host 127.0.0.1 --port 8000
```
Open **`http://127.0.0.1:8000/`** in your browser.

### 4. Standalone Polite Crawl
```bash
python -m auditiq.cli crawl https://example.com --max-pages 50 --concurrency 5
```

### 5. Generate White-Label Reports
Export HTML, print-ready PDF, JSON record, and CSV findings from any existing audit:
```bash
python -m auditiq.cli report reports/audit_8d25ad6f81.json --format html,pdf,json,csv --out reports/
```

### 6. Compare Two Audits for Regressions
Compare a baseline audit against a newer run to detect score deltas and resolved/regressed findings:
```bash
python -m auditiq.cli compare reports/record_baseline.json reports/record_current.json
```

---

## 🐳 Docker Deployment

Run the complete AuditIQ engine with Playwright Chromium inside a container:

```bash
# Build and run with docker compose
docker compose up --build

# Access the dashboard at http://localhost:8000/
```

---

## 📁 Repository Structure

```
auditiq/
├── config/
│   ├── ai_bots.yaml          # 3-tier AI bot taxonomy (training, search, user)
│   ├── branding.yaml         # White-label agency customization
│   └── scoring.yaml          # Deterministic layer weights and deductions
├── demo/
│   ├── demo-script.md        # 3-minute agency pitch script with talk tracks
│   ├── case-study-template.md# Remediation case study (Synthex Analytics: 14% to 68% AI citation)
│   ├── objection-cheat-sheet.md # Top 10 client & CTO objection responses
│   ├── sample-report.html    # Standalone white-label HTML client report
│   └── sample-report.pdf     # Print-ready executive PDF report
├── docs/
│   ├── architecture.md       # Full system architecture and component topology
│   ├── scoring.md            # Mathematical formulation and proportional redistribution
│   ├── checks.md             # Complete catalogue of all 55 checks
│   ├── ai-visibility-methodology.md # Wilson score intervals and query archetypes
│   ├── validation.md         # Empirical validation across 5 benchmark testbeds
│   └── LEARNING-NOTES.md     # 16 in-depth plain-English technical foundation notes
├── src/auditiq/
│   ├── checks/               # Pluggable check implementations (tech, content, geo, live)
│   ├── crawler/              # Async crawler, robots, sitemap, link graph, Playwright renderer
│   ├── models/               # Pydantic v2 strict data contracts
│   ├── reports/              # HTML, PDF, JSON, and CSV white-label report generators
│   ├── scoring/              # Scoring engine and regression comparison
│   ├── server/               # FastAPI REST API, SSE streaming, and static SPA
│   ├── visibility/           # Live AI AnswerEngine runner, prompt generator, Wilson math
│   └── cli.py                # Typer & Rich interactive command-line interface
└── tests/                    # 53 unit and integration tests (100% green)
```

---

## 🔒 Security & Privacy

- **SSRF Protection**: Strict IP filtering in `crawler/ssrf.py` blocking loopback, RFC 1918 private ranges, link-local, and AWS/GCP/Azure cloud metadata endpoints (`169.254.169.254`).
- **Zero External CDNs**: Web dashboard SPA runs self-contained with no third-party tracking, external stylesheets, or external scripts.
- **RFC 9309 Compliance**: Honors `robots.txt` directives, crawl delays, and sitemap protocols by default.
- **BYOK Architecture**: Commercial LLM API keys remain in your local environment and are never transmitted to external services.

---

## 📄 License & Attribution

AuditIQ is licensed under the MIT License. See [NOTICE.md](NOTICE.md) for open-source dependency licenses and attributions.
