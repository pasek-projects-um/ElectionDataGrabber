from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
import re

from pypdf import PdfReader


@dataclass(slots=True)
class PdfPageText:
    page_number: int
    text: str
    text_chars: int


@dataclass(slots=True)
class PdfExtractionResult:
    pages: list[PdfPageText]
    method: str
    confidence: str
    warnings: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)


def extract_pdf_text(body: bytes) -> PdfExtractionResult:
    """Extract embedded PDF text while preserving uncertainty metadata.

    This is intentionally conservative. It does not OCR image-only PDFs and it
    does not claim tabular structure merely because whitespace resembles columns.
    Consumers should retain the raw PDF and treat warnings/confidence as part of
    provenance.
    """
    reader = PdfReader(BytesIO(body))
    pages: list[PdfPageText] = []
    warnings: list[str] = []

    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # malformed PDFs should degrade, not destroy ingest
            text = ""
            warnings.append(f"page_{i}_extract_error:{type(exc).__name__}")
        pages.append(PdfPageText(i, text, len(text.strip())))

    total_chars = sum(p.text_chars for p in pages)
    empty_pages = sum(1 for p in pages if p.text_chars < 20)
    if not pages:
        confidence = "none"
        warnings.append("no_pages")
    elif total_chars < 100:
        confidence = "low"
        warnings.append("very_little_embedded_text")
    elif empty_pages / len(pages) > 0.4:
        confidence = "low"
        warnings.append("many_pages_without_embedded_text")
    else:
        confidence = "medium"

    return PdfExtractionResult(
        pages=pages,
        method="pypdf_embedded_text",
        confidence=confidence,
        warnings=warnings,
    )


def looks_like_ohio_precinct_report(text: str) -> bool:
    """Loose family detector for common Ohio precinct-detail/SOV PDFs."""
    blob = re.sub(r"\s+", " ", text).lower()
    signals = [
        "precinct",
        "registered voters",
        "ballots cast",
        "turnout",
    ]
    return sum(s in blob for s in signals) >= 3


def pdf_needs_fallback(result: PdfExtractionResult) -> bool:
    """True when a richer extractor/OCR/manual parser should be attempted."""
    return result.confidence in {"none", "low"}
