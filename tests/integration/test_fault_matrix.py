import pytest
from number_app.checks.a_count import check_a
from number_app.checks.b_sort import check_b
from number_app.checks.c_ids import check_c
from tests.support.candidate_factory import candidate
from tests.support.mutations import mutate,refingerprint

C_ONLY=['delete_item','add_item','duplicate_id','id_negative','id_bool','id_mapping','code_short','code_unicode','position_duplicate','position_missing','empty_jsonl','empty_group','first_order','cross_group']
ALL=['all_zero_to_999','one_code_imbalance','amount_wrong','quota_wrong','quota_duplicate','display_wrong','duplicate_json_key','missing_group']

@pytest.mark.parametrize('name',C_ONLY+ALL)
def test_self_consistent_semantic_matrix(tmp_path,name):
    ctx=candidate(tmp_path); mutate(tmp_path,name); ctx=refingerprint(tmp_path,ctx)
    reports=[f(tmp_path,ctx) for f in (check_a,check_b,check_c)]
    assert reports[2]['status']!='PASS',reports
    if name in C_ONLY:
        assert reports[0]['status']==reports[1]['status']=='PASS',reports
    else: assert all(r['status']!='PASS' for r in reports),reports

def test_fingerprint_corruption(tmp_path):
    ctx=candidate(tmp_path); (tmp_path/'groups/group_001.txt').write_bytes('007直选1元\n'.encode())
    for check in (check_a,check_b,check_c):
        r=check(tmp_path,ctx); assert r['status']!='PASS' and 'fingerprint' in str(r['errors'])
