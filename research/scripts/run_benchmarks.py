"""Benchmark exploration script for Phase 1 landscape study.
Fetches public benchmark sites, inspects robots.txt, measures TTFB, extracts structured data,
and saves outputs to research/outputs/.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any
import httpx
import extruct
from selectolax.lexbor import LexborHTMLParser

BENCHMARK_SITES = [
    {
        "id": "python-docs",
        "url": "https://docs.python.org/3/",
        "category": "Static / Sphinx HTML",
    },
    {
        "id": "techcrunch",
        "url": "https://techcrunch.com",
        "category": "WordPress / News CMS",
    },
    {
        "id": "vercel-blog",
        "url": "https://vercel.com/blog",
        "category": "Next.js / Modern SPA",
    },
    {
        "id": "books-toscrape",
        "url": "https://books.toscrape.com",
        "category": "eCommerce Catalog",
    },
    {
        "id": "cloudflare-learning",
        "url": "https://www.cloudflare.com/learning/",
        "category": "B2B Educational Hub",
    },
]

HEADERS = {
    "User-Agent": "AuditIQResearch/1.0 (+https://auditiq.dev/bot-research; academic-benchmarking)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


async def inspect_site(client: httpx.AsyncClient, site: dict[str, str], out_dir: Path) -> dict[str, Any]:
    url = site["url"]
    site_id = site["id"]
    print(f"[*] Inspecting {site_id} ({url})...")
    
    # 1. Fetch robots.txt
    from urllib.parse import urljoin
    robots_url = urljoin(url, "/robots.txt")
    robots_text = ""
    robots_status = None
    try:
        r_resp = await client.get(robots_url, timeout=10.0)
        robots_status = r_resp.status_code
        if r_resp.status_code == 200:
            robots_text = r_resp.text
    except Exception as e:
        robots_text = f"Error fetching robots.txt: {e}"

    # 2. Fetch main page
    start = time.perf_counter()
    page_resp = None
    ttfb_ms = 0.0
    elapsed_ms = 0.0
    status_code = None
    headers_dict: dict[str, str] = {}
    html_content = ""
    error_msg = None

    try:
        page_resp = await client.get(url, timeout=15.0, follow_redirects=True)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        status_code = page_resp.status_code
        headers_dict = dict(page_resp.headers)
        html_content = page_resp.text
        # Approximate TTFB as elapsed since httpx streams by default on full read
        ttfb_ms = elapsed_ms
    except Exception as e:
        error_msg = str(e)

    # 3. Parse with Selectolax
    title = ""
    meta_desc = ""
    h1s: list[str] = []
    canonical = ""
    word_count = 0
    semantic_tags_count = 0
    div_count = 0

    if html_content:
        parser = LexborHTMLParser(html_content)
        title_node = parser.css_first("title")
        if title_node:
            title = title_node.text(strip=True)
        
        meta_desc_node = parser.css_first('meta[name="description"]')
        if meta_desc_node:
            meta_desc = meta_desc_node.attributes.get("content", "")

        canonical_node = parser.css_first('link[rel="canonical"]')
        if canonical_node:
            canonical = canonical_node.attributes.get("href", "")

        for h1 in parser.css("h1"):
            h1s.append(h1.text(strip=True))

        body_node = parser.css_first("body")
        if body_node:
            text = body_node.text(separator=" ", strip=True)
            word_count = len(text.split())

        semantic_tags_count = len(parser.css("main, article, section, header, nav, footer, aside"))
        div_count = len(parser.css("div"))

    # 4. Extract Structured Data with extruct
    structured_data: dict[str, Any] = {}
    if html_content:
        try:
            data = extruct.extract(html_content, base_url=url, syntaxes=['json-ld', 'microdata'])
            structured_data = {
                "json_ld_count": len(data.get("json-ld", [])),
                "json_ld_types": [item.get("@type") for item in data.get("json-ld", []) if isinstance(item, dict)],
                "microdata_count": len(data.get("microdata", [])),
            }
        except Exception as ex:
            structured_data = {"error": str(ex)}

    result = {
        "site_id": site_id,
        "url": url,
        "category": site["category"],
        "status_code": status_code,
        "elapsed_ms": elapsed_ms,
        "ttfb_ms": ttfb_ms,
        "page_size_kb": round(len(html_content.encode("utf-8")) / 1024, 2) if html_content else 0,
        "title": title,
        "meta_desc_length": len(meta_desc),
        "h1_count": len(h1s),
        "h1_sample": h1s[:2],
        "canonical": canonical,
        "word_count": word_count,
        "semantic_tags_count": semantic_tags_count,
        "div_count": div_count,
        "semantic_to_div_ratio": round(semantic_tags_count / max(1, div_count), 3),
        "structured_data": structured_data,
        "robots_status": robots_status,
        "robots_sample": robots_text[:500] if robots_text else "",
        "error": error_msg,
    }

    # Save to disk
    site_out = out_dir / f"{site_id}.json"
    with open(site_out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[+] Saved {site_out}")
    return result


async def main() -> None:
    out_dir = Path("research/outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(headers=HEADERS, verify=False) as client:
        results = await asyncio.gather(*[inspect_site(client, site, out_dir) for site in BENCHMARK_SITES])

    summary_file = out_dir / "benchmarks_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[✓] Research benchmark run complete! Summary written to {summary_file}")


if __name__ == "__main__":
    asyncio.run(main())
