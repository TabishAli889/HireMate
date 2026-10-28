"""URL safety checks and job-text extraction (no network needed)."""

import json

import pytest

from app.services import job_scraper
from app.services.job_scraper import ScrapeError, extract_job_text, validate_public_url

LONG_DESCRIPTION = "<p>We are hiring a Python intern.</p><ul>" + "<li>Build FastAPI services and write tests</li>" * 8 + "</ul>"


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/job",
        "http://localhost:8000/admin",
        "http://127.0.0.1/",
        "http://10.0.0.5/jobs",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/",
    ],
)
def test_unsafe_urls_are_rejected(url: str) -> None:
    with pytest.raises(ScrapeError):
        validate_public_url(url)


def test_json_ld_job_posting_is_preferred() -> None:
    ld = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": "AI Intern",
        "hiringOrganization": {"@type": "Organization", "name": "Nimbus"},
        "jobLocation": {"@type": "Place", "address": {"addressLocality": "Lahore", "addressCountry": "PK"}},
        "employmentType": "INTERN",
        "description": LONG_DESCRIPTION,
    }
    html = f"""<html><body><nav>Menu Login</nav>
        <script type="application/ld+json">{json.dumps({"@graph": [ld]})}</script>
        <main>Other page text</main></body></html>"""
    text = extract_job_text(html)
    assert text.startswith("Title: AI Intern")
    assert "Company: Nimbus" in text
    assert "Lahore, PK" in text
    assert "Build FastAPI services" in text
    assert "Menu" not in text


def test_main_content_fallback_strips_noise() -> None:
    html = """<html><head><style>.x{}</style></head><body>
        <nav>Home Jobs Login</nav><script>track()</script>
        <main><h1>Junior Data Analyst</h1><p>Use SQL   and   Python.</p></main>
        <footer>Copyright</footer></body></html>"""
    text = extract_job_text(html)
    assert "Junior Data Analyst" in text
    assert "Use SQL and Python." in text
    assert "Login" not in text and "track" not in text and "Copyright" not in text


def test_too_little_text_asks_user_to_paste(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(job_scraper, "fetch_html", lambda url: "<html><body><main>Sign in to view</main></body></html>")
    with pytest.raises(ScrapeError, match="paste the job text"):
        job_scraper.scrape_job_url("https://example.com/job/1")
