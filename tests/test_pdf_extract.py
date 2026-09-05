from election_data_grabber.adapters.pdf_extract import (
    PdfExtractionResult,
    PdfPageText,
    looks_like_ohio_precinct_report,
    pdf_needs_fallback,
)


def test_ohio_family_detector():
    text = "Precinct ATH 1 Registered Voters 1200 Ballots Cast 650 Turnout 54.2%"
    assert looks_like_ohio_precinct_report(text)


def test_low_confidence_requires_fallback():
    result = PdfExtractionResult(
        pages=[PdfPageText(page_number=1, text="", text_chars=0)],
        method="pypdf_embedded_text",
        confidence="low",
        warnings=["very_little_embedded_text"],
    )
    assert pdf_needs_fallback(result)


def test_medium_confidence_does_not_force_fallback():
    result = PdfExtractionResult(
        pages=[PdfPageText(page_number=1, text="x" * 500, text_chars=500)],
        method="pypdf_embedded_text",
        confidence="medium",
    )
    assert not pdf_needs_fallback(result)
