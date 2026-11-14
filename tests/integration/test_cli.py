import subprocess
import sys
from number_app.storage.files import load_json

def test_cli_generate_verify(tmp_path):
    out=tmp_path/'generation.json'
    cmd=[sys.executable,'-m','number_app']
    r=subprocess.run(cmd+['generate','--copies','100','--groups','40','--data-dir',str(tmp_path),'--result-json',str(out)],capture_output=True,timeout=180)
    assert r.returncode==0,r.stderr
    result=load_json(out); assert result['status']=='COMPLETED'
    before=load_json(result['batch_dir']+'/manifest.json')
    check=tmp_path/'reverify.json'
    r=subprocess.run(cmd+['verify','--batch-dir',result['batch_dir'],'--data-dir',str(tmp_path),'--result-json',str(check)],capture_output=True,timeout=180)
    assert r.returncode==0,r.stderr
    report=load_json(check)
    assert report['status']=='PASS' and report['audit_id']!=result['audit_id'] and report['checks_passed']==15
    assert load_json(result['batch_dir']+'/manifest.json')==before
    r=subprocess.run(cmd+['generate','--copies','99','--groups','40','--result-json',str(out)],capture_output=True,timeout=20)
    assert r.returncode==2 and load_json(out)['status']=='INVALID_INPUT'
