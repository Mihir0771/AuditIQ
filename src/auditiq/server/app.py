"""AuditIQ FastAPI Server & REST API."""

import asyncio
import json
import os
import sys
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

import auditiq
from auditiq.checks.content import register_content_checks
from auditiq.checks.geo import register_geo_checks
from auditiq.checks.live import register_live_checks
from auditiq.checks.registry import default_registry
from auditiq.checks.tech import register_tech_checks
from auditiq.models.finding import AuditLayer
from auditiq.reports.pdf import generate_pdf_report_async
from auditiq.scoring.regression import compare_audits
from auditiq.server.jobs import job_manager

app = FastAPI(
    title="AuditIQ Engine API",
    description="Production-grade AI SEO & GEO Audit Engine REST API",
    version=auditiq.__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateAuditRequest(BaseModel):
    url: str
    brand_name: str = ""
    layers: list[str] = Field(default_factory=lambda: ["tech", "content", "geo", "live"])
    max_pages: int = Field(default=30, ge=1, le=500)
    max_depth: int = Field(default=3, ge=1, le=10)
    mock_ai: bool = False


class CompareRequest(BaseModel):
    baseline_id: str
    current_id: str


@app.get("/api/v1/system/doctor")
async def system_doctor() -> dict[str, Any]:
    """Runs system diagnostics on server environment, configs, and browsers."""
    register_tech_checks()
    register_content_checks()
    register_geo_checks()
    register_live_checks()

    playwright_ok = False
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            b = await p.chromium.launch(headless=True)
            await b.close()
        playwright_ok = True
    except Exception:
        playwright_ok = False

    keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "PERPLEXITY_API_KEY"]
    configured_keys = [k for k in keys if os.getenv(k)]

    return {
        "status": "healthy",
        "version": auditiq.__version__,
        "python_version": sys.version.split()[0],
        "registered_checks_count": len(default_registry.get_checks()),
        "playwright_chromium_operational": playwright_ok,
        "configured_ai_keys": configured_keys,
    }


@app.post("/api/v1/audits")
async def create_audit(req: CreateAuditRequest) -> dict[str, Any]:
    """Starts a new background audit job."""
    layer_map = {
        "tech": AuditLayer.TECHNICAL,
        "content": AuditLayer.CONTENT,
        "geo": AuditLayer.GEO_READINESS,
        "live": AuditLayer.LIVE_VISIBILITY,
    }
    resolved_layers = [
        layer_map[layer_str.lower()] for layer_str in req.layers if layer_str.lower() in layer_map
    ]
    if not resolved_layers:
        resolved_layers = [AuditLayer.TECHNICAL]

    job_id = job_manager.start_job(
        target_url=req.url,
        brand_name=req.brand_name,
        layers=resolved_layers,
        max_pages=req.max_pages,
        max_depth=req.max_depth,
        mock_ai=req.mock_ai,
    )
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Audit job queued successfully.",
    }


@app.get("/api/v1/audits")
async def list_audits() -> dict[str, Any]:
    """Lists all active and completed audits."""
    return {"audits": job_manager.list_jobs()}


@app.get("/api/v1/audits/{job_id}")
async def get_audit(job_id: str) -> dict[str, Any]:
    """Retrieves current status and full record for an audit job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")

    return {
        "id": job.id,
        "url": job.url,
        "brand_name": job.brand_name,
        "status": job.status.value,
        "progress_pct": job.progress_pct,
        "message": job.message,
        "error": job.error,
        "record": job.record.model_dump() if job.record else None,
    }


@app.get("/api/v1/audits/{job_id}/stream")
async def stream_audit_progress(job_id: str) -> StreamingResponse:
    """Server-Sent Events (SSE) stream providing real-time crawl & evaluation updates."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        q = await job_manager.subscribe(job_id)
        # Yield initial state
        init_payload = {
            "status": job.status.value,
            "progress_pct": job.progress_pct,
            "message": job.message,
        }
        yield f"data: {json.dumps(init_payload)}\n\n"

        try:
            while True:
                data = await q.get()
                # Serialize status enum if present
                if "status" in data and hasattr(data["status"], "value"):
                    data["status"] = data["status"].value
                yield f"data: {json.dumps(data)}\n\n"
                if data.get("status") in ("completed", "failed") or data.get("progress_pct") == 100:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            await job_manager.unsubscribe(job_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/api/v1/audits/{job_id}/cancel")
async def cancel_audit_endpoint(job_id: str) -> dict[str, Any]:
    """Cancels an in-progress background audit job."""
    success = job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Audit cannot be cancelled (either not found or already finished)",
        )
    return {"status": "cancelled", "job_id": job_id}


