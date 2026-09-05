# Ohio portability census

Ohio is the first cross-state stress test for the extraction architecture built in Michigan.

For each county classify portability as:

- **A** existing parser works unchanged
- **B** existing parser works with source-profile/config changes only
- **C** existing parser needs a reusable/general enhancement
- **D** genuinely new platform family
- **E** bespoke or unstructured source

The engineering objective is for A+B to rise as the project encounters more jurisdictions. A county-specific parser should be the last resort.

The first cohort intentionally mixes large urban, suburban, industrial, college-town, and rural counties. For each county capture official authority, current/live result endpoint, archive, precinct granularity, vote-mode detail, turnout fields, under/overvotes, downloadable formats, reporting topology, audit/canvass material, and platform family.

Administrative/reporting semantics remain separate from parser shape: the same vendor in Ohio and Michigan may encode early voting, absentee, precinct reporting, or aggregation differently.
