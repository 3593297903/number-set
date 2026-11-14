import pytest
from tests.support.candidate_factory import candidate
from tests.support.faults import absent_report,crash_worker,slow_worker,old_report,change_report_after_read,change_files_after_read
from number_app.jobs.audit import audit_batch,all_pass

def test_gate_exact_combinations():
    good=[dict(method=m,round=r,accepted=True) for r in range(1,6) for m in 'ABC']
    assert all_pass(good)
    assert not all_pass(good[:-1])
    assert not all_pass(good[:-1]+[good[0]])

@pytest.mark.parametrize('target,timeout',[(absent_report,120),(crash_worker,120),(slow_worker,.05),(old_report,120)])
def test_fail_closed(tmp_path,target,timeout):
    ctx=candidate(tmp_path)
    r=audit_batch(tmp_path,ctx,_target=target,timeout=timeout)
    assert r['status']!='PASS' and r['checks_passed']==0

@pytest.mark.parametrize('target',[change_report_after_read,change_files_after_read])
def test_mutation_after_checks_never_passes(tmp_path,target):
    ctx=candidate(tmp_path); r=audit_batch(tmp_path,ctx,_target=target)
    assert r['status']=='FAIL' and 'error' in r
