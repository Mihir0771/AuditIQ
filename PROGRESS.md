# PROGRESS.md — AuditIQ Living Roadmap & Status Tracker

This document tracks overall progress, phase milestones, blockers, and known issues. It is updated at the conclusion of every phase.

---

## Current Status: Phase 0 (Planning & Repository Setup)

- **Overall Health**: 🟢 On Track
- **Current Phase**: Phase 0 (Planning)
- **Blocked Items**: None

---

## Phase Checklist

### [x] Phase 0: Planning & Repository Setup
- [x] Master prompt review & core rules verification
- [x] Git repository initialization on `main` branch
- [x] Repository skeleton: `.gitignore`, `.env.example`, `pyproject.toml`, `Makefile`, `tasks.ps1`, `.pre-commit-config.yaml`
- [x] Five living documents established: `plan.md`, `learn.md`, `DECISIONS.md`, `PROGRESS.md`, `docs/LEARNING-NOTES.md`
- [x] Open source compliance document: `NOTICE.md`
- [x] Architecture specification drafted in `plan.md`
- [ ] **GATE**: User review and approval of `plan.md`

---

### [ ] Phase 1: Landscape Study & Reverse Engineering (`learn.md`)
- [ ] Select and study ≥6 open-source and reference tools (GEO Optimizer, OranGEO, geo-audit, Lighthouse, Crawlee, extruct, Screaming Frog output)
- [ ] Define 5 diverse benchmark sites in `research/benchmarks.md`
- [ ] Execute tools against benchmarks and record outputs in `research/outputs/`
- [ ] Synthesize findings in `learn.md` (gap analysis, check catalogue expansion, bot taxonomy)
- [ ] Revise `plan.md` based on real-world findings
- [ ] **GATE**: User review and approval of `learn.md` and updated `plan.md`

---

### [ ] Phase 2: Core Crawler & Technical SEO Engine
- [ ] Asynchronous polite crawler (`httpx`, RFC 9309 robots.txt parser, sitemap parser, link graph)
- [ ] Selective Playwright rendering engine (Rendered DOM & screenshot capture)
- [ ] Pluggable check runner framework (`BaseCheck`, `Finding`, `CheckRegistry`)
- [ ] Implement Technical SEO check suite (`TECH-*`)
- [ ] CLI commands: `auditiq crawl`, `auditiq audit --layers tech`
- [ ] Unit & fixture-based integration tests
- [ ] **GATE**: Validation on 5 benchmark sites matching industry standards

---

### [ ] Phase 3: Content & Entity Analysis Engine
- [ ] Content extractability and readability algorithms (Flesch-Kincaid, text statistics)
- [ ] Heading hierarchy and question-answering structure checks
- [ ] Entity and structured data validator (JSON-LD, Microdata, schema.org)
- [ ] AI-assisted content evaluation (cached, prompt-versioned, evidence-backed)
- [ ] Implement Content & Entity check suite (`CONT-*`)
- [ ] CLI command: `auditiq audit --layers tech,content`
- [ ] **GATE**: Full test suite green and verification of deterministic vs AI-assisted checks

---

### [ ] Phase 4: GEO Readiness & Live AI Visibility Engine
- [ ] AI bot permission matrix parser (`config/ai_bots.yaml` verified against vendor docs)
- [ ] Render-vs-Raw differential analyzer (content loss detection)
- [ ] `llms.txt` and semantic chunkability checks (`GEO-*`)
- [ ] Buyer-intent prompt generator (20–30 contextual queries)
- [ ] Multi-engine `AnswerEngine` abstraction (OpenAI, Anthropic, Gemini, Perplexity)
- [ ] Repeated prompt execution with Wilson Score interval calculation & variance tracking
- [ ] Pre-run cost estimator and budget cap enforcement
- [ ] CLI commands: `auditiq prompts`, `auditiq visibility run`
- [ ] **GATE**: Live visibility tests verified across ≥2 providers with confidence intervals

---

### [ ] Phase 5: Scoring Rubric, Reporting & White-Label Delivery
- [ ] Composite and layer scoring engine (reproducible, explainable, proportional redistribution)
- [ ] Impact × Effort prioritization matrix calculation
- [ ] Jinja2 HTML report generator (responsive, accessible, clean design)
- [ ] Playwright headless PDF generator (print-ready styling)
- [ ] White-label configuration system (`config/branding.yaml`)
- [ ] Historical audit storage and regression comparison engine (`auditiq compare`)
- [ ] Export formats: HTML, PDF, JSON, CSV
- [ ] **GATE**: Audit reports verified for white-label styling and reproducible scores

---

### [ ] Phase 6: REST API, Dashboard, Docker & Benchmark Validation
- [ ] FastAPI backend with asynchronous audit jobs and SSE progress streaming
- [ ] Next.js dashboard for interactive audit inspection and report downloads
- [ ] Dockerfile and Docker Compose deployment configuration
- [ ] Comprehensive validation suite (`scripts/validate.py`) comparing benchmark results
- [ ] Documentation suite (`docs/architecture.md`, `docs/scoring.md`, `docs/validation.md`)
- [ ] Agency Demo Kit: sample report PDF, 3-minute pitch script, case study, and objection cheat sheet
- [ ] **GATE**: CI green, test coverage ≥80% on core, validation report completed

---

## Known Issues & Technical Debt
*None at Phase 0.*
