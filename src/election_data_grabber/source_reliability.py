"""Persist verified election-result source identities across intermittent audit failures.

A transient unsuccessful observation never revokes an earlier verified source.
Current reachability and historical evidence are separate dimensions.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        raise ValueError("source must have an absolute HTTP(S) URL")
    if parts.username or parts.password or any(ch.isspace() for ch in parts.netloc):
        raise ValueError("source URL contains credentials or invalid host")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def merge_source_observation(
    previous: dict | None, *, jurisdiction_id: str, source_url: str,
    verified: bool, observed_at: str, failure_class: str = "",
) -> dict:
    """Merge an observation without promoting unverified sources to coverage."""
    if not jurisdiction_id:
        raise ValueError("jurisdiction_id is required")
    checked = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    if checked.tzinfo is None:
        raise ValueError("observation timestamp must include timezone")
    observed_at = checked.astimezone(timezone.utc).isoformat()
    url = canonical_url(source_url)
    if previous and (previous["jurisdiction_id"], previous["source_url"]) != (jurisdiction_id, url):
        raise ValueError("cannot merge different source identities")
    if previous:
        last = datetime.fromisoformat(previous["last_checked_at"].replace("Z", "+00:00"))
        if checked < last:
            raise ValueError("out-of-order source observation")
    if verified and failure_class:
        raise ValueError("verified observation cannot have failure_class")
    if not verified and not failure_class:
        raise ValueError("unverified observation requires failure_class")
    return {
        "jurisdiction_id": jurisdiction_id,
        "source_url": url,
        "ever_verified": bool(verified or (previous and previous["ever_verified"])),
        "first_verified_at": (
            (previous or {}).get("first_verified_at") or (observed_at if verified else "")
        ),
        "last_verified_at": (
            observed_at if verified else (previous or {}).get("last_verified_at", "")
        ),
        "last_checked_at": observed_at,
        "currently_reachable": bool(verified),
        "last_failure_class": "" if verified else failure_class,
    }


def load_ledger(path: Path) -> dict[tuple[str, str], dict]:
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("ledger must be a JSON array")
    ledger = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("ever_verified"), bool):
            raise ValueError("invalid ledger row")
        key = (row["jurisdiction_id"], canonical_url(row["source_url"]))
        if key in ledger:
            raise ValueError("duplicate source identity")
        ledger[key] = row
    return ledger


def save_ledger(path: Path, ledger: dict[tuple[str, str], dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps([ledger[k] for k in sorted(ledger)], indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
