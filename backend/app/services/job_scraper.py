"""`scrape_job_url` tool: fetch a public job page safely and pull out the posting text.

Safety: http(s) only, every redirect hop re-checked, private/loopback/cloud-metadata addresses
blocked (SSRF), 2 MB size cap, 10 s timeout. Prefers schema.org JobPosting JSON-LD when present.
"""

import ipaddress
import json
import re
import socket
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.exceptions import AppError

MAX_BYTES = 2_000_000
TIMEOUT_SECONDS = 10.0
MAX_REDIRECTS = 4
MIN_TEXT_CHARS = 200
MAX_TEXT_CHARS = 20_000
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HireMate/0.3; job-posting reader)",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
}
_NOISE_TAGS = ["script", "style", "noscript", "svg", "nav", "header", "footer", "form", "iframe", "button"]


class ScrapeError(AppError):
    status_code = 422
    default_detail = "We couldn't read that job page. Please paste the job description text instead."


def validate_public_url(url: str) -> None:
    """Reject non-http(s) URLs and hosts that resolve to private or internal addresses."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ScrapeError("Only http:// or https:// job links are supported.")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(parsed.hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ScrapeError("We couldn't find that website. Check the link, or paste the job text instead.") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            raise ScrapeError("That link points to a private or local address, which isn't allowed.")


def fetch_html(url: str) -> str:
    """GET the page, following up to MAX_REDIRECTS redirects, each one re-validated."""
    current = url
    with httpx.Client(timeout=TIMEOUT_SECONDS, headers=HEADERS, follow_redirects=False) as client:
        for _ in range(MAX_REDIRECTS + 1):
            validate_public_url(current)
            try:
                with client.stream("GET", current) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise ScrapeError()
                        current = urljoin(current, location)
                        continue
                    if response.status_code in (401, 403, 429, 999):
                        raise ScrapeError(
                            "That site blocks automated readers or needs a login (LinkedIn does this). "
                            "Please paste the job text instead."
                        )
                    if response.status_code >= 400:
                        raise ScrapeError(
                            f"The job page returned an error ({response.status_code}). Please paste the job text instead."
                        )
                    content_type = response.headers.get("content-type", "")
                    if "html" not in content_type and "text" not in content_type:
                        raise ScrapeError("That link isn't a web page. Please paste the job text instead.")
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body += chunk
                        if len(body) > MAX_BYTES:
                            break
                    return bytes(body).decode(response.encoding or "utf-8", errors="replace")
            except httpx.HTTPError as exc:
                raise ScrapeError("We couldn't reach that page. Check the link, or paste the job text instead.") from exc
    raise ScrapeError("That link redirects too many times. Please paste the job text instead.")


def _clean_text(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    joined = "\n".join(line for line in lines if line)
    return re.sub(r"\n{3,}", "\n\n", joined).strip()


def _iter_ld_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for entry in data for item in _iter_ld_items(entry)]
    if isinstance(data, dict):
        return [data, *_iter_ld_items(data.get("@graph", []))]
    return []


def _is_job_posting(item: dict[str, Any]) -> bool:
    kind = item.get("@type")
    return kind == "JobPosting" or (isinstance(kind, list) and "JobPosting" in kind)


def _job_posting_from_json_ld(soup: BeautifulSoup) -> str | None:
    """Readable text from a schema.org JobPosting block, if the page has one."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for item in _iter_ld_items(data):
            if not _is_job_posting(item):
                continue
            description = BeautifulSoup(str(item.get("description", "")), "html.parser").get_text("\n")
            if len(description.strip()) < 100:
                continue
            org = item.get("hiringOrganization")
            company = org.get("name", "") if isinstance(org, dict) else ""
            locations = item.get("jobLocation")
            locations = locations if isinstance(locations, list) else [locations]
            places = []
            for loc in locations:
                address = loc.get("address", {}) if isinstance(loc, dict) else {}
                if isinstance(address, dict):
                    places.append(", ".join(str(address[k]) for k in ("addressLocality", "addressCountry") if address.get(k)))
            header = [
                f"Title: {item.get('title', '')}",
                f"Company: {company}",
                f"Location: {'; '.join(p for p in places if p)}",
                f"Employment type: {item.get('employmentType', '')}",
            ]
            return _clean_text("\n".join(header) + "\n\n" + description)
    return None


def extract_job_text(html: str) -> str:
    """Best-effort job text: JSON-LD JobPosting first, else the page's main content."""
    soup = BeautifulSoup(html, "html.parser")
    posting = _job_posting_from_json_ld(soup)
    if posting:
        return posting
    for tag in soup(_NOISE_TAGS):
        tag.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    return _clean_text(root.get_text("\n"))


def scrape_job_url(url: str) -> str:
    """Fetch `url` and return the job posting text, or raise ScrapeError with a 'paste instead' hint."""
    text = extract_job_text(fetch_html(url))
    if len(text) < MIN_TEXT_CHARS:
        raise ScrapeError(
            "We couldn't find a job description on that page (it may need a login or load with JavaScript). "
            "Please paste the job text instead."
        )
    return text[:MAX_TEXT_CHARS]
