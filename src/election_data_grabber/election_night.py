"""Explicitly selected result feeds, immutable captures and transactional poll state.

Discovery candidates never enter this collector automatically. Successful polling
is operational evidence, not a certification of election or jurisdiction coverage.
"""

from __future__ import annotations

import csv
import fcntl
import hashlib
import io
import json
import re
import sqlite3
import time
from contextlib import closing, contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin, urlsplit
from xml.etree.ElementTree import ParseError
from zoneinfo import ZoneInfo

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from election_data_grabber.adapters.clarity_xml import parse_clarity_like_xml
from election_data_grabber.adapters.enhanced_voting import parse_enhanced_voting_html
from election_data_grabber.adapters.generic_csv import (
    COLUMN_ALIASES,
    VOTE_COLUMNS,
    parse_generic_precinct_csv,
)
from election_data_grabber.adapters.generic_json import parse_generic_results_json
from election_data_grabber.adapters.washtenaw import WashtenawAdapter
from election_data_grabber.discovery_publication import publishable_url
from election_data_grabber.discovery_watch import (
    HostDeferred,
    TimeBudgetExhausted,
    WatchFetcher,
)
from election_data_grabber.models import ResultObservation, Source, SourceKind
from election_data_grabber.national_discovery import RequestBudgetExhausted, normalize
from election_data_grabber.reporting_unit_identity import AdapterReportingContext, UnitType

PARSERS = {
    "csv": parse_generic_precinct_csv,
    "json": parse_generic_results_json,
    "clarity_xml": parse_clarity_like_xml,
    "enhanced_voting": parse_enhanced_voting_html,
}


@contextmanager
def collector_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another collector owns this state directory") from None
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(body):
    return hashlib.sha256(body).hexdigest()


