"""Asynchronous audit job runner with SSE progress broadcasting."""

import asyncio
import contextlib
import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from auditiq.checks.content import register_content_checks
from auditiq.checks.geo import register_geo_checks
from auditiq.checks.live import register_live_checks
from auditiq.checks.registry import default_registry
from auditiq.checks.tech import register_tech_checks
from auditiq.crawler.engine import HttpCrawler
from auditiq.models.audit import AuditConfig, AuditRecord, AuditStatus
from auditiq.models.finding import AuditLayer
from auditiq.reports.html import generate_html_report
from auditiq.scoring.engine import calculate_score_card
from auditiq.visibility.generator import PromptGenerator
from auditiq.visibility.runner import VisibilityRunner

logger = logging.getLogger("auditiq.server.jobs")


class AuditJob(BaseModel):
    id: str
    url: str
    brand_name: str = ""
    status: AuditStatus = AuditStatus.PENDING
    progress_pct: int = 0
    message: str = "Initialized"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    record: AuditRecord | None = None
    error: str | None = None


class JobManager:
    """Manages active background audit jobs and event distribution."""

    def __init__(self, reports_dir: Path | None = None) -> None:
        self.reports_dir = reports_dir or Path("reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, AuditJob] = {}
        self.event_queues: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}

    def get_job(self, job_id: str) -> AuditJob | None:
        if job_id in self.jobs:
            return self.jobs[job_id]

        # Check on-disk report
        disk_file = self.reports_dir / f"audit_{job_id}.json"
        if disk_file.exists():
            try:
                with open(disk_file, encoding="utf-8") as f:
                    rec = AuditRecord.model_validate(json.load(f))
                    job = AuditJob(
                        id=job_id,
                        url=rec.config.target_url,
                        brand_name=rec.config.brand_name,
                        status=AuditStatus.COMPLETED,
                        progress_pct=100,
                        message="Completed",
                        record=rec,
                    )
                    self.jobs[job_id] = job
                    return job
            except Exception as e:
                logger.error("Failed to load on-disk audit %s: %s", job_id, e)

        return None

    def list_jobs(self) -> list[dict[str, Any]]:
        results = []
        # Add in-memory jobs
        for j in self.jobs.values():
            results.append(
                {
                    "id": j.id,
                    "url": j.url,
                    "brand": j.brand_name,
                    "status": j.status.value,
                    "progress": j.progress_pct,
                    "score": j.record.score_card.composite_score
                    if j.record and j.record.score_card
                    else None,
                    "grade": j.record.score_card.letter_grade
                    if j.record and j.record.score_card
                    else None,
                    "date": j.created_at.strftime("%Y-%m-%d %H:%M"),
                }
            )

        # Also discover on-disk audit files
        for p in self.reports_dir.glob("audit_*.json"):
            jid = p.stem.replace("audit_", "")
            if jid not in self.jobs:
                try:
                    with open(p, encoding="utf-8") as f:
                        data = json.load(f)
                        score_card = data.get("score_card") or {}
                        results.append(
                            {
                                "id": jid,
                                "url": data.get("config", {}).get("target_url", "Unknown"),
                                "brand": data.get("config", {}).get("brand_name", ""),
                                "status": data.get("status", "completed"),
                                "progress": 100,
                                "score": score_card.get("composite_score"),
                                "grade": score_card.get("letter_grade"),
                                "date": data.get("created_at", "")[:16].replace("T", " "),
                            }
                        )
                except Exception:
                    pass

        return results

    async def subscribe(self, job_id: str) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        if job_id not in self.event_queues:
            self.event_queues[job_id] = []
        self.event_queues[job_id].append(q)
        return q

    async def unsubscribe(self, job_id: str, q: asyncio.Queue[dict[str, Any]]) -> None:
        if job_id in self.event_queues:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                self.event_queues[job_id].remove(q)

    async def broadcast(self, job_id: str, event_data: dict[str, Any]) -> None:
        job = self.jobs.get(job_id)
        if job:
            job.status = event_data.get("status", job.status)
            job.progress_pct = event_data.get("progress_pct", job.progress_pct)
            job.message = event_data.get("message", job.message)

        queues = self.event_queues.get(job_id, [])
        for q in queues:
            await q.put(event_data)

    def start_job(
        self,
        target_url: str,
        brand_name: str = "",
        layers: list[AuditLayer] | None = None,
        max_pages: int = 30,
        max_depth: int = 3,
        mock_ai: bool = False,
    ) -> str:
        job_id = hashlib.sha256(
            f"{target_url}:{datetime.now(UTC).isoformat()}".encode()
        ).hexdigest()[:10]
        job = AuditJob(
            id=job_id,
            url=target_url,
            brand_name=brand_name,
            status=AuditStatus.PENDING,
            progress_pct=0,
            message="Queued",
        )
        self.jobs[job_id] = job

        # Launch background task
        asyncio.create_task(
            self._execute_audit(
                job_id=job_id,
                target_url=target_url,
                brand_name=brand_name,
                layers=layers
                or [AuditLayer.TECHNICAL, AuditLayer.CONTENT, AuditLayer.GEO_READINESS],
                max_pages=max_pages,
                max_depth=max_depth,
                mock_ai=mock_ai,
            )
        )
        return job_id

    async def _execute_audit(
        self,
        job_id: str,
        target_url: str,
        brand_name: str,
        layers: list[AuditLayer],
        max_pages: int,
        max_depth: int,
        mock_ai: bool,
    ) -> None:
        try:
            # Register check suites
            register_tech_checks()
            register_content_checks()
            register_geo_checks()
            register_live_checks()

            config = AuditConfig(
                target_url=target_url,
                brand_name=brand_name,
                layers=layers,
                max_pages=max_pages,
                max_depth=max_depth,
            )

            await self.broadcast(
                job_id,
                {
                    "status": AuditStatus.CRAWLING,
                    "progress_pct": 10,
                    "message": f"Politely crawling {target_url} (max {max_pages} pages)...",
                },
            )

            # 1. Crawl
            crawler = HttpCrawler(start_url=target_url, max_pages=max_pages, max_depth=max_depth)

            def _progress(url: str, current: int, total: int) -> None:
                pct = min(40, 10 + int((current / max(1, total)) * 30))
                asyncio.create_task(
                    self.broadcast(
                        job_id,
                        {
                            "status": AuditStatus.CRAWLING,
                            "progress_pct": pct,
                            "message": f"Crawled ({current}/{total}): {url}",
                        },
                    )
                )

            crawl_result = await crawler.crawl(progress_callback=_progress)

            # 2. Live Visibility (if active)
            visibility_summary = None
            if AuditLayer.LIVE_VISIBILITY in layers:
                await self.broadcast(
                    job_id,
                    {
                        "status": AuditStatus.CHECKING,
                        "progress_pct": 45,
                        "message": "Querying AI Answer Engines for real-time visibility...",
                    },
                )
                runner = VisibilityRunner(use_mock_fallback=mock_ai)
                if runner.has_available_engines():
                    queries = PromptGenerator.generate_queries(
                        crawl_result, brand_name=brand_name or None, max_queries=15
                    )
                    visibility_summary = await runner.run(queries)

            # 3. Checks evaluation
            await self.broadcast(
                job_id,
                {
                    "status": AuditStatus.CHECKING,
                    "progress_pct": 60,
                    "message": "Evaluating Technical, Content, and GEO check rules...",
                },
            )
            findings = await default_registry.run_checks(
                crawl_result=crawl_result,
                config=config,
                active_layers=layers,
                visibility_summary=visibility_summary,
            )

            # 4. Scoring & Prioritization
            await self.broadcast(
                job_id,
                {
                    "status": AuditStatus.SCORING,
                    "progress_pct": 80,
                    "message": "Computing composite mathematical score & prioritizing actions...",
                },
            )
            score_card = calculate_score_card(
                findings=findings,
                total_pages_crawled=crawl_result.total_pages_crawled,
                active_layers=layers,
            )

            # 5. Build Record & Reports
            await self.broadcast(
                job_id,
                {
                    "status": AuditStatus.REPORTING,
                    "progress_pct": 90,
                    "message": "Generating white-label report and structured JSON...",
                },
            )

            record = AuditRecord(
                id=job_id,
                config=config,
                status=AuditStatus.COMPLETED,
                completed_at=datetime.now(UTC),
                score_card=score_card,
                findings=findings,
                crawl_summary={
                    "total_pages": crawl_result.total_pages_crawled,
                    "duration_sec": crawl_result.crawl_duration_sec,
                    "sitemap_urls_count": len(crawl_result.sitemap_urls),
                    "base_domain": crawl_result.base_domain,
                },
            )

            # Save on disk
            json_file = self.reports_dir / f"audit_{job_id}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                f.write(record.model_dump_json(indent=2))

            html_file = self.reports_dir / f"report_{job_id}.html"
            generate_html_report(record, output_path=html_file)

            job = self.jobs.get(job_id)
            if job:
                job.record = record

            await self.broadcast(
                job_id,
                {
                    "status": AuditStatus.COMPLETED,
                    "progress_pct": 100,
                    "message": f"Audit complete! Score: {score_card.letter_grade} ({score_card.composite_score}/100)",
                    "score": score_card.composite_score,
                    "grade": score_card.letter_grade,
                },
            )

        except Exception as e:
            logger.error("Audit %s failed: %s", job_id, e, exc_info=True)
            job = self.jobs.get(job_id)
            if job:
                job.status = AuditStatus.FAILED
                job.error = str(e)
            await self.broadcast(
                job_id,
                {
                    "status": AuditStatus.FAILED,
                    "progress_pct": 100,
                    "message": f"Audit failed: {e}",
                    "error": str(e),
                },
            )


job_manager = JobManager()
