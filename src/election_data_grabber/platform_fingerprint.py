from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse


@dataclass(frozen=True, slots=True)
class PlatformFingerprint:
    family: str
    confidence: str
    evidence: tuple[str, ...]
    discovered_artifacts: tuple[str, ...] = ()


SIGNATURES = (
    ("enhanced_voting", ("enhancedvoting", "enhanced voting")),
    ("clarity", ("clarityelections", "election night reporting", "enrresults")),
    ("scytl", ("scytl",)),
    ("electionware", ("electionware",)),
)


def fingerprint_result_surface(url: str, text: str) -> PlatformFingerprint:
    blob = (url + "\n" + text[:500000]).lower()
    evidence: list[str] = []
    family = "unknown_web"

    for candidate, tokens in SIGNATURES:
        hits = [token for token in tokens if token in blob]
        if hits:
            family = candidate
            evidence.extend(f"signature:{token}" for token in hits)
            break

    artifacts = []
    for match in re.findall(r'''(?:href|src)\s*=\s*["']([^"']+)["']''', text, flags=re.I):
        absolute = urljoin(url, match)
        lower = absolute.lower()
        if any(token in lower for token in (".csv", ".json", ".xml", ".zip", ".xls", ".xlsx")):
            artifacts.append(absolute)

    api_clues = []
    for pattern in (r'''https?://[^"'\s<>]+/api/[^"'\s<>]+''', r'''fetch\(["']([^"']+)["']'''):
        for match in re.findall(pattern, text, flags=re.I):
            value = match if isinstance(match, str) else match[0]
            api_clues.append(urljoin(url, value))

    if artifacts:
        evidence.append(f"download_artifacts:{len(set(artifacts))}")
    if api_clues:
        evidence.append(f"api_clues:{len(set(api_clues))}")

    host = (urlparse(url).hostname or "").lower()
    if family == "unknown_web" and (artifacts or api_clues):
        family = "structured_web"
    if host.endswith(".gov"):
        evidence.append("official_host")

    confidence = "high" if any(item.startswith("signature:") for item in evidence) else ("medium" if artifacts or api_clues else "low")
    discovered = tuple(sorted(set(artifacts + api_clues)))
    return PlatformFingerprint(
        family=family,
        confidence=confidence,
        evidence=tuple(evidence),
        discovered_artifacts=discovered,
    )
