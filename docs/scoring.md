# AuditIQ Mathematical Scoring & Remediation Rubric (v2026.1)

This specification details the mathematical formulas, deduction curves, dynamic proportional weight redistribution, and action prioritization algorithms used in AuditIQ.

---

## 1. Core Principles

1. **Zero Hardcoded / Arbitrary Scores**: Scores are calculated strictly from empirical crawl findings, DOM analysis, and answer engine evaluation trials.
2. **Asymmetric Impact**: A single critical vulnerability (e.g. blocking AI search bots in `robots.txt` or a site-wide 403 firewall block) incurs severe penalization, while informational notes never deduct points.
3. **Proportional Scope Penalties**: Issues affecting 100% of pages are penalized significantly more heavily than isolated single-page anomalies.
4. **Proportional Weight Redistribution**: When optional or credential-dependent layers (such as Live AI Visibility without API keys) are unmeasured, their weight is automatically and proportionally redistributed across the remaining active layers.

---

## 2. Layer Taxonomy & Base Weights

AuditIQ measures four distinct dimensions of web visibility:

| Layer | System Code | Base Weight | Core Focus |
| :--- | :--- | :---: | :--- |
| **Technical SEO** | `technical` | **25%** | Crawlability, indexability, canonicals, robots.txt, sitemaps, status codes, latency. |
| **Content Quality** | `content` | **20%** | Flesch reading ease, thin content, answer-first inverted pyramid, E-E-A-T, Simhash cannibalization. |
| **GEO Readiness** | `geo_readiness` | **25%** | AI bot permission matrix, SSR vs CSR render differential, semantic HTML landmarks, `/llms.txt`. |
| **Live AI Visibility**| `live_visibility`| **30%** | Empirical brand mention & citation rates in ChatGPT, Perplexity, Gemini, Claude (Wilson intervals). |

$$\sum \text{Base Weights} = 0.25 + 0.20 + 0.25 + 0.30 = 1.00 \quad (100\%)$$

---

## 3. Layer Deduction Formula

Within each layer, every registered check $i$ evaluates site-wide or page-level snapshots:

### Step 1: Severity Weights ($w_i$)
Each check carries an inherent severity weight based on its potential to harm indexing or visibility:

| Finding Severity | Weight ($w_i$) | Deduction Factor ($D_i$) |
| :--- | :---: | :---: |
| **CRITICAL** | **1.00** | 1.0 (Full penalty) |
| **HIGH** | **0.70** | 0.7 |
| **MEDIUM** | **0.40** | 0.4 |
| **LOW** | **0.15** | 0.15 |
| **INFO** | **0.00** | 0.0 (No deduction) |

### Step 2: Page Ratio Multiplier ($R_i$)
For page-level checks, penalties scale with the fraction of the site affected:
$$R_i = \min\left(1.0, \frac{\text{Affected Pages}}{\text{Total Pages Crawled}}\right)$$

### Step 3: Check Score ($S_i$)
If the check has 0 failures or warnings:
$$S_i = 1.0 \quad (100\% \text{ pass})$$

If failures or warnings exist:
$$S_i = \max\left(0.0, 1.0 - (R_i \times D_i)\right)$$

### Step 4: Layer Score Calculation ($L_k$)
The raw score for layer $k$ is the weighted average of all active checks in that layer:
$$L_k = \frac{\sum_{i \in \text{Layer } k} w_i \times S_i}{\sum_{i \in \text{Layer } k} w_i} \times 100.0$$
*(If a layer has no failing or deduction-eligible checks, $L_k = 100.0$.)*

---

## 4. Proportional Weight Redistribution (ADR 0006)

When an audit is executed with a subset of layers (e.g. `--layers tech,content,geo`) or when Live AI Visibility cannot run due to missing third-party API credentials, AuditIQ **never** fabricates a mock score or penalizes the user.

Instead, the unmeasured layer's score is set to `None`, and its base weight is redistributed across active layers:

$$\text{Active Weight Sum} = \sum_{j \in \text{Active Layers}} W_j$$

For each active layer $j$:
$$W'_j = \frac{W_j}{\text{Active Weight Sum}}$$

### Example: Live Visibility Unmeasured
Suppose Live AI Visibility (base weight 30%) is unmeasured:
$$\text{Active Weight Sum} = 0.25 (\text{Tech}) + 0.20 (\text{Content}) + 0.25 (\text{GEO}) = 0.70$$

Normalized weights ($W'_j$):
- **Technical SEO**: $\frac{0.25}{0.70} \approx 35.71\%$
- **Content Quality**: $\frac{0.20}{0.70} \approx 28.57\%$
- **GEO Readiness**: $\frac{0.25}{0.70} \approx 35.71\%$
$$\sum W'_j = 35.71\% + 28.57\% + 35.71\% = 100.00\%$$

---

## 5. Composite Score & Letter Grade

The overall composite score is the weighted sum of all normalized active layer scores:
$$\text{Composite Score} = \sum_{j \in \text{Active Layers}} W'_j \times L_j$$

### Letter Grade Scale

| Score Range | Letter Grade | Executive Meaning |
| :---: | :---: | :--- |
| **90.0 – 100.0** | **A** | **Exceptional**: Prime candidate for generative citations & top search rankings. |
| **80.0 – 89.9** | **B** | **Strong**: Healthy foundation with minor optimization opportunities. |
| **70.0 – 79.9** | **C** | **Moderate**: Detectable content, rendering, or technical friction. |
| **60.0 – 69.9** | **D** | **At Risk**: Significant barriers preventing reliable AI model ingestion. |
| **< 60.0** | **F** | **Critical Failure**: Blocked bots, severe CSR loss, or broken crawlability. |

---

## 6. Action Prioritization Matrix (Impact × Effort)

Every failing finding is converted into an actionable remediation item and classified into an **Eisenhower 4-Quadrant Matrix**:

### Priority Score:
$$\text{Priority Score} = \frac{\text{Impact} \times 2.0}{\text{Effort Weight}} \times \left(1.0 + 0.5 \times \frac{\text{Affected Pages}}{\text{Total Pages}}\right)$$

Where:
- $\text{Impact} \in [1, 5]$
- $\text{Effort Weight}$: $\text{Small (S)} = 1.0$, $\text{Medium (M)} = 2.0$, $\text{Large (L)} = 3.5$

### The 4 Quadrants:

```
        HIGH IMPACT (>= 4)
             │
 ⚡ QUICK WINS│ 🏗️ MAJOR PROJECTS
 (Effort: S) │ (Effort: M or L)
─────────────┼──────────────────
 🧹 FILL-INS │ ⏳ THANKLESS TASKS
 (Effort: S) │ (Effort: M or L)
             │
        LOW IMPACT (< 4)
```

1. **⚡ Quick Wins** (High Impact $\ge 4$, Low Effort `S`): Fix immediately. Generates the highest ROI for agency clients.
2. **🏗️ Major Projects** (High Impact $\ge 4$, High Effort `M`/`L`): Strategic investments (e.g. migrating CSR app to Next.js SSR, overhaul of entity schema).
3. **🧹 Fill-Ins** (Low Impact $< 4$, Low Effort `S`): Minor housekeeping tasks (e.g. fixing heading skips or missing table headers).
4. **⏳ Thankless Tasks** (Low Impact $< 4$, High Effort `M`/`L`): Deprioritize. Only address after higher-value quadrants are resolved.
