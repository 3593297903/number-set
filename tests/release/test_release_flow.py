import pytest
from pathlib import Path
from tests.release.test_packaged_verify import dist_path
from tests.release.support import ROOT,exe_run
from number_app.storage.files import load_json

@pytest.mark.parametrize('s,k',[(100,40),(100,300),(300,40),(137,73),(300,300)])
def test_boundaries_exe(request,s,k):
    dist=dist_path(request); root=ROOT/f'c{s}_g{k}'; root.mkdir(exist_ok=True)
    code,r=exe_run(dist,['generate','--copies',s,'--groups',k,'--data-dir',root],root/'generation.json')
    assert code==0 and r['status']=='COMPLETED' and r['checks_passed']==15 and r['total_items']==1000*s
    summary=load_json(Path(r['batch_dir'])/'audits'/r['audit_id']/'summary.json')
    assert len(summary['launches'])==15 and len({v['execution_id'] for v in summary['launches']})==15
    assert all(c['accepted'] and c['exitcode']==0 for c in summary['checks'])

def test_exe_export_backup_restore(request,tmp_path):
    dist=dist_path(request); root=ROOT/'c300_g300'; generated=load_json(root/'generation.json')
    before=(Path(generated['batch_dir'])/'manifest.json').read_bytes()
    code,verified=exe_run(dist,['--batch-dir',generated['batch_dir'],'--data-dir',root],root/'exe_reverify.json',verify=True)
    assert code==0 and verified['status']=='PASS' and verified['audit_id']!=generated['audit_id']
    assert (Path(generated['batch_dir'])/'manifest.json').read_bytes()==before
    code,exported=exe_run(dist,['export','--batch-id',generated['batch_id'],'--data-dir',root,'--destination',tmp_path/'exports'],tmp_path/'export-result.json')
    assert code==0 and exported['status']=='EXPORTED'
    assert (Path(exported['export_dir'])/'manifest.json').read_bytes()==before
    code,backup=exe_run(dist,['backup','--data-dir',root,'--backup-dir',tmp_path/'backups'],tmp_path/'backup-result.json')
    assert code==0 and backup['status']=='BACKUP_COMPLETE'
    code,restored=exe_run(dist,['restore','--backup-dir',backup['backup_dir'],'--destination',tmp_path/'restored','--data-dir',root],tmp_path/'restore-result.json')
    assert code==0 and restored['status']=='RESTORED'
    assert all(b['checks_passed']==15 and b['status']=='COMPLETED' for b in restored['batches'])
