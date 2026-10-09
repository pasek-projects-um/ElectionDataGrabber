import csv
import io
import zipfile
from pathlib import Path
from scripts.expand_census_county_starts import expand


def test_county_enumeration_is_provenanced_and_idempotent(tmp_path: Path):
    (tmp_path / "us_primary_election_locality_denominators.csv").write_text(
        "state,expected_primary_units,authority_model\nAL,2,county\nMA,351,municipal\n")
    (tmp_path / "us_primary_election_localities.csv").write_text(
        "jurisdiction_id,state,jurisdiction_level,canonical_name\n"
        "us:al:county:alpha,AL,county,Alpha County\n")
    source = "USPS\tGEOID\tNAME\nAL\t01001\tAlpha County\nAL\t01003\tBeta County\nMA\t25001\tBarnstable County\n"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("counties.txt", source)
    rows, added = expand(tmp_path, buffer.getvalue())
    assert len(added) == 1
    assert added[0]["canonical_name"] == "Beta County"
    assert added[0]["external_id"] == "01003"
    assert added[0]["final_evidence_url"] == ""
    assert added[0]["assessment_status"] == "enumerated_not_source_verified"
    assert len(rows) == 2
