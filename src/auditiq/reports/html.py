"""HTML Report Generator using Jinja2 and White-Label Branding."""

from pathlib import Path

import jinja2
import yaml

from auditiq.models.audit import AuditRecord


def load_branding_config(branding_path: Path | None = None) -> dict[str, object]:
    """Loads agency white-label styling config from YAML with safe defaults."""
    cfg_file = branding_path or Path("config/branding.yaml")
    if cfg_file.exists():
        try:
            with open(cfg_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass

    return {
        "agency": {
            "name": "AuditIQ Search Intelligence",
            "tagline": "Next-Generation Technical SEO & AI Search Visibility Audits",
            "website": "https://auditiq.local",
            "email": "contact@auditiq.local",
        },
        "colors": {
            "primary": "#1E293B",
            "secondary": "#0284C7",
            "accent": "#10B981",
            "warning": "#F59E0B",
            "danger": "#EF4444",
            "background": "#F8FAFC",
            "text": "#0F172A",
        },
        "typography": {
            "font_family": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
        },
        "report_settings": {
            "disclaimer": (
                "This audit is generated using rigorous statistical sampling and deterministic crawl heuristics. "
                "Search and AI engine results change dynamically over time."
            )
        },
    }


def generate_html_report(
    record: AuditRecord,
    output_path: Path | None = None,
    branding_path: Path | None = None,
) -> Path:
    """Renders a self-contained, agency-branded HTML audit report."""
    branding = load_branding_config(branding_path)

    templates_dir = Path(__file__).parent / "templates"
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(templates_dir)),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
    )

    template = env.get_template("report.html.jinja2")
    rendered_html = template.render(record=record, branding=branding)

    out_file = output_path or Path(f"reports/report_{record.id}.html")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    return out_file
