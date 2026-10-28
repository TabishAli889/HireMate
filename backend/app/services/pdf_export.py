"""Clean, ATS-friendly PDFs with reportlab (pure Python, no system dependencies)."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

from app.schemas.profile import ProfileData
from app.services.text_clean import pdf_safe

ACCENT = colors.HexColor("#4338CA")
MUTED = colors.HexColor("#555B6E")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["Normal"]
    return {
        "name": ParagraphStyle("name", parent=base, fontName="Helvetica-Bold", fontSize=18, leading=22, alignment=TA_LEFT),
        "headline": ParagraphStyle("headline", parent=base, fontSize=10.5, leading=14, textColor=MUTED),
        "contact": ParagraphStyle("contact", parent=base, fontSize=9, leading=12, textColor=MUTED),
        "section": ParagraphStyle(
            "section", parent=base, fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=ACCENT, spaceBefore=10
        ),
        "item": ParagraphStyle("item", parent=base, fontName="Helvetica-Bold", fontSize=10, leading=13, spaceBefore=4),
        "meta": ParagraphStyle("meta", parent=base, fontSize=9, leading=12, textColor=MUTED),
        "body": ParagraphStyle("body", parent=base, fontSize=10, leading=13.5),
        "bullet": ParagraphStyle("bullet", parent=base, fontSize=9.5, leading=13),
        "letter": ParagraphStyle("letter", parent=base, fontSize=11, leading=16, spaceAfter=10),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(pdf_safe(text)), style)


def _bullets(items: list[str], style: ParagraphStyle) -> ListFlowable:
    return ListFlowable(
        [ListItem(_p(item, style), leftIndent=10) for item in items if item.strip()],
        bulletType="bullet",
        start="•",
        leftIndent=10,
        bulletFontSize=8,
    )


def _document(buffer: BytesIO, title: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm, title=title
    )


def render_resume_pdf(profile: ProfileData) -> bytes:
    """One-column resume from a (possibly tailored) profile."""
    s = _styles()
    story: list = [_p(profile.full_name or "Your name", s["name"])]
    if profile.headline:
        story.append(_p(profile.headline, s["headline"]))
    contact = " · ".join(part for part in (profile.email, profile.phone, profile.location, *profile.links) if part)
    if contact:
        story.append(_p(contact, s["contact"]))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=0.6, color=ACCENT))

    def section(title: str) -> None:
        story.append(_p(title.upper(), s["section"]))

    if profile.summary:
        section("Summary")
        story.append(_p(profile.summary, s["body"]))
    if profile.skills:
        section("Skills")
        story.append(_p(", ".join(profile.skills), s["body"]))
    if profile.experience:
        section("Experience")
        for job in profile.experience:
            story.append(_p(" — ".join(part for part in (job.title, job.company) if part), s["item"]))
            meta = " · ".join(part for part in (job.location, " – ".join(d for d in (job.start_date, job.end_date) if d)) if part)
            if meta:
                story.append(_p(meta, s["meta"]))
            if job.bullets:
                story.append(_bullets(job.bullets, s["bullet"]))
    if profile.projects:
        section("Projects")
        for project in profile.projects:
            story.append(_p(project.name, s["item"]))
            meta = " · ".join(part for part in (", ".join(project.tech_stack), project.link) if part)
            if meta:
                story.append(_p(meta, s["meta"]))
            if project.description:
                story.append(_p(project.description, s["body"]))
            if project.bullets:
                story.append(_bullets(project.bullets, s["bullet"]))
    if profile.education:
        section("Education")
        for edu in profile.education:
            story.append(_p(" — ".join(part for part in (edu.degree, edu.institution) if part), s["item"]))
            meta = " · ".join(part for part in (edu.field_of_study, " – ".join(d for d in (edu.start_date, edu.end_date) if d)) if part)
            if meta:
                story.append(_p(meta, s["meta"]))
            if edu.details:
                story.append(_p(edu.details, s["body"]))

    buffer = BytesIO()
    _document(buffer, f"{profile.full_name or 'Resume'} — Resume").build(story)
    return buffer.getvalue()


def render_letter_pdf(profile: ProfileData, body: str) -> bytes:
    """Cover letter with a simple contact header."""
    s = _styles()
    story: list = [_p(profile.full_name or "Your name", s["name"])]
    contact = " · ".join(part for part in (profile.email, profile.phone, profile.location) if part)
    if contact:
        story.append(_p(contact, s["contact"]))
    story += [Spacer(1, 4), HRFlowable(width="100%", thickness=0.6, color=ACCENT), Spacer(1, 12)]
    for paragraph in body.split("\n\n"):
        if paragraph.strip():
            story.append(Paragraph(escape(pdf_safe(paragraph.strip())).replace("\n", "<br/>"), s["letter"]))
    buffer = BytesIO()
    _document(buffer, f"{profile.full_name or 'Cover letter'} — Cover letter").build(story)
    return buffer.getvalue()