@app.get("/api/v1/audits/{job_id}/report")
async def get_audit_report(job_id: str, format: str = "html") -> FileResponse:
    """Downloads or views the generated report (HTML, PDF, JSON, or CSV)."""
    job = job_manager.get_job(job_id)
    if not job or not job.record:
        raise HTTPException(status_code=404, detail="Audit record not found or not completed")

    if format.lower() == "pdf":
        pdf_path = job_manager.reports_dir / f"report_{job_id}.pdf"
        if not pdf_path.exists():
            await generate_pdf_report_async(job.record, output_path=pdf_path)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"auditiq_report_{job_id}.pdf",
        )

    if format.lower() == "json":
        from auditiq.reports.exporters import export_json

        json_path = job_manager.reports_dir / f"audit_{job_id}.json"
        if not json_path.exists():
            export_json(job.record, output_path=json_path)
        return FileResponse(
            json_path,
            media_type="application/json",
            filename=f"auditiq_record_{job_id}.json",
        )

    if format.lower() == "csv":
        from auditiq.reports.exporters import export_csv

        csv_path = job_manager.reports_dir / f"findings_{job_id}.csv"
        if not csv_path.exists():
            export_csv(job.record, output_path=csv_path)
        return FileResponse(
            csv_path,
            media_type="text/csv",
            filename=f"auditiq_findings_{job_id}.csv",
        )

    html_path = job_manager.reports_dir / f"report_{job_id}.html"
    if not html_path.exists():
        from auditiq.reports.html import generate_html_report

        generate_html_report(job.record, output_path=html_path)

    return FileResponse(html_path, media_type="text/html")


@app.get("/api/v1/audits/{job_id}/badge.svg", response_class=Response)
async def get_audit_badge(job_id: str) -> Response:
    """Generates an embeddable SVG badge indicating AuditIQ score and grade."""
    job = job_manager.get_job(job_id)
    if not job or not job.record or not job.record.score_card:
        raise HTTPException(status_code=404, detail="Audit record not found or not completed")

    sc = job.record.score_card
    grade = sc.letter_grade
    score = round(sc.composite_score, 1)

    color_map = {
        "A": "#30D158",
        "B": "#0A84FF",
        "C": "#64D2FF",
        "D": "#FF9F0A",
        "F": "#FF453A",
    }
    badge_color = color_map.get(grade, "#8E8E93")

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="168" height="28" role="img" aria-label="AuditIQ: Grade {grade} ({score}/100)">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#fff" stop-opacity=".12"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="168" height="28" rx="6" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="84" height="28" fill="#1C1C1E"/>
    <rect x="84" width="84" height="28" fill="{badge_color}"/>
    <rect width="168" height="28" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" text-rendering="geometricPrecision" font-size="12">
    <text x="42" y="18" font-weight="700" fill="#fff">AuditIQ</text>
    <text x="126" y="18" font-weight="800" fill="#fff">Grade {grade} · {score}</text>
  </g>
</svg>"""
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/api/v1/audits/{job_id}/bundle.zip")
async def get_audit_bundle(job_id: str) -> FileResponse:
    """Packages HTML, PDF, CSV, and JSON audit artifacts into a single downloadable ZIP archive."""
    import zipfile

    job = job_manager.get_job(job_id)
    if not job or not job.record:
        raise HTTPException(status_code=404, detail="Audit record not found or not completed")

    zip_path = job_manager.reports_dir / f"bundle_{job_id}.zip"
    html_path = job_manager.reports_dir / f"report_{job_id}.html"
    pdf_path = job_manager.reports_dir / f"report_{job_id}.pdf"
    csv_path = job_manager.reports_dir / f"findings_{job_id}.csv"
    json_path = job_manager.reports_dir / f"audit_{job_id}.json"

    if not html_path.exists():
        from auditiq.reports.html import generate_html_report

        generate_html_report(job.record, output_path=html_path)
    if not pdf_path.exists():
        await generate_pdf_report_async(job.record, output_path=pdf_path)
    if not csv_path.exists():
        from auditiq.reports.exporters import export_csv

        export_csv(job.record, output_path=csv_path)
    if not json_path.exists():
        from auditiq.reports.exporters import export_json

        export_json(job.record, output_path=json_path)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if html_path.exists():
            zf.write(html_path, arcname=f"report_{job_id}.html")
        if pdf_path.exists():
            zf.write(pdf_path, arcname=f"report_{job_id}.pdf")
        if csv_path.exists():
            zf.write(csv_path, arcname=f"findings_{job_id}.csv")
        if json_path.exists():
            zf.write(json_path, arcname=f"audit_{job_id}.json")

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"auditiq_bundle_{job_id}.zip",
    )


@app.post("/api/v1/compare")
async def compare_audits_endpoint(req: CompareRequest) -> dict[str, Any]:
    """Compares two historical audits and returns score and finding regressions."""
    job_a = job_manager.get_job(req.baseline_id)
    job_b = job_manager.get_job(req.current_id)

    if not job_a or not job_a.record:
        raise HTTPException(status_code=404, detail=f"Baseline audit {req.baseline_id} not found")
    if not job_b or not job_b.record:
        raise HTTPException(status_code=404, detail=f"Current audit {req.current_id} not found")

    cmp = compare_audits(job_a.record, job_b.record)
    return cmp.model_dump()


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard() -> HTMLResponse:
    """Serves the interactive web dashboard SPA."""
    index_path = Path(__file__).parent / "static" / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>AuditIQ Dashboard</h1><p>Static index.html not found.</p>")
