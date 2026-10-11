from election_data_grabber.source_context import source_context
from election_data_grabber.structured_directory import extract_csv_directory


def test_format_does_not_establish_updates():
    for url in ('https://a.gov/results/2026.csv', 'https://a.gov/results/2026.html'):
        row = source_context(url)
        assert row['election_context'] == 'current_year_candidate'
        assert row['update_evidence'] == 'unknown'
    assert source_context('https://a.gov/dashboard')['election_context'] == 'unknown'
    assert source_context('https://a.gov/results/2024.pdf')['election_context'] == 'historical'
    assert source_context('https://a.gov/archive/2026')['election_context'] == 'historical'
    assert source_context('https://a.gov/results', '2024 and 2026')['election_context'] == 'mixed_or_other_years'


def test_csv_keeps_byte_provenance_and_ambiguity():
    import hashlib
    units = [{'state': 'XY', 'canonical_name': name, 'jurisdiction_id': str(i)}
             for i, name in enumerate(('Alpha', 'Beta', 'Beta', 'Gamma'))]
    body = b'\xef\xbb\xbfTown,Website\r\nAlpha,https://alpha.gov/clerk\r\nBeta,https://beta.gov/\r\nGamma,\r\n'
    rows, gaps = extract_csv_directory('https://state.gov/clerks.csv', body, units,
                                      state='XY', name_column='Town', url_column='Website')
    assert len(rows) == 2
    assert rows[0]['csv_row_number'] == 2
    assert rows[0]['snapshot_sha256'] == hashlib.sha256(body).hexdigest()
    assert rows[1]['match_status'] == 'ambiguous_unit_label'
    assert len(gaps) == 3
    assert all(r['live_coverage'] == 'false' for r in rows)


def test_csv_does_not_guess_or_accept_contacts():
    import pytest
    units = [{'state': 'XY', 'canonical_name': 'Alpha', 'jurisdiction_id': 'a'}]
    for value in ('alpha.gov', '/alpha', 'mailto:clerk@alpha.gov', 'https://alpha.gov/?token=secret'):
        rows, gaps = extract_csv_directory('https://state.gov/list.csv',
            f'Town,Website\nAlpha,{value}\n'.encode(), units,
            state='XY', name_column='Town', url_column='Website')
        assert not rows and len(gaps) == 1
    with pytest.raises(ValueError, match='Missing explicit'):
        extract_csv_directory('https://state.gov/list.csv', b'Town,Phone\nAlpha,123\n', units,
                              state='XY', name_column='Town', url_column='Website')


def test_inventory_retains_artifacts_and_separate_parent_evidence(tmp_path):
    from scripts.replay_national_authority_directories import source_inventory
    (tmp_path / 'discovered_result_sources.csv').write_text(
        'url,observed_from,observed_years,election_labels,target_status\n'
        'https://a.gov/2024.csv,https://a.gov/results,2024,Primary,fetched\n')
    rows = source_inventory(tmp_path, [{'url': 'https://b.gov/2026.pdf',
        'observed_from': 'https://state.gov/list', 'evidence_excerpt': 'Beta results'}])
    assert len(rows) == 2
    assert rows[0]['source_format'] == 'csv'
    assert rows[0]['election_context'] == 'historical'
    assert rows[1]['target_status'] == 'not_checked'
    assert rows[1]['source_format'] == 'pdf'
    assert all(row['update_evidence'] == 'unknown' for row in rows)
