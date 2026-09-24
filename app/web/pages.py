"""The browser UI: one page (Jinja2) plus its static JavaScript and CSS."""

from flask import Blueprint, Response, current_app, render_template

from app.config import Settings
from app.web.routes import MAX_FILES_PER_UPLOAD

ui = Blueprint("ui", __name__, template_folder="templates", static_folder="static", static_url_path="/assets")

# Pinned version + Subresource Integrity: the browser refuses the file if the CDN ever serves other bytes.
CHART_JS = {
    "src": "https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js",
    "integrity": "sha384-jb8JQMbMoBUzgWatfe6COACi2ljcDdZQ2OxczGA3bGNeWe+6DChMTBJemed7ZnvJ",
}

# Only our own files and the pinned CDN may run; no inline scripts, no framing, no foreign requests.
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' https://cdn.jsdelivr.net",
        "style-src 'self'",
        "img-src 'self' data: blob:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)


@ui.get("/")
def index() -> str:
    settings: Settings = current_app.extensions["settings"]
    return render_template(
        "index.html",
        chart_js=CHART_JS,
        max_files=MAX_FILES_PER_UPLOAD,
        max_upload_mb=settings.max_upload_mb,
        result_ttl_minutes=settings.result_ttl_seconds // 60,
    )


def add_security_headers(response: Response) -> Response:
    response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")  # no MIME sniffing of downloads
    response.headers.setdefault("Referrer-Policy", "no-referrer")  # task ids never leak via the Referer header
    response.headers.setdefault("X-Frame-Options", "DENY")  # older browsers' version of frame-ancestors
    return response
