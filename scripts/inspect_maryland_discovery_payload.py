"""Cross-check saved observed Maryland vote payloads; performs no network requests."""

import argparse
import hashlib
import json
from pathlib import Path

from election_data_grabber.discovery_payloads import (
    maryland_congressional_csv,
    maryland_governor_html,
    reconcile_maryland_governor,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    html, data = args.html.read_bytes(), args.csv.read_bytes()
    result = reconcile_maryland_governor(
        maryland_governor_html(html.decode("utf-8-sig")),
        maryland_congressional_csv(data.decode("utf-8-sig")),
    )
    result.update(
        html_sha256=hashlib.sha256(html).hexdigest(), csv_sha256=hashlib.sha256(data).hexdigest()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
