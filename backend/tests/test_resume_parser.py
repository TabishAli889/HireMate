"""PDF validation and text extraction."""

import pytest

from app.core.exceptions import FileTooLargeError, InvalidFileError
from app.services.resume_parser import extract_pdf_text, validate_pdf
from tests.conftest import make_pdf

MB = 1024 * 1024
RESUME_LINE = "Sara Ahmed - Python developer - FastAPI, SQL, Docker - Lahore"


def test_valid_pdf_passes() -> None:
    validate_pdf("cv.PDF", make_pdf(RESUME_LINE), 5 * MB)


@pytest.mark.parametrize("name", ["cv.docx", "cv.txt", "", None])
def test_non_pdf_extension_rejected(name: str | None) -> None:
    with pytest.raises(InvalidFileError):
        validate_pdf(name, make_pdf(RESUME_LINE), 5 * MB)


def test_fake_pdf_rejected_by_magic_bytes() -> None:
    with pytest.raises(InvalidFileError):
        validate_pdf("cv.pdf", b"PK\x03\x04 this is a zip", 5 * MB)


def test_too_large_rejected() -> None:
    with pytest.raises(FileTooLargeError):
        validate_pdf("cv.pdf", b"%PDF-" + b"0" * (5 * MB), 5 * MB)


def test_empty_rejected() -> None:
    with pytest.raises(InvalidFileError):
        validate_pdf("cv.pdf", b"", 5 * MB)


def test_extracts_text() -> None:
    assert "FastAPI" in extract_pdf_text(make_pdf(RESUME_LINE))


def test_pdf_without_text_rejected() -> None:
    with pytest.raises(InvalidFileError, match="scanned"):
        extract_pdf_text(make_pdf(""))


def test_corrupt_pdf_rejected() -> None:
    with pytest.raises(InvalidFileError):
        extract_pdf_text(b"%PDF-1.4\ngarbage that is not a pdf")
