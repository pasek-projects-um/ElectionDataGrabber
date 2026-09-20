from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

from election_data_grabber.locality_registry import read_localities, read_denominators
from election_data_grabber.source_capabilities import read_source_capabilities


def build_census(root: Path) -> list[dict[str, str]]:
    localities=read_localities(root/"registry/us_primary_election_localities.csv")
    denominators={d.state:d for d in read_denominators(root/"registry/us_primary_election_locality_denominators.csv")}
    capabilities=read_source_capabilities(root/"registry/jurisdiction_source_capabilities.csv")

    by_state=defaultdict(list)
    for row in localities:
        by_state[row.state].append(row)
    caps_by_state=defaultdict(list)
    for cap in capabilities:
        parts=cap.jurisdiction_id.split(":")
        if len(parts) > 1:
            caps_by_state[parts[1].upper()].append(cap)

    out=[]
    for state in sorted(denominators):
        rows=by_state.get(state,[])
        caps=caps_by_state.get(state,[])
        levels=Counter(r.jurisdiction_level for r in rows)
        reporting_units=Counter((c.smallest_observed_unit or "unknown") for c in caps)
        platforms=Counter((c.platform_family or "unknown") for c in caps)
        capability_types=Counter(c.capability_type.value for c in caps)
        out.append({
            "state":state,
            "expected_primary_units":str(denominators[state].expected_primary_units),
            "enumerated_primary_units":str(len(rows)),
            "administrative_levels":"|".join(f"{k}:{v}" for k,v in sorted(levels.items())) or "none",
            "observed_reporting_units":"|".join(f"{k}:{v}" for k,v in sorted(reporting_units.items())) or "none",
            "capability_types":"|".join(f"{k}:{v}" for k,v in sorted(capability_types.items())) or "none",
            "data_access_families":"|".join(f"{k}:{v}" for k,v in sorted(platforms.items())) or "none",
        })
    return out


def write_census(root: Path, out_path: Path) -> None:
    rows=build_census(root)
    out_path.parent.mkdir(parents=True,exist_ok=True)
    fields=[
        "state","expected_primary_units","enumerated_primary_units","administrative_levels",
        "observed_reporting_units","capability_types","data_access_families",
    ]
    with out_path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader(); w.writerows(rows)


if __name__=="__main__":
    root=Path(__file__).resolve().parents[1]
    write_census(root,root/"audit/state_unit_data_access_census.csv")
