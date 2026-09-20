import csv
from pathlib import Path

ALL_JURISDICTIONS={
"AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"
}

def rows(path):
    with Path(path).open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def test_national_first_pass_has_all_states_and_dc():
    den=rows("registry/us_primary_election_locality_denominators.csv")
    src=rows("registry/us_state_central_authority_sources.csv")
    assert {r["state"] for r in den} == ALL_JURISDICTIONS
    assert {r["state"] for r in src} == ALL_JURISDICTIONS
    assert len(den)==51
    assert len(src)==51

def test_first_pass_keeps_uncertain_denominators_provisional():
    den={r["state"]:r for r in rows("registry/us_primary_election_locality_denominators.csv")}
    for state in ("IL","DE","DC","NV"):
        assert den[state]["estimate_status"]=="provisional"
