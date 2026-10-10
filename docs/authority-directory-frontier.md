# Local authority links from state directories

This continues the national hunting layers from merged PR #70. The watcher can now
extract observed directory links into a separate local-authority review queue,
using the state's named-unit registry. It does not silently assign a shared state
website or an ambiguous link to every unit, and does not change verified coverage.

On each successful capture of a registered state-authority/directory starting page:

1. Resolve actual anchor URLs against the observed page/base URL.
2. Match state-scoped canonical unit names in anchor labels, or a bounded table/list
   row when the label is simply "Website".
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

The initial regression cases use synthetic directories, not claimed official
captures. They cover observed URLs, base/row context, overlapping names, duplicate
names, ambiguity, social/contact/transient filtering, artifacts, anchors,
blocked/shell handling, state scoping and watcher retention. The next evidence
pass should run against saved official directories across states, review matches,
and measure how much of the 6,097-unit fallback frontier becomes local starting
evidence. Directory formats without observed links need separate structured or
rendered evidence extraction.
