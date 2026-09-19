from election_data_grabber.state_expansion import PROFILES, classify_result_family, expansion_profile


def test_large_state_profiles_cover_all_unresolved_directory_states():
    assert set(PROFILES)=={"AK","AL","GA","KS","LA","MA","ND","NM","NY","RI","SC","VT","WI"}
    assert sum(p.expected_units for p in PROFILES.values())==3073


def test_profiles_preserve_noncounty_authority_models():
    assert expansion_profile("LA").primary_unit=="parish"
    assert expansion_profile("MA").primary_unit=="municipality"
    assert expansion_profile("VT").primary_unit=="town"
    assert expansion_profile("WI").primary_unit=="municipality"
    assert expansion_profile("AK").primary_unit=="election_region"


def test_family_classifier_prioritizes_reusable_result_families():
    assert classify_result_family("https://app.enhancedvoting.com/results/public/a/elections/1")=="enhanced_voting"
    assert classify_result_family("https://results.enr.clarityelections.com/GA/X/1/")=="clarity"
    assert classify_result_family("https://county.gov/results","Powered by Scytl")=="scytl"
    assert classify_result_family("https://county.gov/results","Electionware report")=="electionware"
    assert classify_result_family("https://county.gov/DocumentCenter/View/1/results.pdf")=="civicplus"
    assert classify_result_family("https://county.gov/results.xlsx")=="tabular_download"
    assert classify_result_family("https://county.gov/results")=="official_web"
