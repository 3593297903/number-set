import subprocess
import pytest
from pathlib import Path
from number_app.storage.files import load_json

def dist_path(request):
    value=request.config.getoption('--dist-dir')
    assert value,'release tests require --dist-dir; no silent skip'
    root=Path(value)
    assert (root/'NumberTool.exe').is_file() and (root/'NumberVerify.exe').is_file()
    return root

def test_packaged_generate_and_standalone_verify(request,tmp_path):
    dist=dist_path(request); output=tmp_path/'generation.json'
    cmd=[str(dist/'NumberTool.exe'),'generate','--copies','100','--groups','40','--data-dir',str(tmp_path),'--result-json',str(output)]
    p=subprocess.run(cmd,capture_output=True,timeout=180)
    assert p.returncode==0,(p.stdout,p.stderr)
    generated=load_json(output); assert generated['status']=='COMPLETED' and generated['checks_passed']==15
    report=tmp_path/'verified.json'
    p=subprocess.run([str(dist/'NumberVerify.exe'),'--batch-dir',generated['batch_dir'],'--data-dir',str(tmp_path),'--result-json',str(report)],capture_output=True,timeout=180)
    assert p.returncode==0,p.stderr
    verified=load_json(report)
    assert verified['status']=='PASS' and verified['checks_passed']==15
    assert verified['audit_id']!=generated['audit_id']
