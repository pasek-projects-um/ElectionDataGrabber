import csv
from pathlib import Path


def test_first_pass_state_result_surfaces_cover_all_states_and_dc():
    path = Path("registry/first_pass_state_result_surfaces.csv")
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    states = {row["state"] for row in rows}
    expected = {
        "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
        "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
        "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC",
    }
    assert states == expected
    assert len(rows) == 51
    assert all(row["result_url"].startswith("https://") for row in rows)
    assert all(row["source_scope"] in {"statewide", "county"} for row in rows)
