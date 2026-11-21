"""Print-ready PDF report generation via Headless Chromium."""

import asyncio
import contextlib
from pathlib import Path

from playwright.async_api import async_playwright

from auditiq.models.audit import AuditRecord
from auditiq.reports.html import generate_html_report


async def generate_pdf_report_async(
    record: AuditRecord,
    output_path: Path | None = None,
    branding_path: Path | None = None,
) -> Path:
    """Generates an agency-branded, print-ready PDF audit report using Headless Chromium."""
    out_file = output_path or Path(f"reports/report_{record.id}.pdf")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # First generate the HTML report
    temp_html = out_file.parent / f"_temp_{record.id}.html"
    generate_html_report(record, output_path=temp_html, branding_path=branding_path)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            # Convert file path to file:// URI for Windows/Unix compatibility
            file_uri = temp_html.resolve().as_uri()
            await page.goto(file_uri, wait_until="load")
            await page.pdf(
                path=str(out_file),
                print_background=True,
                format="A4",
                margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"},
            )
            await browser.close()
    finally:
        if temp_html.exists():
            with contextlib.suppress(Exception):
                temp_html.unlink()

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
