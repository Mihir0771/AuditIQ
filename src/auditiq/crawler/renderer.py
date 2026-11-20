"""Selective headless browser rendering engine powered by Playwright."""

import logging
from pathlib import Path
from pydantic import BaseModel

logger = logging.getLogger("auditiq.crawler.renderer")


class RenderResult(BaseModel):
    url: str
    rendered_html: str
    screenshot_path: str | None = None
    elapsed_ms: float = 0.0
    error: str | None = None


class SelectiveRenderer:
    """Manages headless Chromium instances for selective DOM rendering and screenshots."""

    def __init__(self, headless: bool = True, timeout_sec: float = 20.0) -> None:
        self.headless = headless
        self.timeout_sec = timeout_sec

    async def render_page(self, url: str, screenshot_dir: Path | None = None) -> RenderResult:
        """Launches headless Chromium, navigates to the URL, waits for network idle,

        and extracts the hydrated DOM tree and optional screenshot.
        """
        import time

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return RenderResult(
                url=url,
                rendered_html="",
                error="playwright package is not installed.",
            )

        start = time.perf_counter()
        screenshot_file: str | None = None

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 AuditIQ/1.0",
                )
                page = await context.new_page()

                # Navigate and wait for DOM load
                await page.goto(url, wait_until="load", timeout=int(self.timeout_sec * 1000))

                # Allow a short grace period for hydration
                try:
                    await page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    pass

                rendered_html = await page.content()

                if screenshot_dir:
                    screenshot_dir.mkdir(parents=True, exist_ok=True)
                    safe_name = "".join(c if c.isalnum() else "_" for c in url)[:60]
                    target_path = screenshot_dir / f"{safe_name}.png"
                    await page.screenshot(path=str(target_path), full_page=False)
                    screenshot_file = str(target_path)

                await context.close()
                await browser.close()

                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                return RenderResult(
                    url=url,
                    rendered_html=rendered_html,
                    screenshot_path=screenshot_file,
                    elapsed_ms=elapsed_ms,
                )

        except Exception as e:
            logger.warning("Rendering failed for %s: %s", url, e)
            return RenderResult(
                url=url,
                rendered_html="",
                error=f"Playwright render error: {e}",
            )
