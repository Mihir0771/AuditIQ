"""Selective headless browser rendering engine powered by Playwright with session pooling."""

import contextlib
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger("auditiq.crawler.renderer")


class RenderResult(BaseModel):
    url: str
    rendered_html: str
    screenshot_path: str | None = None
    elapsed_ms: float = 0.0
    error: str | None = None


class SelectiveRenderer:
    """Manages headless Chromium instances for selective DOM rendering and screenshots.

    Supports session-scoped browser pooling to eliminate cold launch latency across pages.
    """

    def __init__(self, headless: bool = True, timeout_sec: float = 20.0) -> None:
        self.headless = headless
        self.timeout_sec = timeout_sec
        self._playwright: Any = None
        self._browser: Any = None

    async def start(self) -> None:
        """Initializes shared Playwright instance and launches pooled Chromium browser."""
        if self._browser is not None:
            return
        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-gpu",
                ],
            )
            logger.debug("SelectiveRenderer browser pool started successfully.")
        except Exception as e:
            logger.warning("Could not initialize pooled Chromium browser: %s", e)
            self._browser = None

    async def stop(self) -> None:
        """Gracefully closes pooled Chromium browser and Playwright runtime."""
        if self._browser is not None:
            with contextlib.suppress(Exception):
                await self._browser.close()
            self._browser = None

        if self._playwright is not None:
            with contextlib.suppress(Exception):
                await self._playwright.stop()
            self._playwright = None
        logger.debug("SelectiveRenderer browser pool terminated.")

    async def __aenter__(self) -> "SelectiveRenderer":
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.stop()

    async def render_page(self, url: str, screenshot_dir: Path | None = None) -> RenderResult:
        """Navigates to the URL using the pooled browser (or an ad-hoc session if not started),

        waits for network idle, and extracts the hydrated DOM tree and optional screenshot.
        """
        import time

        start = time.perf_counter()
        screenshot_file: str | None = None

        # 1. Preferred fast path: Use pooled browser session
        if self._browser is not None:
            try:
                context = await self._browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 AuditIQ/1.0"
                    ),
                )
                page = await context.new_page()

                # Navigate and wait for DOM load
                await page.goto(url, wait_until="load", timeout=int(self.timeout_sec * 1000))

                # Allow a short grace period for hydration
                with contextlib.suppress(Exception):
                    await page.wait_for_load_state("networkidle", timeout=3000)

                rendered_html = await page.content()

                if screenshot_dir:
                    screenshot_dir.mkdir(parents=True, exist_ok=True)
                    safe_name = "".join(c if c.isalnum() else "_" for c in url)[:60]
                    target_path = screenshot_dir / f"{safe_name}.png"
                    await page.screenshot(path=str(target_path), full_page=False)
                    screenshot_file = str(target_path)

                await context.close()
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                return RenderResult(
                    url=url,
                    rendered_html=rendered_html,
                    screenshot_path=screenshot_file,
                    elapsed_ms=elapsed_ms,
                )
            except Exception as e:
                logger.warning("Pooled render failed for %s: %s", url, e)
                return RenderResult(
                    url=url,
                    rendered_html="",
                    error=f"Playwright render error: {e}",
                )

        # 2. Fallback path: Standalone ad-hoc launch (for one-off calls or unpooled runs)
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return RenderResult(
                url=url,
                rendered_html="",
                error="playwright package is not installed.",
            )

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 AuditIQ/1.0"
                    ),
                )
                page = await context.new_page()

                await page.goto(url, wait_until="load", timeout=int(self.timeout_sec * 1000))
                with contextlib.suppress(Exception):
                    await page.wait_for_load_state("networkidle", timeout=3000)

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
            logger.warning("Standalone rendering failed for %s: %s", url, e)
            return RenderResult(
                url=url,
                rendered_html="",
                error=f"Playwright render error: {e}",
            )