class Feed(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
    state: str = Field(pattern=r"^[A-Z]{2}$")
    jurisdiction_id: str
    authority_id: str
    election_id: str = Field(min_length=1)
    url: str
    parser: Literal["csv", "json", "clarity_xml", "enhanced_voting", "washtenaw"]
    enabled: bool = False
    authority_evidence_url: str = ""
    election_evidence_url: str = ""
    reviewed_at: datetime | None = None
    interval_seconds: int = Field(default=60, ge=30, le=86400)
    stale_after_seconds: int = Field(default=300, ge=60, le=86400)
    update_semantics: Literal["cumulative", "incremental", "unknown"] = "unknown"
    required_text: str = ""
    source_timezone: str | None = None
    reporting_unit_name: str | None = None
    reporting_unit_type: Literal["county", "precinct", "municipality", "reporting_unit"] = (
        "reporting_unit"
    )

    @model_validator(mode="after")
    def validate_selection(self):
        if self.source_timezone:
            ZoneInfo(self.source_timezone)
        for url in (self.url, self.authority_evidence_url, self.election_evidence_url):
            if url and (not normalize(url) or not publishable_url(url)):
                raise ValueError("Feed/evidence URLs must be public HTTP(S) URLs without secrets")
        if not self.url:
            raise ValueError("Feed URL is required")
        if self.stale_after_seconds < self.interval_seconds:
            raise ValueError("Staleness threshold must be at least the polling interval")
        if self.enabled and (
            not self.authority_evidence_url
            or not self.election_evidence_url
            or not self.reviewed_at
            or self.reviewed_at.tzinfo is None
        ):
            raise ValueError("Enabled feeds require authority/election evidence and dated review")
        AdapterReportingContext(
            self.state,
            self.election_id,
            self.jurisdiction_id,
            self.authority_id,
            self.source_id,
            "election_night",
            "election-night",
            "0" * 64,
        )
        return self

    @property
    def identity(self):
        # URL and parser changes require a new baseline; list order never affects identity.
        return digest(encoded(self.model_dump(mode="json")))


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    election_id: str = Field(min_length=1)
    election_date: date
    feeds: list[Feed]

    @model_validator(mode="after")
    def validate_feeds(self):
        ids = [feed.source_id for feed in self.feeds]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate source_id")
        if any(feed.election_id != self.election_id for feed in self.feeds):
            raise ValueError("Feed election disagrees with manifest election")
        return self


def load_manifest(path):
    return Manifest.model_validate_json(Path(path).read_text())


class FeedFetcher(WatchFetcher):
    """Robots-aware bounded binary fetcher with explicit conditional requests."""

    def fetch_feed(self, url, validators):
        original = normalize(url)
        for _ in range(6):
            url = normalize(url)
            if not url or not publishable_url(url):
                raise ValueError("Unsafe redirect")
            self.before_request(url)
            if self.remaining <= 0:
                raise RequestBudgetExhausted()
            host = urlsplit(url).hostname
            self.wait_for_host(host)
            self.remaining -= 1
            self.requests += 1
            self.last[host] = time.monotonic()
            headers = validators if url == original else {}
            with self.client.stream("GET", url, headers=headers) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    url = urljoin(url, response.headers["location"])
                    continue
                if response.status_code != 304:
                    response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    self.check_budget()
                    body.extend(chunk)
                    if len(body) > self.max_bytes:
                        raise ValueError("Response exceeds byte budget")
                return (
                    response.status_code,
                    bytes(body),
                    str(response.url),
                    {
                        "etag": response.headers.get("etag", ""),
                        "last_modified": response.headers.get("last-modified", ""),
                        "content_type": response.headers.get("content-type", ""),
                    },
                )
        raise ValueError("Redirect limit")


def connect(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / "collector.sqlite3", timeout=0)
    db.row_factory = sqlite3.Row
    db.executescript("""
      CREATE TABLE IF NOT EXISTS feeds (
        source_id TEXT PRIMARY KEY, config TEXT NOT NULL, next_due REAL NOT NULL,
        last_success REAL, last_changed REAL, failures INTEGER NOT NULL DEFAULT 0,
        sample_path TEXT, latest_sample_path TEXT, status TEXT NOT NULL DEFAULT 'unpolled',
        etag TEXT NOT NULL DEFAULT '', last_modified TEXT NOT NULL DEFAULT ''
      );
      CREATE TABLE IF NOT EXISTS attempts (
        id INTEGER PRIMARY KEY, source_id TEXT NOT NULL, observed_at REAL NOT NULL,
        status TEXT NOT NULL, detail TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS refresh_reviews (
        id INTEGER PRIMARY KEY, source_id TEXT NOT NULL, config TEXT NOT NULL,
        old_sample TEXT NOT NULL, new_sample TEXT NOT NULL,
        reviewed_at TEXT NOT NULL, evidence_url TEXT NOT NULL, note TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS policy (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL);
    """)
    return db


def immutable(root, directory, body, suffix):
    relative = Path(directory) / (digest(body) + suffix)
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != body:
            raise ValueError("Immutable artifact content mismatch")
    else:
        # The process lock serializes writers. A crash leaves an unreferenced file, not state.
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(body)
        temporary.replace(path)
    return str(relative)


def validate_vote_payload(parser, payload):
    """Reject ambiguous partial parses instead of silently dropping malformed votes."""
    if parser == "csv":
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
        for raw in reader:
            if not any(raw.values()):
                continue
            if None in raw:
                raise ValueError("CSV row width disagrees with header")
            row = {key.strip().lower(): value for key, value in raw.items()}
            if not all(
                any(row.get(alias, "") for alias in COLUMN_ALIASES[field])
                for field in ("precinct", "contest", "candidate")
            ):
                raise ValueError("CSV contains an incomplete observation row")
            votes = [row[column] for column in VOTE_COLUMNS if row.get(column) not in (None, "")]
            if not votes or any(
                not re.fullmatch(r"-?[0-9][0-9,]*", value.strip()) for value in votes
            ):
                raise ValueError("CSV contains missing or non-integer vote counts")
    if parser == "json":
        if not isinstance(payload, dict) or not isinstance(payload.get("reporting_units"), list):
            raise ValueError("Unsupported JSON reporting-unit schema")
        for unit in payload["reporting_units"]:
            if not isinstance(unit, dict) or not isinstance(unit.get("contests"), list):
                raise TypeError("Invalid JSON reporting unit")
            for contest in unit["contests"]:
                if not isinstance(contest, dict) or not isinstance(contest.get("choices"), list):
                    raise TypeError("Invalid JSON contest")
                for choice in contest["choices"]:
                    if not isinstance(choice, dict):
                        raise TypeError("Invalid JSON choice")
                    value = choice.get("votes")
                    if (
                        isinstance(value, bool)
                        or not isinstance(value, (int, str))
                        or not re.fullmatch(r"-?[0-9]+", str(value).strip())
                    ):
                        raise ValueError("JSON requires explicit integer vote counts")


def parse_capture(feed, body, fetched_at):
    if feed.required_text and feed.required_text not in body.decode("utf-8", errors="replace"):
        raise ValueError("Required election/feed marker absent")
    context = AdapterReportingContext(
        feed.state,
        feed.election_id,
        feed.jurisdiction_id,
        feed.authority_id,
        feed.source_id,
        "election_night",
        "election-night",
        digest(body),
    )
    payload = json.loads(body) if feed.parser == "json" else body
    validate_vote_payload(feed.parser, payload)
    if feed.parser == "washtenaw":
        source = Source(
            source_id=feed.source_id,
            jurisdiction=feed.jurisdiction_id,
            state=feed.state,
            url=feed.url,
            kind=SourceKind.OFFICIAL_WEB,
        )
        rows = WashtenawAdapter(source, election_id=feed.election_id).parse(
            body, fetched_at=fetched_at, reporting_context=context
        )
    else:
        rows = PARSERS[feed.parser](
            payload,
            election_id=feed.election_id,
            jurisdiction_id=feed.jurisdiction_id,
            source_id=feed.source_id,
            fetched_at=fetched_at,
            reporting_context=context,
        )
    if feed.parser == "washtenaw" and feed.reporting_unit_name:
        for row in rows:
            row.reporting_unit_name = feed.reporting_unit_name
            row.reporting_unit_raw_name = feed.reporting_unit_name
            row.reporting_unit_id = context.unit_id(
                UnitType(feed.reporting_unit_type), feed.reporting_unit_name
            )
    if feed.source_timezone:
        for row in rows:
            if row.source_timestamp and row.source_timestamp.tzinfo is None:
                row.source_timestamp = row.source_timestamp.replace(
                    tzinfo=ZoneInfo(feed.source_timezone)
                )
    if not rows:
        raise ValueError("No normalized observations")
    keys = [observation_key(row) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate observation identity; ambiguous rows cannot be summed")
    if any(row.votes < 0 for row in rows):
        raise ValueError("Negative absolute vote count")
    return sorted((row.model_dump(mode="json") for row in rows), key=encoded)


def observation_key(row):
    if isinstance(row, ResultObservation):
        row = row.model_dump(mode="json")
    # Keep raw modes separate: two unmapped modes must never collapse to UNKNOWN.
    return tuple(
        row.get(key)
        for key in (
            "reporting_unit_id",
            "contest_name",
            "choice_name",
            "party",
            "vote_mode",
            "raw_vote_mode",
        )
    )


def compare(previous, current, semantics):
    old = {observation_key(row): row["votes"] for row in previous}
    new = {observation_key(row): row["votes"] for row in current}
    common = old.keys() & new.keys()
    return {
        "added_rows": len(new.keys() - old.keys()),
        "removed_rows": len(old.keys() - new.keys()),
        "changed_rows": sum(old[key] != new[key] for key in common),
        "decreased_rows": sum(new[key] < old[key] for key in common)
        if semantics == "cumulative"
        else 0,
        "common_rows": len(common),
    }


def read_sample(root, relative):
    content = (root / relative).read_bytes()
    if digest(content) != Path(relative).stem:
        raise ValueError("Sample digest mismatch")
    sample = json.loads(content)
    body = (root / sample["body_path"]).read_bytes()
    if digest(body) != sample["snapshot_sha256"]:
        raise ValueError("Snapshot digest mismatch")
    return sample, body


def replay_sample(root, relative):
    """Replay only preserved bytes with the original configuration and acquisition time."""
    sample, body = read_sample(Path(root), relative)
    rows = parse_capture(
        Feed.model_validate(sample["feed"]), body, datetime.fromisoformat(sample["fetched_at"])
    )
    if rows != sample["observations"]:
        raise ValueError("Replay differs from persisted normalized observations")
    return {
        "replay_match": True,
        "observations": len(rows),
        "snapshot_sha256": sample["snapshot_sha256"],
    }


def collect(manifest, root, *, fetch=None, now=None, time_budget=120, max_feeds=25):
    if time_budget < 1 or max_feeds < 1:
        raise ValueError("Positive time and feed budgets required")
    root = Path(root)
    clock = time.time if now is None else lambda: now
    now = clock()
    deadline = time.monotonic() + time_budget
    owned = fetch is None
    fetch = fetch or FeedFetcher(delay=1, max_bytes=10_000_000, max_requests=200)
    results = []
    stop_reason = "due_queue_complete"
    try:
        with collector_lock(root / "collector.lock"), closing(connect(root)) as db:
            if isinstance(fetch, FeedFetcher):
                fetch.deadline = deadline
                policy = db.execute("SELECT body FROM policy WHERE id=1").fetchone()
                if policy:
                    fetch.restore_policy(json.loads(policy["body"]))
            # Validate the entire manifest before writes. Disabled feeds are never queued.
            for feed in manifest.feeds:
                if not feed.enabled:
                    continue
                db.execute(
                    """INSERT INTO feeds(source_id,config,next_due) VALUES(?,?,0)
                              ON CONFLICT(source_id) DO UPDATE SET
                              next_due=CASE WHEN config!=excluded.config THEN 0 ELSE next_due END,
                              last_success=CASE WHEN config!=excluded.config THEN NULL ELSE last_success END,
                              sample_path=CASE WHEN config!=excluded.config THEN NULL ELSE sample_path END,
                              latest_sample_path=CASE WHEN config!=excluded.config THEN NULL ELSE latest_sample_path END,
                              status=CASE WHEN config!=excluded.config THEN 'unpolled' ELSE status END,
                              failures=CASE WHEN config!=excluded.config THEN 0 ELSE failures END,
                              last_changed=CASE WHEN config!=excluded.config THEN NULL ELSE last_changed END,
                              etag=CASE WHEN config!=excluded.config THEN '' ELSE etag END,
                              last_modified=CASE WHEN config!=excluded.config THEN '' ELSE last_modified END,
                              config=excluded.config""",
                    (feed.source_id, feed.identity),
                )
            db.commit()
            feeds = {feed.source_id: feed for feed in manifest.feeds if feed.enabled}
            due = [
                row
                for row in db.execute(
                    "SELECT * FROM feeds WHERE next_due<=? ORDER BY next_due,source_id", (now,)
                )
                if row["source_id"] in feeds
            ]
            for row in due[:max_feeds]:
                if time.monotonic() >= deadline:
                    stop_reason = "time_budget"
                    break
                feed = feeds[row["source_id"]]
                result = {"source_id": feed.source_id, "feed_config": feed.model_dump(mode="json")}
                try:
                    headers = {}
                    if row["etag"]:
                        headers["If-None-Match"] = row["etag"]
                    if row["last_modified"]:
                        headers["If-Modified-Since"] = row["last_modified"]
                    status, body, final_url, meta = fetch.fetch_feed(feed.url, headers)
                    previous = None
                    if row["sample_path"]:
                        previous, old_body = read_sample(root, row["sample_path"])
                    if status == 304:
                        if previous is None:
                            raise ValueError("304 without a preserved baseline")
                        body = old_body
                    elif status != 200:
                        raise ValueError("Expected a complete 200 or conditional 304 response")
                    body_path = immutable(root, "raw", body, ".bin")
                    result.update(
                        body_path=body_path, snapshot_sha256=digest(body), http_status=status
                    )
                    captured_at = clock()
                    timestamp = datetime.fromtimestamp(captured_at, UTC)
                    observations = parse_capture(feed, body, timestamp)
                    changes = compare(
                        previous["observations"] if previous else [],
                        observations,
                        feed.update_semantics,
                    )
                    warnings = []
                    if changes["removed_rows"]:
                        warnings.append("rows_disappeared")
                    if changes["decreased_rows"]:
                        warnings.append("cumulative_votes_decreased")
                    if previous and not changes["common_rows"]:
                        warnings.append("identity_discontinuity")
                    sample = {
                        "feed": feed.model_dump(mode="json"),
                        "fetched_at": timestamp.isoformat(),
                        "final_url": final_url,
                        "http_status": status,
                        "response": meta,
                        "snapshot_sha256": digest(body),
                        "body_path": body_path,
                        "observations": observations,
                        "changes": changes,
                        "warnings": warnings,
                    }
                    # Prove replay before advancing the successful baseline.
                    if (
                        parse_capture(feed, (root / body_path).read_bytes(), timestamp)
                        != observations
                    ):
                        raise ValueError("Non-deterministic parser replay")
                    sample_path = (
                        row["sample_path"]
                        if previous and previous["snapshot_sha256"] == digest(body)
                        else immutable(root, "samples", encoded(sample), ".json")
                    )
                    capture = {
                        key: value
                        for key, value in sample.items()
                        if key not in ("observations", "feed")
                    }
                    capture["sample_path"] = sample_path
                    capture["feed_identity"] = feed.identity
                    result["capture_path"] = immutable(root, "captures", encoded(capture), ".json")
                    changed = not previous or previous["snapshot_sha256"] != digest(body)
                    result.update(
                        status="review_required" if warnings else "ok",
                        sample_path=sample_path,
                        observation_count=len(observations),
                        snapshot_sha256=digest(body),
                        warnings=warnings,
                        **changes,
                        update_observed=bool(previous and changes["changed_rows"]),
                        refresh_verified=False,
                    )
                    if warnings:
                        db.execute(
                            "UPDATE feeds SET next_due=?,latest_sample_path=? WHERE source_id=?",
                            (clock() + feed.interval_seconds, sample_path, feed.source_id),
                        )
                    else:
                        db.execute(
                            """UPDATE feeds SET next_due=?,last_success=?,last_changed=?,
                                  failures=0,sample_path=?,etag=?,last_modified=? WHERE source_id=?""",
                            (
                                clock() + feed.interval_seconds,
                                captured_at,
                                captured_at if changed else row["last_changed"],
                                sample_path,
                                meta.get("etag") or (row["etag"] if status == 304 else ""),
                                meta.get("last_modified")
                                or (row["last_modified"] if status == 304 else ""),
                                feed.source_id,
                            ),
                        )
                        db.execute(
                            "UPDATE feeds SET latest_sample_path=? WHERE source_id=?",
                            (sample_path, feed.source_id),
                        )
                except (TimeBudgetExhausted, RequestBudgetExhausted, KeyboardInterrupt):
                    stop_reason = "time_request_budget_or_signal"
                    break
                except HostDeferred as exc:
                    result.update(status="host_deferred", retry_after_seconds=exc.seconds)
                    db.execute(
                        "UPDATE feeds SET next_due=? WHERE source_id=?",
                        (clock() + max(30, exc.seconds), feed.source_id),
                    )
                except (
                    ValueError,
                    TypeError,
                    KeyError,
                    AttributeError,
                    ParseError,
                    httpx.HTTPError,
                ) as exc:
                    failures = row["failures"] + 1
                    result.update(
                        status="failed", failure_class=type(exc).__name__, detail=str(exc)[:300]
                    )
                    db.execute(
                        "UPDATE feeds SET next_due=?,failures=? WHERE source_id=?",
                        (
                            clock() + min(3600, feed.interval_seconds * 2 ** min(failures - 1, 6)),
                            failures,
                            feed.source_id,
                        ),
                    )
                db.execute(
                    "UPDATE feeds SET status=? WHERE source_id=?",
                    (result["status"], feed.source_id),
                )
                db.execute(
                    "INSERT INTO attempts(source_id,observed_at,status,detail) VALUES(?,?,?,?)",
                    (feed.source_id, clock(), result["status"], encoded(result).decode()),
                )
                if isinstance(fetch, FeedFetcher):
                    db.execute(
                        "INSERT OR REPLACE INTO policy VALUES(1,?)",
                        (encoded(fetch.export_policy()).decode(),),
                    )
                db.commit()
                results.append(result)
            else:
                if len(due) > max_feeds:
                    stop_reason = "feed_limit"
            if isinstance(fetch, FeedFetcher):
                db.execute(
                    "INSERT OR REPLACE INTO policy VALUES(1,?)",
                    (encoded(fetch.export_policy()).decode(),),
                )
                db.commit()
            summary = report(manifest, root, now=clock(), db=db)
            verified_sources = {f["source_id"] for f in summary["feeds"] if f["refresh_verified"]}
            for result in results:
                result["refresh_verified"] = result["source_id"] in verified_sources
            summary.update(
                stop_reason=stop_reason,
                results=results,
                http_requests=getattr(fetch, "requests", 0),
            )
            temp = root / "last-run.tmp"
            temp.write_bytes(encoded(summary) + b"\n")
            temp.replace(root / "last-run.json")
            return summary
    finally:
        if owned:
            fetch.close()


def report(manifest, root, *, now=None, db=None):
    now = time.time() if now is None else now
    owned = db is None
    db = db or connect(root)
    try:
        rows = {row["source_id"]: row for row in db.execute("SELECT * FROM feeds")}
        feeds = []
        for feed in manifest.feeds:
            row = rows.get(feed.source_id)
            current = row and row["config"] == feed.identity
            success = row["last_success"] if current else None
            stale = success is None or now - success > feed.stale_after_seconds
            sample = None
            integrity = True
            if current and row["latest_sample_path"]:
                try:
                    sample, _ = read_sample(Path(root), row["latest_sample_path"])
                    if row["sample_path"] and row["sample_path"] != row["latest_sample_path"]:
                        read_sample(Path(root), row["sample_path"])
                except (OSError, ValueError, KeyError):
                    integrity = False
                    stale = True
            review = db.execute(
                "SELECT * FROM refresh_reviews WHERE source_id=? AND config=? ORDER BY id DESC LIMIT 1",
                (feed.source_id, feed.identity),
            ).fetchone()
            verified = bool(review and integrity and current and row["sample_path"])
            if verified:
                try:
                    read_sample(Path(root), review["old_sample"])
                    read_sample(Path(root), review["new_sample"])
                except (OSError, ValueError, KeyError):
                    verified = False
            feeds.append(
                {
                    "source_id": feed.source_id,
                    "enabled": feed.enabled,
                    "state": feed.state,
                    "jurisdiction_id": feed.jurisdiction_id,
                    "last_success_at": success,
                    "stale": stale,
                    "last_payload_change_at": row["last_changed"] if current else None,
                    "freshness_basis": "successful_transport_and_parse",
                    "source_timestamps": sorted(
                        {
                            r["source_timestamp"]
                            for r in sample["observations"]
                            if r.get("source_timestamp")
                        }
                    )
                    if sample
                    else [],
                    "status": (
                        "artifact_integrity_failed"
                        if not integrity
                        else row["status"]
                        if current
                        else "unpolled"
                    ),
                    "artifact_integrity": integrity,
                    "next_due_at": row["next_due"] if current else None,
                    "failures": row["failures"] if current else 0,
                    "sample_path": row["sample_path"] if current else None,
                    "warnings": sample["warnings"] if sample else [],
                    "replay_tested": bool(integrity and current and row["sample_path"]),
                    "refresh_verified": verified,
                    "refresh_review_evidence": dict(review) if review and verified else None,
                }
            )
        return {
            "election_id": manifest.election_id,
            "election_date": str(manifest.election_date),
            "configured_feeds": len(feeds),
            "enabled_feeds": sum(f["enabled"] for f in feeds),
            "stale_enabled_feeds": sum(f["enabled"] and f["stale"] for f in feeds),
            "replay_tested_feeds": sum(f["enabled"] and f["replay_tested"] for f in feeds),
            "refresh_verified_feeds": sum(f["enabled"] and f["refresh_verified"] for f in feeds),
            "feeds": feeds,
            "scope": "Selected feeds only; not national verified election coverage",
        }
    finally:
        if owned:
            db.close()
