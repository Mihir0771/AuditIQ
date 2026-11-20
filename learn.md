# learn.md — Landscape Study & Reverse Engineering Notes

> This living document records the reverse-engineering analysis of existing SEO, GEO, and AI visibility tools conducted during Phase 1. It focuses on ethical, black-box, and open-source analysis (understanding concepts, architectures, and algorithms without copying proprietary code).

---

## 0. Summary
*(To be populated in Phase 1 with the top 10 most critical engineering insights learned from studying benchmark tools)*

---

## 1. Landscape Map
*(To be populated in Phase 1 with a comparative taxonomy table)*

| Tool | Type | License | Primary Checks | Architecture / Stack | Quality Notes |
|---|---|---|---|---|---|
| *GEO Optimizer* | CLI / MCP | MIT | AI readiness, citation check | Python / Typer | *Pending Phase 1 deep dive* |
| *OranGEO* | Skill / CLI | MIT | Bot access, prompt generation | Python | *Pending Phase 1 deep dive* |
| *GetCito* | SaaS / OSS | Open Source | AEO visibility monitoring | Python / Node | *Pending Phase 1 deep dive* |
| *geo-audit* | PyPI Library | MIT | 20-point page audit | Python (stdlib) | *Pending Phase 1 deep dive* |
| *Lighthouse* | CLI / DevTools | Apache 2.0 | Performance, SEO, a11y | Node / Chromium | *Pending Phase 1 deep dive* |
| *Crawlee / Scrapy*| Crawler Framework| Apache 2.0 / BSD | Crawling, queues, politeness | Python / TypeScript | *Pending Phase 1 deep dive* |
| *advertools* | Library | MIT | SEO crawling, text analysis | Python | *Pending Phase 1 deep dive* |
| *extruct* | Extraction Lib | BSD-3-Clause | JSON-LD, Microdata, RDFa | Python | *Pending Phase 1 deep dive* |
| *Screaming Frog*| Desktop (Free) | Proprietary | 500-page technical audit | Java Desktop | *Pending Phase 1 black-box analysis* |

---

## 2. Per-Tool Deep Dives
*(Detailed analysis per tool following the Section 3.3 study method)*

---

## 3. Master Check Catalogue
*(Consolidated, de-duplicated check inventory with cross-tool sources)*

---

## 4. Scoring Approaches Compared
*(Analysis of scoring methodologies: arbitrary weighting vs. principled statistical curves)*

---

## 5. Black-Box Comparison Results
*(Comparative execution across the 5 benchmark sites stored in `research/benchmarks.md`)*

---

## 6. Gap Analysis — What NO Tool Does Well (Our Opportunity)
*(Uncovered industry shortcomings: lack of statistical honesty, ignoring non-JS AI crawler realities, poor white-label reporting)*

---

## 7. AI Crawler & Bot Reference Table
*(Verified user-agent strings, bot types, and vendor documentation dates)*

---

## 8. GEO Signals: Evidence vs. Folklore
*(Rigorous differentiation between documented vendor requirements and unsubstantiated SEO marketing claims)*

---

## 9. Decisions This Research Led To
*(Direct links to ADRs in `DECISIONS.md`)*

---

## 10. Attribution & License Notes
*(Cross-references to `NOTICE.md` ensuring ethical compliance)*
