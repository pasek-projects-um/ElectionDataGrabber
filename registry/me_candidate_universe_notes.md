# Maine permissive candidate universe

Source strategy: use Maine state locality lists as a permissive superset, not as proof of election-authority status.

Candidate classes:

- `organized_candidate`: town/city/plantation-like entity that may have a local election authority.
- `ut_candidate`: unorganized township/gore/surplus/grant-like geography that may appear in state-administered election reporting but should not be assumed to have its own clerk/result site.
- `verified_authority`: locality whose official election authority/source has been confirmed.
- `rejected_authority`: candidate geography/source that is not a standalone election authority for our purposes.

The smoke/discovery process should promote/demote candidates based on reachable official sources and published election artifacts. Presence in the registry is discovery scope only, not evidence of live ingest support.
