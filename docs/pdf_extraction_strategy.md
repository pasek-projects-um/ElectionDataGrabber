# PDF extraction strategy

Election-result PDFs range from clean born-digital tables to scanned canvass books and visually complex multi-column reports. The ingest contract should not depend on any one PDF library or assume that text order equals visual/table order.

## Escalation ladder

1. Preserve the raw PDF immutably with hash/provenance.
2. Extract embedded text page-by-page with `pypdf`.
3. If confidence is adequate, run source-family text/table normalization.
4. Where useful, try a table-aware extractor such as `pdfplumber` as an optional enhancement.
5. If embedded text is sparse or absent, mark the artifact as needing OCR rather than silently returning empty structured data.
6. For unusually complex layouts, allow a source profile to specify page regions, repeated headers, column geometry, or other layout hints.
7. Keep manual/source-specific recovery as a last resort and preserve parser version + warnings.

## Reliability rules

- Never infer ballot order from PDF results-column order without an authoritative ballot/rotation source.
- Never discard raw text merely because structured parsing failed.
- Keep page number and extraction warnings so parsed observations can be traced back to the source page.
- Treat OCR output as lower-confidence derived data unless verified against arithmetic/aggregation constraints.
- Cross-check candidate totals, ballots cast, registration, precinct totals, and higher-level aggregates whenever the PDF exposes them.

This design is intentionally suitable for difficult states and counties: irregular PDFs should trigger a richer extraction path, not require a new canonical data model.
