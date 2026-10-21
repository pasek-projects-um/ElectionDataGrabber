"""Evidence-backed operator review of changing selected election feeds."""

import json
from datetime import UTC, datetime
from pathlib import Path

from election_data_grabber.discovery_publication import publishable_url
from election_data_grabber.election_night import (
    Feed,
    collector_lock,
    compare,
    connect,
    read_sample,
    replay_sample,
)
from election_data_grabber.national_discovery import normalize


def verify_refresh(manifest, root, old_sample, new_sample, *, evidence_url, note):
    if not note.strip() or not normalize(evidence_url) or not publishable_url(evidence_url):
        raise ValueError("An official evidence URL and an explicit review note are required")
    root = Path(root)
    with collector_lock(root / "collector.lock"):
        old, _ = read_sample(root, old_sample)
        new, _ = read_sample(root, new_sample)
        configured = {feed.identity: feed for feed in manifest.feeds if feed.enabled}
        feed = configured.get(Feed.model_validate(new["feed"]).identity)
        if not feed or old["feed"] != new["feed"]:
            raise ValueError("Both samples must match the same enabled feed configuration")
        if old["warnings"] or new["warnings"]:
            raise ValueError(
                "Unresolved sample findings require review before refresh verification"
            )
        times = [datetime.fromisoformat(sample["fetched_at"]) for sample in (old, new)]
        if times[0] >= times[1]:
            raise ValueError("Samples must have increasing acquisition times")
        if any(not -1 <= (stamp.date() - manifest.election_date).days <= 7 for stamp in times):
            raise ValueError("Samples must fall within the configured election reporting window")
        changes = compare(old["observations"], new["observations"], feed.update_semantics)
        if not changes["common_rows"] or not changes["changed_rows"] or changes["removed_rows"]:
            raise ValueError("Refresh evidence requires changed votes and continuous identities")
        if changes["decreased_rows"]:
            raise ValueError("Cumulative decreases require separate correction adjudication")
        for sample in (old_sample, new_sample):
            replay_sample(root, sample)
        db = connect(root)
        try:
            accepted = {
                json.loads(row["detail"]).get("sample_path")
                for row in db.execute(
                    "SELECT detail FROM attempts WHERE source_id=? AND status='ok'",
                    (feed.source_id,),
                )
            }
            if not {old_sample, new_sample} <= accepted:
                raise ValueError("Both samples must be accepted collector attempts")
            reviewed = datetime.now(UTC).isoformat()
            db.execute(
                """INSERT INTO refresh_reviews(source_id,config,old_sample,new_sample,
                          reviewed_at,evidence_url,note) VALUES(?,?,?,?,?,?,?)""",
                (
                    feed.source_id,
                    feed.identity,
                    old_sample,
                    new_sample,
                    reviewed,
                    evidence_url,
                    note,
                ),
            )
            db.commit()
            return {
                "source_id": feed.source_id,
                "refresh_verified": True,
                "reviewed_at": reviewed,
                "old_sample": old_sample,
                "new_sample": new_sample,
                "changes": changes,
                "scope": "This configured source/election only; not national coverage",
            }
        finally:
            db.close()
