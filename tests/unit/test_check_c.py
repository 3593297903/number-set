import json
from tests.support.candidate_factory import candidate,refix
from number_app.checks.c_ids import check_c
from number_app.checks.a_count import check_a
from number_app.checks.b_sort import check_b

def test_c_valid_duplicate_same_code(tmp_path):
    ctx=candidate(tmp_path)
    assert check_c(tmp_path,ctx)['status']=='PASS'
    p=tmp_path/'items.jsonl'; lines=p.read_bytes().splitlines(); first=json.loads(lines[0]); code=first['code']
    j=next(i for i in range(1,len(lines)) if json.loads(lines[i])['code']==code)
    item=json.loads(lines[j]); item['item_id']=first['item_id']; lines[j]=json.dumps(item).encode()
    p.write_bytes(b'\n'.join(lines)+b'\n'); ctx=refix(tmp_path,ctx)
    assert check_a(tmp_path,ctx)['status']=='PASS'
    assert check_b(tmp_path,ctx)['status']=='PASS'
    report=check_c(tmp_path,ctx)
    assert report['status']=='FAIL' and 'duplicate item_id' in str(report['errors'])

def test_first_order(tmp_path):
    ctx=candidate(tmp_path); p=tmp_path/'groups/group_001.txt'; text=p.read_text(encoding='utf-8'); a,b,tail=text.split('.',2)
    p.write_bytes((b+'.'+a+'.'+tail).encode()); ctx=refix(tmp_path,ctx)
    assert check_a(tmp_path,ctx)['status']=='PASS'
    assert check_b(tmp_path,ctx)['status']=='PASS'
    assert check_c(tmp_path,ctx)['status']=='FAIL'
