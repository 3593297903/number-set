import json
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path
import psutil
import pytest
from tests.release.test_packaged_verify import dist_path
from tests.release.support import ROOT,exe_run,append_evidence
from tests.support.candidate_factory import candidate
from tests.support.mutations import mutate,refingerprint
from number_app.storage.files import load_json

@pytest.mark.parametrize('fault',['fingerprint','duplicate_id','all_zero_to_999','first_order','cross_group','display_wrong'])
def test_packaged_negative_candidates(request,tmp_path,fault):
    dist=dist_path(request); folder=tmp_path/'candidate'; ctx=candidate(folder)
    if fault=='fingerprint': (folder/'groups/group_001.txt').write_bytes(b'corrupt')
    else: mutate(folder,fault); refingerprint(folder,ctx)
    code,r=exe_run(dist,['--batch-dir',folder,'--data-dir',tmp_path/'catalog'],tmp_path/'result.json',verify=True)
    assert code==3 and r['status']=='FAIL' and r['checks_passed']<15
    summary=load_json(folder/'audits'/r['audit_id']/'summary.json')
    if fault in {'duplicate_id','first_order','cross_group'}:
        assert sum(c['accepted'] for c in summary['checks'] if c['method'] in 'AB')==10
        assert all(not c['accepted'] for c in summary['checks'] if c['method']=='C')
    append_evidence(dict(kind='fault',fault=fault,batch_dir=str(folder),result=r,self_consistent_fingerprints=fault!='fingerprint'))

def test_packaged_child_crash(request,tmp_path):
    dist=dist_path(request); out=tmp_path/'generation.json'
    command=[str(dist/'NumberTool.exe'),'generate','--copies','300','--groups','300','--data-dir',str(tmp_path),'--result-json',str(out)]
    process=subprocess.Popen(command); child=None; deadline=time.monotonic()+60
    while process.poll() is None and time.monotonic()<deadline:
        children=psutil.Process(process.pid).children(recursive=True)
        if children:
            child=children[0]; child.kill(); break
        time.sleep(.01)
    assert child is not None,'no real audit child found'
    code=process.wait(timeout=180); result=load_json(out)
    assert code==3 and result['status']=='FAILED' and result['checks_passed']<15
    append_evidence(dict(kind='killed_checker',command=command,killed_pid=child.pid,exitcode=code,result=result))

def test_packaged_interruption_commit_gap_and_recover(request,tmp_path):
    dist=dist_path(request); out=tmp_path/'generation.json'
    command=[str(dist/'NumberTool.exe'),'generate','--copies','300','--groups','300','--data-dir',str(tmp_path),'--result-json',str(out)]
    process=subprocess.Popen(command); db=None; row=None; deadline=time.monotonic()+120
    try:
        while process.poll() is None and time.monotonic()<deadline:
            finals=list((tmp_path/'batches').glob('*')) if (tmp_path/'batches').exists() else []
            if finals:
                db=sqlite3.connect(tmp_path/'history.sqlite',timeout=5); db.row_factory=sqlite3.Row
                db.execute('BEGIN IMMEDIATE')
                row=dict(db.execute('SELECT * FROM batches WHERE batch_id=?',(finals[0].name,)).fetchone())
                assert row['status']=='COMMITTING','missed commit gap; must not claim interruption evidence'
                process.kill(); process.wait(timeout=10); break
            time.sleep(.001)
        assert row is not None,'did not observe committed files'
    finally:
        if db: db.rollback(); db.close()
        if process.poll() is None: process.kill(); process.wait()
    assert load_json(out)['status']=='RUNNING'
    code,scan=exe_run(dist,['inspect-recovery','--data-dir',tmp_path],tmp_path/'scan.json')
    assert code==0 and scan['pending'][0]['can_resume'] and scan['pending'][0]['status']=='INTERRUPTED'
    code,recovered=exe_run(dist,['recover','--batch-id',row['batch_id'],'--data-dir',tmp_path],tmp_path/'recovered.json')
    assert code==0 and recovered['status']=='COMPLETED' and recovered['checks_passed']==15
    assert recovered['audit_id']!=row['last_audit_id']
    append_evidence(dict(kind='forced_close_after_files_before_database',command=command,killed_exitcode=process.returncode,status_at_kill=row['status'],result_file_at_kill='RUNNING',recovered=recovered))
