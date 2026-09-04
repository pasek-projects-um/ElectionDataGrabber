from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import httpx

from election_data_grabber.models import ResultObservation, Snapshot, Source


@dataclass(slots=True)
class FetchResult:
    body: bytes
    status_code: int
    content_type: str | None
    fetched_at: datetime


class Adapter(ABC):
    def __init__(self, source: Source, timeout: float = 30.0) -> None:
        self.source = source
        self.timeout = timeout

    def fetch(self) -> FetchResult:
        with httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": "ElectionDataGrabber/0.1 (+research; respectful polling)"},
        ) as client:
            response = client.get(str(self.source.url))
            response.raise_for_status()
        return FetchResult(
            body=response.content,
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            fetched_at=datetime.now(timezone.utc),
        )

    def snapshot(self, result: FetchResult, root: Path) -> Snapshot:
        digest = sha256(result.body).hexdigest()
        suffix = self.default_suffix(result.content_type)
        destination = root / self.source.source_id / f"{digest}{suffix}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            destination.write_bytes(result.body)
        return Snapshot(
            source_id=self.source.source_id,
            fetched_at=result.fetched_at,
            url=self.source.url,
            http_status=result.status_code,
            content_type=result.content_type,
            sha256=digest,
            body_path=str(destination),
        )

    @staticmethod
    def default_suffix(content_type: str | None) -> str:
        if not content_type:
            return ".bin"
        if "json" in content_type:
            return ".json"
        if "xml" in content_type:
            return ".xml"
        if "csv" in content_type:
            return ".csv"
        if "html" in content_type:
            return ".html"
        if "pdf" in content_type:
            return ".pdf"
        return ".bin"

    @abstractmethod
    def parse(self, body: bytes, *, fetched_at: datetime) -> list[ResultObservation]:
        raise NotImplementedError
