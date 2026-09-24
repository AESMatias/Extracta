import re
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient
from pydantic import SecretStr

from app import create_app
from app.config import Settings
from app.web.pages import CHART_JS


@pytest.fixture
def client(tmp_path: Path) -> FlaskClient:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        gemini_api_key=SecretStr("test"),
        database_url=SecretStr("postgresql+psycopg://u:p@h:5432/d"),
        secret_key=SecretStr("k" * 32),
        upload_dir=tmp_path,
        max_upload_mb=25,
        result_ttl_seconds=1800,
    )
    app: Flask = create_app(settings)
    return app.test_client()


def test_home_page_renders_the_upload_form(client: FlaskClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    html = response.get_data(as_text=True)
    assert re.search(r'<input[^>]+type="file"[^>]+accept="application/pdf,\.pdf"[^>]+multiple', html)
    assert 'name="save_to_db" value="false" checked' in html  # ephemeral is the default, as in the API
    assert 'name="save_to_db" value="true"' in html
    assert 'id="results-body"' in html
    for fmt in ("csv", "xlsx", "json"):
        assert f'data-export-all="{fmt}"' in html


def test_limits_come_from_the_settings(client: FlaskClient) -> None:
    html = client.get("/").get_data(as_text=True)

    assert 'data-max-upload-mb="25"' in html
    assert 'data-max-files="50"' in html
    assert 'data-result-ttl-minutes="30"' in html
    assert "25 MB each" in html


def test_chart_js_is_pinned_and_integrity_checked(client: FlaskClient) -> None:
    html = client.get("/").get_data(as_text=True)

    assert CHART_JS["src"].startswith("https://cdn.jsdelivr.net/npm/chart.js@4.")
    assert f'src="{CHART_JS["src"]}"' in html
    assert f'integrity="{CHART_JS["integrity"]}"' in html  # the browser refuses a tampered file
    assert 'crossorigin="anonymous"' in html


def test_page_has_no_inline_scripts(client: FlaskClient) -> None:
    # The Content-Security-Policy forbids inline scripts, so every <script> must load a file.
    html = client.get("/").get_data(as_text=True)

    scripts = re.findall(r"<script\b[^>]*>", html)
    assert scripts
    assert all("src=" in tag for tag in scripts)
    assert "onclick=" not in html


@pytest.mark.parametrize("path", ["/", "/health"])
def test_security_headers_on_every_response(client: FlaskClient, path: str) -> None:
    headers = client.get(path).headers

    csp = headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self' https://cdn.jsdelivr.net" in csp
    assert "frame-ancestors 'none'" in csp
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"  # task ids never leak through the Referer header


@pytest.mark.parametrize(
    ("path", "mimetype"),
    [("/assets/app.js", "text/javascript"), ("/assets/app.css", "text/css")],
)
def test_static_files_are_served(client: FlaskClient, path: str, mimetype: str) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert response.mimetype == mimetype
    response.close()


def test_frontend_never_injects_html_from_documents() -> None:
    # Document data comes from PDFs and the LLM: it must be inserted as text, never as HTML.
    script = (Path(__file__).parents[1] / "app/web/static/app.js").read_text()

    assert "innerHTML" not in script
    assert "insertAdjacentHTML" not in script
    assert "eval(" not in script
