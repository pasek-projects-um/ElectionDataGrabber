"""Conservative source clues; format and date never establish live updates."""

import re
from urllib.parse import unquote, urlsplit

CONTEXT_FIELDS = ("election_context", "election_year_clues", "source_format", "update_evidence")


def source_context(url, label="", *, election_year=2026):
    path = unquote(urlsplit(url).path).casefold()
    text = unquote(url) + " " + label
    years = sorted({int(y) for y in re.findall(r"(?<!\d)(20\d{2})(?!\d)", text)})
    archive = bool(re.search(r"\b(?:archive|archived|historical|past elections)\b|resultsarchive",
                             text, re.IGNORECASE))
    if archive or (years and all(y < election_year for y in years)):
        context = "historical"
    elif years == [election_year]:
        context = "current_year_candidate"
    elif years:
        context = "mixed_or_other_years"
    else:
        context = "unknown"
    suffix = path.rsplit(".", 1)[-1]
    formats = {"pdf": "pdf", "csv": "csv", "tsv": "tsv", "xls": "spreadsheet",
               "xlsx": "spreadsheet", "json": "json", "xml": "xml",
               "html": "html", "htm": "html", "aspx": "html", "php": "html"}
    return {"election_context": context, "election_year_clues": " | ".join(map(str, years)),
            "source_format": formats.get(suffix, "unknown"), "update_evidence": "unknown"}
