# Benchmark Evaluation Sites (`research/benchmarks.md`)

This benchmark suite defines five diverse public websites representing distinct architectures, tech stacks, and content scales. These sites serve as the fixed testbed for Phase 1 landscape comparisons, Phase 2–4 crawler validation, and Phase 6 final verification.

---

## 1. Static / Minimal Architecture
- **Site**: Python Developer Documentation (`https://docs.python.org/3/`)
- **Category**: Static / Sphinx HTML
- **Characteristics**: Fast TTFB, semantic headings, dense technical text, pure server-side HTML, zero client-side JavaScript required for indexing.
- **Evaluation Purpose**: Establishes upper-bound baseline for raw HTML extractability and crawl efficiency.

---

## 2. WordPress / Classic CMS Architecture
- **Site**: TechCrunch (`https://techcrunch.com`)
- **Category**: News & Media CMS
- **Characteristics**: High publication volume, author bylines, tags, categories, complex canonical structures, dynamic ad scripts, rich OpenGraph and schema.org markup.
- **Evaluation Purpose**: Evaluates author trust signals, freshness timestamps, redirect hygiene, and sitemap index parsing.

---

## 3. JavaScript-Heavy Single-Page App (SPA)
- **Site**: Vercel Blog & Showcase (`https://vercel.com/blog`)
- **Category**: Next.js / React Modern Web App
- **Characteristics**: Client-side hydration, dynamic routing, high interactivity, modern Core Web Vitals optimizations.
- **Evaluation Purpose**: Stress-tests the **Render-vs-Raw differential analyzer** to quantify how much content is lost when an AI crawler does not execute JavaScript.

---

## 4. Large eCommerce Catalog
- **Site**: Books to Scrape (`https://books.toscrape.com`)
- **Category**: Sandbox eCommerce Architecture
- **Characteristics**: Deep pagination, product catalogs, faceted navigation, breadcrumb hierarchies, price/inventory schema structures.
- **Evaluation Purpose**: Tests pagination handling, crawl depth limiting, canonicalization loops, and Product schema validation.

---

## 5. High-Authority B2B SaaS / Solution Platform
- **Site**: Cloudflare Learning Center (`https://www.cloudflare.com/learning/`)
- **Category**: Educational B2B Hub
- **Characteristics**: Answer-first technical definitions, question-based H2/H3 headings, comparison tables, high internal linking density.
- **Evaluation Purpose**: Validates chunkability, passage quality, question-answering structure, and brand entity consistency.
