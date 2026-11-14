import json
from pathlib import Path
import pytest
from number_app.checks.a_count import check_a,parse_a
from tests.support.candidate_factory import candidate,refix

def test_a_valid_and_semantic(tmp_path):
    ctx=candidate(tmp_path)
    assert check_a(tmp_path,ctx)['status']=='PASS'
    p=tmp_path/'groups/group_001.txt'
    p.write_bytes(p.read_bytes().replace(b'000',b'999'))
    bad=refix(tmp_path,ctx)
    r=check_a(tmp_path,bad)
    assert r['status']=='FAIL' and 'fingerprint' not in str(r['errors'])

def test_a_invalid_fixed():
    data=json.loads((Path(__file__).parents[2]/'验收样例_直选金额.json').read_text(encoding='utf-8'))
    for c in data['invalid_text_cases']:
        with pytest.raises(ValueError): parse_a(c['text'].encode(),300)
