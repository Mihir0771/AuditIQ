"""Print-ready PDF report generation via Headless Chromium."""

import asyncio
from pathlib import Path

import jinja2
from playwright.async_api import async_playwright

from auditiq.models.audit import AuditRecord
from auditiq.reports.html import load_branding_config


async def generate_pdf_report_async(
    record: AuditRecord,
    output_path: Path | None = None,
    branding_path: Path | None = None,
) -> Path:
    """Generates an agency-branded, print-ready PDF audit report using Headless Chromium."""
    out_file = output_path or Path(f"reports/report_{record.id}.pdf")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Render HTML directly into memory without file I/O latency
    branding = load_branding_config(branding_path)
    templates_dir = Path(__file__).parent / "templates"
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(templates_dir)),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html.jinja2")
    rendered_html = template.render(record=record, branding=branding)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(rendered_html, wait_until="domcontentloaded")
        await page.pdf(
            path=str(out_file),
            print_background=True,
            format="A4",
            margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"},
        )
        await browser.close()

    return out_file


def generate_pdf_report(
    record: AuditRecord,
    output_path: Path | None = None,
    branding_path: Path | None = None,
) -> Path:
    """Synchronous wrapper for generating PDF report."""
    return asyncio.run(
        generate_pdf_report_async(record, output_path=output_path, branding_path=branding_path)
    )
