import asyncio
from auditiq.crawler.engine import HttpCrawler
from auditiq.checks.registry import default_registry
from auditiq.checks.tech import register_tech_checks
from auditiq.checks.content import register_content_checks
from auditiq.checks.geo import register_geo_checks
from auditiq.scoring.engine import calculate_score_card
from auditiq.models.finding import AuditLayer
from auditiq.models.audit import AuditConfig

register_tech_checks()
register_content_checks()
register_geo_checks()

async def test_sites():
    # Targets from Colorlib bad websites article
    test_urls = [
        ("Colorlib Bad Websites Article", "https://colorlib.com/wp/bad-websites/"),
        ("Pacific Northwest X-Ray (Bad UI/Structure)", "http://www2.pnwx.com/"),
        ("Arngren (Infamous Worst Website)", "https://arngren.net/"),
        ("Penny Juice (Terrible Layout/Colors)", "https://www.pennyjuice.com/"),
        ("Ling's Cars (Viral Cluttered Website)", "https://www.lingscars.com/"),
        ("Yale School of Art (Wiki/Chaotic)", "https://art.yale.edu/"),
        ("Berkshire Hathaway (90s Plain HTML)", "https://www.berkshirehathaway.com/"),
    ]

    layers = [AuditLayer.TECHNICAL, AuditLayer.CONTENT, AuditLayer.GEO_READINESS]

    for name, url in test_urls:
        print(f"\n=======================================================")
        print(f"TARGET: {name} ({url})")
        crawler = HttpCrawler(start_url=url, max_pages=3, max_depth=1, timeout_sec=12.0)
        try:
            crawl_res = await crawler.crawl()
            print(f"Crawled: {crawl_res.total_pages_crawled} pages.")
            start_snap = crawl_res.pages.get(crawl_res.start_url)
            if not start_snap:
                alt = crawl_res.start_url.rstrip("/") if crawl_res.start_url.endswith("/") else crawl_res.start_url + "/"
                start_snap = crawl_res.pages.get(alt)
            print(f"Start URL Status: {start_snap.status_code if start_snap else 'None'}, Error: {start_snap.error if start_snap else 'None'}")
            
            cfg = AuditConfig(target_url=url, brand_name=name, layers=layers, max_pages=3, max_depth=1)
            findings = await default_registry.run_checks(
                crawl_result=crawl_res,
                config=cfg,
                active_layers=layers,
            )
            
            score_card = calculate_score_card(
                findings=findings,
                total_pages_crawled=crawl_res.total_pages_crawled,
                active_layers=layers,
                registered_checks=default_registry.get_checks(),
            )
            print(f"SCORE: {score_card.composite_score} / 100 (Grade {score_card.letter_grade})")
            print(f"Layer Scores: Tech={score_card.layer_scores.get(AuditLayer.TECHNICAL)}, Content={score_card.layer_scores.get(AuditLayer.CONTENT)}, GEO={score_card.layer_scores.get(AuditLayer.GEO_READINESS)}")
            
            fails = [f for f in findings if f.status == "fail"]
            warns = [f for f in findings if f.status == "warning"]
            print(f"Findings: {len(fails)} fails, {len(warns)} warnings")
            print("Failed Checks:")
            for f in fails[:8]:
                print(f"  - [{f.severity.upper()}] {f.title} ({f.check_id})")
            if score_card.top_negative_drivers:
                print("Negative Drivers:")
                for d in score_card.top_negative_drivers[:5]:
                    print(f"  - {d}")
        except Exception as e:
            print(f"Exception during audit: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_sites())
