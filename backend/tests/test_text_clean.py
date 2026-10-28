from io import BytesIO

import pdfplumber

from app.schemas.profile import ProfileData
from app.services.pdf_export import render_letter_pdf
from app.services.text_clean import normalize_text, pdf_safe

LLM_TEXT = "end‑to‑end LLM‑powered app, 5 users – Retrieval‐Augmented​"


def test_normalize_replaces_typographic_hyphens_and_spaces():
    assert normalize_text(LLM_TEXT) == "end-to-end LLM-powered app, 5 users – Retrieval-Augmented"


def test_pdf_safe_only_keeps_cp1252_characters():
    cleaned = pdf_safe(LLM_TEXT + " łódź ★")
    cleaned.encode("cp1252")  # must not raise
    assert "end-to-end" in cleaned
    assert "ó" in cleaned  # characters the font has are kept


def test_letter_pdf_has_no_missing_glyphs():
    body = f"Dear Hiring Team,\n\nI built {LLM_TEXT}.\n\nSincerely,\nSam"
    pdf = render_letter_pdf(ProfileData(full_name="Sam"), body)
    with pdfplumber.open(BytesIO(pdf)) as doc:
        text = "\n".join(page.extract_text() or "" for page in doc.pages)
    assert "end-to-end" in text
    assert "LLM-powered" in text
    assert "■" not in text
