# Local authority links from state directories

This continues the national hunting layers from merged PR #70. The watcher can now
extract observed directory links into a separate local-authority review queue,
using the state's named-unit registry. It does not silently assign a shared state
website or an ambiguous link to every unit, and does not change verified coverage.

On each successful capture of a registered state-authority/directory starting page:

1. Resolve actual anchor URLs against the observed page/base URL.
2. Match state-scoped canonical unit names in anchor labels, a bounded table/list
   row, a details summary or a definition term when the label is simply "Website".
   County/parish units also accept the observed display name without that suffix;
   duplicate aliases remain ambiguous and canonical IDs remain unchanged.
3. Keep unique label matches separate from ambiguous names, unmatched authority
   links, artifact links and in-page anchors.
4. Bind candidates to their directory URL, exact evidence excerpt and snapshot hash.
5. Retain units without an unambiguous website-label candidate as further hunting
   work; blocked pages and application shells are access follow-up.

Matching is conservative. For example, "New York" suppresses a nested "York"
match, but two units with the same name remain ambiguous. No URLs are generated
from unit names. Social links, mailto links and transient-token URLs do not clear
website-label gaps. A successful label match is not a verified election authority
or service-area association.

## Worker integration

The existing scheduled command automatically reads the named units from
`--registry registry` and writes `watch-data/authority-link-queue.csv`, in addition
to its result-candidate queue. Its checkpoint retains first/last observation times
and per-directory unresolved unit IDs. New authority-link candidates produce
`authority_link_candidate` events. A later fetch failure preserves prior evidence.

Authority candidates are kept in the review queue rather than automatically
followed as verified authority sites. After adjudication, add appropriate URLs and
unit associations to the official registries or explicit watcher seeds and
regenerate the national layer frontier. Existing result-candidate follow-up remains
separate. This PR has not adjudicated or added new locality websites.

## Replay a saved directory capture

From the repository root:

```sh
python -m scripts.extract_authority_directory \
  --state MD \
  --page-url https://elections.maryland.gov/about/county_boards.html \
  --html /absolute/path/to/saved-directory.html \
  --output audit/authority-directory-md
```

The file must be an actual saved capture of that page. This command makes no
network requests and produces `authority-link-candidates.csv`,
`unresolved-units.csv`, and `summary.json`. Counts describe evidence in that single
capture, not source absence or complete state coverage.

The regression cases use synthetic examples, including a manually constructed
example of the details/summary structure observed on Maryland's official page.
They cover ambiguity, contact/transient filtering, link roles, blocked/shell
handling, state scoping, watcher retention and capture digest verification.

## National capture replay and readiness report

The October 10 pass checked all 51 registered state/DC starting pages with 96 HTTP
requests. It saved 29 captures, of which 28 contain usable HTML and one is a security
challenge; 12 pages were robots-denied, four had
unresolved robots access and six had unresolved fetches. Offline replay extracted
1,420 links and retained link roles separately: authority websites, external
websites, result leads, documents/maps, anchors and other links. Only unique
unit-label matches to website/result leads contribute a directory hunting clue.
Targets linked from these directories have not been fetched by this pass.

Across the 6,288 named units, the report has 39 units with observed result-page
candidates from the prior discovery catalog, 248 with hunting locations, and
6,001 unresolved. These counts describe units, not distinct URLs. Catalog parent
joins and directory labels still require service-area review; none of these
counts certifies live results or a served jurisdiction. Provisional denominators
remain provisional. Shared statewide fallbacks do not resolve local gaps.

See [the report](../audit/authority-directory-national/README.md). Reproduce from
your own saved watcher checkpoint and snapshots:

```sh
python -m scripts.replay_national_authority_directories \
  --watch-state /absolute/path/to/watch-data/state.json \
  --snapshots /absolute/path/to/watch-data/snapshots \
  --output audit/authority-directory-national
```

The replay checks capture hashes, makes no network requests and writes per-state
capture status, observed link evidence, per-unit readiness and summary files.
Raw HTML remains in the worker snapshot directory; the repository report records
source URLs, digests and bounded excerpts. It does not claim a complete crawl.
Directory formats without usable links need structured or rendered extraction.
