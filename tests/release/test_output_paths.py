"""Path regression against the exact candidate/published executable bytes."""
import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path
import pytest
from tests.integration.test_output_paths import (QA,CASES,prepare_context,target_cases,protected_snapshot,states,tree_snapshot,save,junction)
from tests.release.test_packaged_verify import dist_path

def invoke(dist,args,receipt,verify=False):
    exe=dist/('NumberVerify.exe' if verify else 'NumberTool.exe')
    expected=json.loads((QA/'candidate-exes.json').read_text(encoding='utf-8'))['sha256'][exe.name]
    actual=hashlib.sha256(exe.read_bytes()).hexdigest()
    assert actual==expected,'Wrong/stale executable '+str(exe)
    receipt.parent.mkdir(parents=True,exist_ok=True)
    command=[str(exe),*map(str,args),'--result-json',str(receipt)]
    started=time.monotonic(); completed=subprocess.run(command,capture_output=True,timeout=240)
    assert receipt.is_file(),(completed.returncode,completed.stderr)
    result=json.loads(receipt.read_text(encoding='utf-8'))
    assert hashlib.sha256(exe.read_bytes()).hexdigest()==actual,'Executable changed during test'
    save(receipt.with_suffix('.command.json'),dict(command=command,exe=str(exe.resolve()),sha256=actual,exitcode=completed.returncode,
        duration_ms=int((time.monotonic()-started)*1000),result=result,stdout=completed.stdout.decode(errors='replace'),stderr=completed.stderr.decode(errors='replace')))
    return completed.returncode,result

@pytest.fixture(scope='module')
def exe_context(request):
    dist=dist_path(request).resolve(); base=QA/'exe'/(dist.parent.name+'-'+uuid.uuid4().hex)
    def generator(workspace,label):
        code,result=invoke(dist,['generate','--copies',100,'--groups',40,'--data-dir',workspace],base/'receipts'/f'generate-{label}.json')
        assert code==0 and result['status']=='COMPLETED' and result['checks_passed']==15
        return result
    c=prepare_context(base,generator); c['dist']=dist
    save(base/'tested-executables.json',dict(dist=str(dist),sha256={name:hashlib.sha256((dist/name).read_bytes()).hexdigest() for name in ['NumberTool.exe','NumberVerify.exe']}))
    return c

@pytest.mark.parametrize('operation',['backup','export'])
@pytest.mark.parametrize('case',CASES)
def test_exe_rejects_without_any_protected_write(exe_context,operation,case):
    c=exe_context; destination=target_cases(c)[case]
    before=protected_snapshot(c); before_states=states(c['workspace'])
    args=['backup','--backup-dir',destination] if operation=='backup' else ['export','--batch-id',c['A']['batch_id'],'--destination',destination]
    code,result=invoke(c['dist'],[*args,'--data-dir',c['workspace']],c['base']/'receipts'/f'{operation}-{case}.json')
    after=protected_snapshot(c); after_states=states(c['workspace'])
    save(c['base']/'evidence'/f'{operation}-{case}.json',dict(exitcode=code,result=result,trees_equal=before==after,states_equal=before_states==after_states,
        before=before,after=after,before_states=before_states,after_states=after_states))
    assert code==3 and result['status']=='FAIL',result
    assert before==after,'Rejected exe operation wrote to protected trees'
    assert before_states==after_states,'Rejected exe operation changed batch status'

def test_exe_checks_resolved_final_target_not_only_root(exe_context):
    c=exe_context; parent=c['base']/'planned-target-parent'; parent.mkdir(); junction(parent/c['A']['batch_id'],c['b'])
    before=protected_snapshot(c); parent_before=tree_snapshot(parent); before_states=states(c['workspace'])
    code,result=invoke(c['dist'],['export','--batch-id',c['A']['batch_id'],'--data-dir',c['workspace'],'--destination',parent],c['base']/'receipts/planned-target.json')
    after=protected_snapshot(c)
    save(c['base']/'evidence/planned-target.json',dict(exitcode=code,result=result,before=before,after=after,parent_before=parent_before,parent_after=tree_snapshot(parent)))
    assert code==3 and result['status']=='FAIL'
    assert before==after and parent_before==tree_snapshot(parent) and before_states==states(c['workspace'])

def test_exe_original_batches_still_pass_fresh_15_checks(exe_context):
    c=exe_context; results=[]
    for label,path in [('A',c['a']),('B',c['b']),('external',c['external'])]:
        code,r=invoke(c['dist'],['--batch-dir',path,'--data-dir',c['workspace']],c['base']/'receipts'/f'reverify-{label}.json',verify=True)
        assert code==0 and r['status']=='PASS' and r['checks_passed']==15; results.append(r)
    assert all(row[1]=='COMPLETED' for row in states(c['workspace']) if row[0] in [c['A']['batch_id'],c['B']['batch_id']])
    save(c['base']/'evidence/fresh-reverify.json',results)

def test_exe_normal_independent_backup_export_restore_and_real_paths(exe_context):
    c=exe_context; results=[]
    for label,destination in [('normal',c['base']/'independent'),('junction',c['normal_alias']),('similar-sibling',c['base']/'registered-other')]:
        code,e=invoke(c['dist'],['export','--batch-id',c['A']['batch_id'],'--data-dir',c['workspace'],'--destination',destination],c['base']/'receipts'/f'normal-export-{label}.json')
        assert code==0 and e['status']=='EXPORTED' and Path(e['export_dir'])==destination.resolve()/c['A']['batch_id']
        assert tree_snapshot(e['export_dir'])==tree_snapshot(c['a'])
        code,b=invoke(c['dist'],['backup','--data-dir',c['workspace'],'--backup-dir',destination/'backups'],c['base']/'receipts'/f'normal-backup-{label}.json')
        assert code==0 and b['status']=='BACKUP_COMPLETE' and Path(b['backup_dir']).parent==(destination/'backups').resolve()
        results.append(dict(export=e,backup=b))
    code,r=invoke(c['dist'],['restore','--backup-dir',results[0]['backup']['backup_dir'],'--destination',c['base']/'restored','--data-dir',c['workspace']],c['base']/'receipts/restored.json')
    assert code==0 and r['status']=='RESTORED' and all(b['checks_passed']==15 and b['status']=='COMPLETED' for b in r['batches'])
    save(c['base']/'evidence/normal-outputs.json',dict(results=results,restored=r))

def test_exe_maximum_300000_and_independent_reverify(exe_context):
    c=exe_context; root=c['base']/'maximum'
    code,g=invoke(c['dist'],['generate','--copies',300,'--groups',300,'--data-dir',root],c['base']/'receipts/maximum-generation.json')
    assert code==0 and g['status']=='COMPLETED' and g['checks_passed']==15 and g['total_items']==300000
    before=tree_snapshot(Path(g['batch_dir'])/'groups'); detail=hashlib.sha256((Path(g['batch_dir'])/'items.jsonl').read_bytes()).hexdigest()
    code,v=invoke(c['dist'],['--batch-dir',g['batch_dir'],'--data-dir',root],c['base']/'receipts/maximum-verified.json',verify=True)
    assert code==0 and v['status']=='PASS' and v['checks_passed']==15 and v['audit_id']!=g['audit_id']
    assert tree_snapshot(Path(g['batch_dir'])/'groups')==before
    assert hashlib.sha256((Path(g['batch_dir'])/'items.jsonl').read_bytes()).hexdigest()==detail
    save(c['base']/'evidence/maximum.json',dict(generation=g,reverify=v,detail_sha256=detail))
