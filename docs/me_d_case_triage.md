# Maine provisional-D triage

The first statewide audit produced 12 locality-level D classifications in its shard summaries, but artifact-level inspection shows the D bucket is contaminated by discovery false positives and contains 24 localities with at least one D artifact.

Observed families:

1. **Scanned/image PDFs that appear to be actual results**: Caribou, Dayton, Lyman, Dedham. These are legitimate OCR/image-table fallback candidates.
2. **Election-adjacent PDFs incorrectly treated as results**: Farmington absentee-ballot application and Lyman absentee-request document. These are discovery false positives, not D extraction.
3. **Generic municipal search pages / FAQ / news pages**: Brunswick, Kittery, Brewer, Casco, Hebron, Damariscotta, Wiscasset and similar. These are source-classification failures, not D parsers.
4. **State absentee-ballot request service links**: Rockport, Arundel, Pownal, Deer Isle, Montville, Milbridge, Greenwood. These must be rejected as non-result artifacts.
5. **Potential dynamic document systems**: Rockland and Brunswick Tyler Portico/Navigator links. These need platform fingerprinting before portability classification.
6. **Potential genuine HTML result pages**: Boothbay Harbor and a small set of municipal article/result pages. These need semantic extraction rather than table-only detection.

Therefore provisional D must not be interpreted as 12 bespoke parser cases. Re-run after stricter result-artifact filtering, then classify only actual result artifacts.
