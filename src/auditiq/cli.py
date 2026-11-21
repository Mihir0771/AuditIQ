"""AuditIQ Command Line Interface (Typer & Rich)."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import auditiq
from auditiq.checks.content import register_content_checks
from auditiq.checks.geo import register_geo_checks
from auditiq.checks.live import register_live_checks
from auditiq.checks.registry import default_registry
from auditiq.checks.tech import register_tech_checks
from auditiq.crawler.engine import HttpCrawler
from auditiq.models.audit import AuditConfig, AuditRecord, AuditStatus
from auditiq.models.finding import AuditLayer
from auditiq.scoring.engine import calculate_score_card
from auditiq.visibility.generator import PromptGenerator
from auditiq.visibility.runner import VisibilityRunner

app = typer.Typer(
    name="auditiq",
    help="AuditIQ — Production-grade AI SEO & GEO Audit Engine.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def crawl(
    url: Annotated[str, typer.Argument(help="Target website URL to crawl")],
    max_pages: Annotated[int, typer.Option("--max-pages", "-m", help="Max pages to crawl")] = 50,
    depth: Annotated[int, typer.Option("--depth", "-d", help="Max crawl click depth")] = 3,
    concurrency: Annotated[
        int, typer.Option("--concurrency", "-c", help="Concurrent request limit")
    ] = 5,
    out: Annotated[Path | None, typer.Option("--out", "-o", help="Output JSON file")] = None,
) -> None:
    """Performs a polite, asynchronous crawl of a website and prints a structured summary."""
    console.print(
        Panel.fit(
            f"[bold cyan]AuditIQ Polite Crawler[/bold cyan]\nTarget: [green]{url}[/green] | Max Pages: {max_pages} | Depth: {depth}",
            border_style="cyan",
        )
    )

    crawler = HttpCrawler(
        start_url=url,
        max_pages=max_pages,
        max_depth=depth,
        concurrency=concurrency,
    )

    with console.status("[bold green]Crawling website...[/bold green]", spinner="dots"):
        result = asyncio.run(crawler.crawl())

    # Display Rich summary table
    table = Table(title="Crawl Results Summary", box=box.ROUNDED)
    table.add_column("Status", style="bold")
    table.add_column("URL", style="cyan")
    table.add_column("Depth", justify="right")
    table.add_column("TTFB (ms)", justify="right")
    table.add_column("Title", style="italic")

    for u, snap in list(result.pages.items())[:30]:
        status_style = (
            "green" if snap.status_code == 200 else "red" if snap.status_code >= 400 else "yellow"
        )
        table.add_row(
            f"[{status_style}]{snap.status_code}[/{status_style}]",
            u[:60] + ("..." if len(u) > 60 else ""),
            str(snap.depth),
            f"{snap.ttfb_ms:.0f}",
            snap.title[:35] + ("..." if len(snap.title) > 35 else ""),
        )

    console.print(table)
    console.print(
        f"\n[bold green]✓[/bold green] Crawled {result.total_pages_crawled} pages in {result.crawl_duration_sec}s. "
        f"Discovered {len(result.sitemap_urls)} sitemap URLs."
    )

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))
        console.print(f"[bold cyan]Saved crawl snapshot to {out}[/bold cyan]")


@app.command()
def audit(
    url: Annotated[str, typer.Argument(help="Target website URL to audit")],
    brand: Annotated[str, typer.Option("--brand", "-b", help="Target brand name")] = "",
    layers: Annotated[
        str, typer.Option("--layers", "-l", help="Comma-separated layers: tech,content,geo,live")
    ] = "tech",
    max_pages: Annotated[int, typer.Option("--max-pages", "-m", help="Max pages to crawl")] = 30,
    depth: Annotated[int, typer.Option("--depth", "-d", help="Max crawl click depth")] = 3,
    mock_ai: Annotated[
        bool, typer.Option("--mock-ai", help="Use deterministic mock AI engines for testing")
    ] = False,
    out: Annotated[Path | None, typer.Option("--out", "-o", help="Output directory")] = None,
) -> None:
    """Executes a multi-layer audit against the target website and computes an evidence-backed score."""
    # Ensure checks are registered
    register_tech_checks()
    register_content_checks()
    register_geo_checks()
    register_live_checks()

    # Parse layers
    layer_map = {
        "tech": AuditLayer.TECHNICAL,
        "content": AuditLayer.CONTENT,
        "geo": AuditLayer.GEO_READINESS,
        "live": AuditLayer.LIVE_VISIBILITY,
    }
    active_layers: list[AuditLayer] = []
    for l_str in layers.split(","):
        l_clean = l_str.strip().lower()
        if l_clean in layer_map:
            active_layers.append(layer_map[l_clean])

    if not active_layers:
        active_layers = [AuditLayer.TECHNICAL]

    console.print(
        Panel.fit(
            f"[bold cyan]AuditIQ Full Audit Engine[/bold cyan]\n"
            f"Target: [green]{url}[/green] | Layers: {[layer_item.value for layer_item in active_layers]} | Max Pages: {max_pages}",
            border_style="cyan",
        )
    )

    config = AuditConfig(
        target_url=url,
        brand_name=brand,
        layers=active_layers,
        max_pages=max_pages,
        max_depth=depth,
    )

    # 1. Polite Crawl
    crawler = HttpCrawler(start_url=url, max_pages=max_pages, max_depth=depth)
    with console.status("[bold green]Crawling website...[/bold green]", spinner="dots"):
        crawl_result = asyncio.run(crawler.crawl())

    # 2. Live AI Visibility (if layer active)
    visibility_summary = None
    if AuditLayer.LIVE_VISIBILITY in active_layers:
        runner = VisibilityRunner(use_mock_fallback=mock_ai)
        if runner.has_available_engines():
            with console.status(
                f"[bold green]Querying AI Answer Engines ({', '.join(e.name for e in runner.engines)})...[/bold green]",
                spinner="dots",
            ):
                queries = PromptGenerator.generate_queries(
                    crawl_result, brand_name=brand or None, max_queries=15
                )
                visibility_summary = asyncio.run(runner.run(queries))
        else:
            console.print(
                "[bold yellow]![/bold yellow] Live AI Visibility: No API keys configured (run with --mock-ai for offline simulation)."
            )

    # 3. Run Checks
    with console.status("[bold green]Evaluating audit checks...[/bold green]", spinner="dots"):
        findings = asyncio.run(
            default_registry.run_checks(
                crawl_result,
                config,
                active_layers,
                visibility_summary=visibility_summary,
            )
        )

    # 3. Calculate Scores & Prioritization
    score_card = calculate_score_card(
        findings=findings,
        total_pages_crawled=crawl_result.total_pages_crawled,
        active_layers=active_layers,
    )

    # Display Score Card Table
    score_table = Table(
        title=f"AuditIQ Score: {score_card.letter_grade} ({score_card.composite_score}/100)",
        box=box.ROUNDED,
    )
    score_table.add_column("Audit Layer", style="bold cyan")
    score_table.add_column("Score", justify="right")
    score_table.add_column("Weight", justify="right")

    for layer_item in active_layers:
        l_score = score_card.layer_scores.get(layer_item)
        score_str = f"{l_score:.1f}/100" if l_score is not None else "Not measured"
        score_table.add_row(
            layer_item.value.replace("_", " ").title(),
            score_str,
            f"{score_card.layer_weights.get(layer_item, 0) * 100:.0f}%",
        )
    console.print(score_table)

    # Display Live AI Visibility Benchmark if available
    if visibility_summary:
        vis_table = Table(
            title=f"Live AI Answer Engine Visibility Benchmark ({', '.join(visibility_summary.active_engines)})",
            box=box.ROUNDED,
        )
        vis_table.add_column("Visibility Metric", style="bold cyan")
        vis_table.add_column("Observed Rate (95% CI)", justify="right")
        vis_table.add_column("Evaluations", justify="right")

        vis_table.add_row(
            "Brand Mention Rate",
            visibility_summary.mention_rate.display,
            f"n={visibility_summary.mention_rate.sample_size}",
        )
        vis_table.add_row(
            "Domain Citation Rate",
            visibility_summary.citation_rate.display,
            f"n={visibility_summary.citation_rate.sample_size}",
        )
        vis_table.add_row(
            "Competitive Share of Voice", f"{visibility_summary.share_of_voice}%", "-"
        )
        console.print(vis_table)

    # Display Top Action Items
    if score_card.priority_actions:
        action_table = Table(
            title="Top Prioritized Remediation Actions (Impact × Effort)", box=box.ROUNDED
        )
        action_table.add_column("Priority Quadrant", style="bold yellow")
        action_table.add_column("Issue Title", style="bold")
        action_table.add_column("Impact", justify="center")
        action_table.add_column("Effort", justify="center")
        action_table.add_column("Pages Affected", justify="right")

        for act in score_card.priority_actions[:8]:
            action_table.add_row(
                act.quadrant.value,
                act.title,
                str(act.impact),
                act.effort,
                str(act.affected_pages_count),
            )
        console.print(action_table)

    # Save outputs if requested
    out_dir = out or Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    import hashlib

    audit_id = hashlib.sha256(f"{url}:{score_card.composite_score}".encode()).hexdigest()[:10]
    out_file = out_dir / f"audit_{audit_id}.json"

    record = AuditRecord(
        id=audit_id,
        config=config,
        status=AuditStatus.COMPLETED,
        score_card=score_card,
        findings=findings,
        crawl_summary={
            "total_pages": crawl_result.total_pages_crawled,
            "duration_sec": crawl_result.crawl_duration_sec,
            "sitemap_urls_count": len(crawl_result.sitemap_urls),
        },
    )

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(record.model_dump_json(indent=2))

    console.print(
        f"\n[bold green]✓[/bold green] Audit complete! Full report saved to [cyan]{out_file}[/cyan]"
    )


@app.command()
def doctor() -> None:
    """Verifies Python version, Playwright Chromium, configs, and environment health."""
    console.print(
        Panel.fit("[bold cyan]AuditIQ System Diagnostics (Doctor)[/bold cyan]", border_style="cyan")
    )

    # 1. Python check
    py_ver = sys.version.split()[0]
    console.print(f"[bold green]✓[/bold green] Python Version: {py_ver}")

    # 2. Package version
    register_tech_checks()
    register_content_checks()
    register_geo_checks()
    register_live_checks()
    console.print(
        f"[bold green]✓[/bold green] AuditIQ Package: v{auditiq.__version__} ({len(default_registry.get_checks())} audit checks registered)"
    )

    # 3. Config check
    cfg_dir = Path("config")
    bots_cfg = cfg_dir / "ai_bots.yaml"
    scoring_cfg = cfg_dir / "scoring.yaml"
    branding_cfg = cfg_dir / "branding.yaml"

    for cfg_path in (bots_cfg, scoring_cfg, branding_cfg):
        if cfg_path.exists():
            console.print(f"[bold green]✓[/bold green] Config file: {cfg_path.name}")
        else:
            console.print(f"[bold red]✗[/bold red] Missing config file: {cfg_path.name}")

    # 4. Playwright Chromium check
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        console.print("[bold green]✓[/bold green] Playwright Chromium Browser: Operational")
    except Exception as e:
        console.print(
            f"[bold yellow]![/bold yellow] Playwright Chromium not yet installed or headless unavailable: {e}"
        )
        console.print("  [dim]Run: python -m playwright install chromium[/dim]")

    # 5. API keys check (optional)
    keys = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "PERPLEXITY_API_KEY",
        "PAGESPEED_API_KEY",
    ]
    found_keys = [k for k in keys if os.getenv(k)]
    if found_keys:
        console.print(f"[bold green]✓[/bold green] Configured API Keys: {', '.join(found_keys)}")
    else:
        console.print(
            "[bold yellow]![/bold yellow] No external API keys found in environment (Live AI Visibility will be 'Not measured')"
        )

    console.print("\n[bold green]Doctor diagnosis complete.[/bold green]")


if __name__ == "__main__":
    app()
