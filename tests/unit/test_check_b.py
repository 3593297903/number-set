import json
from pathlib import Path
import pytest
from number_app.checks.b_sort import check_b,parse_b
from tests.support.candidate_factory import candidate,refix

def test_b_valid_and_semantic(tmp_path):
    ctx=candidate(tmp_path)
    assert check_b(tmp_path,ctx)['status']=='PASS'
    p=tmp_path/'groups/group_001.txt'; p.write_bytes(p.read_bytes().replace(b'000',b'999'))
    r=check_b(tmp_path,refix(tmp_path,ctx))
    assert r['status']=='FAIL' and 'fingerprint' not in str(r['errors'])

def test_b_fixed_invalid():
    fixture=json.loads((Path(__file__).parents[2]/'验收样例_直选金额.json').read_text(encoding='utf-8'))
    for c in fixture['invalid_text_cases']:
        with pytest.raises(ValueError): parse_b(c['text'].encode(),300)
