"""Normalise typographic Unicode that LLMs like to emit (non-breaking hyphens, thin spaces, ...).

Browsers render these fine, but the PDF's built-in Helvetica only covers cp1252 and draws
anything else as a black box. ATS forms and plain-text emails also mangle them.
"""

import re
import unicodedata

_REPLACEMENTS = {
    # hyphens and minus signs -> ASCII hyphen
    "‐": "-", "‑": "-", "‒": "-", "⁃": "-", "−": "-", "﹣": "-", "－": "-",
    # dashes we keep as real dashes (they exist in cp1252)
    "–": "–", "—": "—", "―": "—",
    # odd spaces -> normal space
    " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", " ": " ",
    " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", "　": " ",
    # invisible characters -> nothing
    "​": "", "‌": "", "‍": "", "⁠": "", "﻿": "", "­": "",
    # quotes and primes
    "′": "'", "″": '"', "‛": "'", "‟": '"',
    # arrows and checkmarks sometimes used in bullets
    "→": "->", "←": "<-", "↔": "<->", "✓": "", "✔": "",
}
_TABLE = str.maketrans(_REPLACEMENTS)
_MULTI_SPACE = re.compile(r"[ \t]{2,}")


def normalize_text(text: str) -> str:
    """Replace typographic look-alikes with plain characters. Safe to run on any user-facing text."""
    return _MULTI_SPACE.sub(" ", text.translate(_TABLE))


def pdf_safe(text: str) -> str:
    """`normalize_text`, then make sure every character exists in cp1252 (the PDF font's range)."""
    out: list[str] = []
    for char in normalize_text(text):
        try:
            char.encode("cp1252")
            out.append(char)
        except UnicodeEncodeError:
            # Try a plain-letter fallback (e.g. "ł" -> "l"); otherwise drop the character.
            folded = unicodedata.normalize("NFKD", char).encode("cp1252", "ignore").decode("cp1252")
            out.append(folded)
    return "".join(out)
