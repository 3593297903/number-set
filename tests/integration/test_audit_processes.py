from tests.support.candidate_factory import candidate
from number_app.jobs.audit import audit_batch

def test_real_15_spawn(tmp_path):
    ctx=candidate(tmp_path)
    r=audit_batch(tmp_path,ctx)
    assert r['status']=='PASS' and r['checks_passed']==15
    assert len(r['launches'])==15 and len({p['execution_id'] for p in r['launches']})==15
    assert all(p['files_read']==44 and p['bytes_read']>5000000 for p in r['checks'])
