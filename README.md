# AuditIQ — Production-Grade AI SEO & GEO Audit Engine

[![Status](https://img.shields.io/badge/Status-Phase%200%20(Planning)-blue.svg)]()
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()

> **AuditIQ** is an enterprise-grade dual audit engine designed for digital marketing agencies, SEO teams, and AI consultants. It evaluates websites across traditional search engine visibility (**Technical SEO & Content**) and generative search engine visibility (**GEO / AEO** across ChatGPT, Perplexity, Gemini, Claude, and Google AI Overviews).

---

## 🌟 Key Differentiators

1. **Statistical Honesty in Live AI Visibility**: Repeated runs with Wilson confidence intervals and variance measurement — no single-run noisy snapshots.
2. **Render-vs-Raw DOM Analysis**: Direct comparison between raw HTTP server output and fully rendered DOM to expose content invisible to non-JS AI crawlers.
3. **Evidence-First Findings**: Every issue is backed by a specific URL, code snippet/HTTP header, and remediation instruction.
4. **Impact × Effort Prioritization**: Algorithmic scoring that produces a focused, actionable action plan rather than an unmanageable issue dump.
5. **White-Label Agency Architecture**: Fully configurable branding (agency logo, colors, fonts, client metadata) driven by configuration.
6. **Regression & Historical Tracking**: Automated delta comparisons across audits to detect score drops and newly introduced issues.
7. **Transparent, Explainable Rubric**: Open mathematical formula detailing every factor influencing composite and layer scores.

---

## 🏗️ Architecture Overview

AuditIQ follows an asynchronous pipeline architecture:

```
[Target URL / Sitemaps]
         │
         ▼
┌──────────────────┐
│  Polite Crawler  │ ──► [RFC 9309 Robots / Graph Builder / Raw Fetch]
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Selective Render │ ──► [Playwright DOM / Screenshot / Rendered Diff]
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Check Engine   │ ──► [Pluggable Checks: TECH / CONT / GEO / LIVE]
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Scoring Engine  │ ──► [Proportional Weights / Severity / Deductions]
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Report Generator │ ──► [White-Label HTML / PDF / JSON / CSV]
└──────────────────┘
```

---

## 📋 Audit Layers

| Layer | Code Prefix | Focus Areas |
|---|---|---|
| **Technical SEO** | `TECH-*` | Crawlability, robots.txt, sitemaps, canonicals, redirect chains, Core Web Vitals, structured data. |
| **Content & Entity** | `CONT-*` | Answer-first layout, heading hierarchies, readability, entity schemas (`Organization`, `sameAs`), freshness. |
| **GEO Readiness** | `GEO-*` | AI bot permissions matrix, render-vs-raw diff, semantic extractability, chunkability, `llms.txt`. |
| **Live AI Visibility** | `LIVE-*` | Multi-engine prompt runs, brand mention rate, citation rate, share of voice, top cited competitors. |

---

## 🚀 Quickstart (Coming in Phase 2)

```bash
# Clone the repository
git clone https://github.com/your-org/auditiq.git
cd auditiq

# Install dependencies
make dev
# or on Windows:
.\tasks.ps1 dev

# Run system doctor
auditiq doctor

# Run an audit
auditiq audit https://example.com --brand "ExampleCorp"
```

---

## 📈 Project Status

- [x] **Phase 0: Architecture & Foundation** (Current)
- [ ] **Phase 1: Landscape Study & Reverse Engineering (`learn.md`)**
- [ ] **Phase 2: Core Crawler & Technical SEO Engine**
- [ ] **Phase 3: Content & Entity Analysis Engine**
- [ ] **Phase 4: GEO Readiness & Live AI Visibility Engine**
- [ ] **Phase 5: Scoring Rubric, Reporting & White-Label Delivery**
- [ ] **Phase 6: REST API, Dashboard, Docker & Benchmark Validation**

---

## 📄 Living Documentation

- [`plan.md`](plan.md): Comprehensive system architecture and implementation blueprint.
- [`learn.md`](learn.md): Landscape study, tool teardowns, and reverse engineering notes.
- [`DECISIONS.md`](DECISIONS.md): Architectural Decision Records (ADRs).
- [`PROGRESS.md`](PROGRESS.md): Live phase progress and milestone status.
- [`docs/LEARNING-NOTES.md`](docs/LEARNING-NOTES.md): Concepts explained for AI & Data Science foundations.
- [`NOTICE.md`](NOTICE.md): Attribution and open-source compliance ledger.
