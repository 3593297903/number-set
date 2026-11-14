"""Public backend regressions; every destructive probe uses a new QA workspace."""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import uuid
from pathlib import Path
import pytest
from number_app.jobs.service import generate_batch,verify_batch
from number_app.spec import BatchSpec
from number_app.storage.backup import create_backup,validate_backup,restore_backup
from number_app.storage.catalog import Catalog
from number_app.storage.export import export_batch

QA=Path(__file__).resolve().parents[2]/'qa/pathguard-fix'

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def tree_snapshot(root):
    root=Path(root); nodes={}
    def visit(path,relative):
        if path.is_symlink() or path.is_junction():
            nodes[relative]=dict(kind='link',target=str(path.resolve())); return
        if path.is_file():
            b=path.read_bytes(); nodes[relative]=dict(kind='file',size=len(b),sha256=hashlib.sha256(b).hexdigest()); return
        if path.is_dir():
            nodes[relative]=dict(kind='directory')
            for child in sorted(path.iterdir()): visit(child,child.relative_to(root).as_posix())
        elif path.exists(): raise AssertionError('unknown filesystem object '+str(path))
    visit(root,'.')
    return nodes

def states(root):
    with sqlite3.connect((Path(root)/'history.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
        return db.execute('SELECT batch_id,status,last_audit_id,batch_dir FROM batches ORDER BY batch_id').fetchall()

def junction(alias,target):
    p=subprocess.run(['cmd','/c','mklink','/J',str(alias),str(target)],capture_output=True)
    assert p.returncode==0,(p.stdout,p.stderr)
    assert alias.is_junction() and alias.resolve()==target.resolve()

def prepare_context(base,generator):
    base.mkdir(parents=True,exist_ok=False); workspace=base/'workspace'
    a=generator(workspace,'A'); b=generator(workspace,'B')
    assert a['status']==b['status']=='COMPLETED' and a['checks_passed']==b['checks_passed']==15
    a_path=Path(a['batch_dir']); b_path=Path(b['batch_dir']); catalog=Catalog(workspace)
    registered=base/'registered'; registered.mkdir(); (registered/'keep.txt').write_text('unfinished registered batch',encoding='utf-8')
    future=base/'future-registered'
    staged=workspace/'staging/registered-partial'; staged.mkdir(); (staged/'keep.txt').write_text('partial',encoding='utf-8')
    orphan=workspace/'staging/unregistered-partial'; orphan.mkdir(); (orphan/'keep.txt').write_text('orphan',encoding='utf-8')
    for bid,path in [('registered-created',registered),('registered-not-created',future),('staged-created',staged)]:
        catalog.add(bid,BatchSpec(100,40),path,'2026-11-14T00:00:00+08:00')
    external=base/'external-exported-batch'; shutil.copytree(b_path,external)
    marked={}
    for marker in ['manifest.json','items.jsonl','quotas.json']:
        folder=base/('external-broken-'+marker.split('.')[0]); folder.mkdir()
        (folder/'request.json').write_bytes(b'not valid json')
        (folder/marker).write_bytes(b'damaged marker bytes')
        marked[marker]=folder
    aliases={}
    for key,target in [('A',a_path),('B',b_path),('external',external)]:
        aliases[key]=base/('junction-'+key); junction(aliases[key],target)
    normal=base/'normal-real'; normal.mkdir(); normal_alias=base/'normal-junction'; junction(normal_alias,normal)
    obstruction=base/'obstructions'; obstruction.mkdir(); file=obstruction/'plain-file'; file.write_bytes(b'keep file')
    protected=[workspace/'batches',workspace/'staging',registered,future,external,*marked.values(),obstruction]
    return dict(base=base,workspace=workspace,A=a,B=b,a=a_path,b=b_path,registered=registered,future=future,staged=staged,orphan=orphan,
                external=external,marked=marked,aliases=aliases,normal=normal,normal_alias=normal_alias,file=file,protected=protected)

def source_generator(workspace,label): return generate_batch(BatchSpec(100,40),workspace)

def target_cases(c):
    return {
        'source-root':c['a'], 'source-groups':c['a']/'groups', 'source-future-audits':c['a']/'audits/not-created/deeper',
        'other-root':c['b'], 'other-future':c['b']/'new/not-created',
        'batches-reserved':c['workspace']/'batches/future/not-created',
        'staging-registered':c['staged']/'deeper', 'staging-unregistered':c['orphan']/'deeper',
        'staging-future':c['workspace']/'staging/never-created/deeper',
        'registered-created':c['registered']/'nested', 'registered-future':c['future']/'nested',
        'external-valid':c['external']/'groups/new',
        'external-broken-manifest':c['marked']['manifest.json']/'new/deep',
        'external-items-marker':c['marked']['items.jsonl']/'new/deep',
        'external-quotas-marker':c['marked']['quotas.json']/'new/deep',
        'case-variant':Path(str(c['b']).swapcase())/'new/deep',
        'junction-source':c['aliases']['A']/'new/deep', 'junction-other':c['aliases']['B']/'new/deep',
        'junction-external':c['aliases']['external']/'new/deep',
        'plain-file':c['file'], 'file-ancestor':c['file']/'not-created',
    }

CASES=['source-root','source-groups','source-future-audits','other-root','other-future','batches-reserved','staging-registered','staging-unregistered','staging-future','registered-created','registered-future','external-valid','external-broken-manifest','external-items-marker','external-quotas-marker','case-variant','junction-source','junction-other','junction-external','plain-file','file-ancestor']

def protected_snapshot(c): return {str(p):tree_snapshot(p) for p in c['protected']}

def public_rejection(c,operation,destination,label):
    before=protected_snapshot(c); before_states=states(c['workspace']); error=None; result=None
    try:
        result=create_backup(c['workspace'],destination) if operation=='backup' else export_batch(c['A']['batch_id'],c['workspace'],destination)
    except Exception as e: error=dict(type=type(e).__name__,message=str(e))
    after=protected_snapshot(c); after_states=states(c['workspace'])
    record=dict(operation=operation,destination=str(destination),error=error,result=result,trees_equal=before==after,states_equal=before_states==after_states,
                before=before,after=after,before_states=before_states,after_states=after_states)
    save(c['base']/'evidence'/f'{label}.json',record)
    # Separate assertions prove the old version fails because it writes actual
    # directories/files or incorrectly succeeds, never because a new import is absent.
    assert error is not None and error['type']=='ValueError',record.get('result') or error
    assert before==after,'Invalid destination polluted protected tree; see '+str(c['base']/'evidence'/f'{label}.json')
    assert before_states==after_states,'Valid batch status changed'

def test_public_backup_rejects_before_target_write():
    c=prepare_context(QA/'source'/('backup-regression-'+uuid.uuid4().hex),source_generator)
    public_rejection(c,'backup',c['a'],'backup-source-root')

def test_public_export_rejects_other_batch_before_copy():
    c=prepare_context(QA/'source'/('export-regression-'+uuid.uuid4().hex),source_generator)
    public_rejection(c,'export',c['b'],'export-A-into-B')

@pytest.fixture(scope='module')
def guarded_context(): return prepare_context(QA/'source'/('matrix-'+uuid.uuid4().hex),source_generator)

@pytest.mark.parametrize('operation',['backup','export'])
@pytest.mark.parametrize('case',CASES)
def test_all_public_destinations_are_rejected_without_pollution(guarded_context,operation,case):
    c=guarded_context; public_rejection(c,operation,target_cases(c)[case],operation+'-'+case)

def test_healthy_batches_still_reverify_15_of_15(guarded_context):
    c=guarded_context
    # Tree equality is always asserted before these legitimate new audit files.
    results=[]
    for path in [c['a'],c['b'],c['external']]:
        r=verify_batch(path,c['workspace']); results.append(r)
        assert r['status']=='PASS' and r['checks_passed']==15
    assert Catalog(c['workspace']).get(c['A']['batch_id'])['status']=='COMPLETED'
    assert Catalog(c['workspace']).get(c['B']['batch_id'])['status']=='COMPLETED'
    save(c['base']/'evidence/reverify-after-rejections.json',results)

def test_normal_independent_outputs_alias_and_similar_sibling(guarded_context):
    c=guarded_context; results=[]
    for destination in [c['base']/'independent',c['normal_alias'],c['base']/'registered-other']:
        e=export_batch(c['A']['batch_id'],c['workspace'],destination)
        assert Path(e['export_dir'])==destination.resolve()/c['A']['batch_id']
        assert tree_snapshot(e['export_dir'])==tree_snapshot(c['a'])
        b=create_backup(c['workspace'],destination/'backup-root'); validate_backup(b['backup_dir'])
        assert Path(b['backup_dir']).parent==(destination/'backup-root').resolve()
        results.append(dict(export=e,backup=b))
    restored=restore_backup(results[0]['backup']['backup_dir'],c['base']/'restore')
    assert restored['status']=='RESTORED' and all(r['checks_passed']==15 for r in restored['batches'])
    save(c['base']/'evidence/normal-and-restore.json',dict(results=results,restored=restored))

def test_guard_is_read_only_and_returns_resolved_paths(guarded_context,monkeypatch):
    from number_app.storage.output_paths import ensure_safe_output_paths
    c=guarded_context; before=tree_snapshot(c['base'])
    def no_write(*args,**kwargs): raise AssertionError('read-only guard attempted a write/database operation')
    with monkeypatch.context() as patch:
        patch.setattr(Path,'mkdir',no_write); patch.setattr(sqlite3,'connect',no_write)
        root,target=ensure_safe_output_paths(c['normal_alias']/'future',c['normal_alias']/'future/new',workspace_root=c['workspace'],registered_batch_dirs=[c['registered'],c['future']])
        assert root==c['normal']/'future' and target==c['normal']/'future/new'
        with pytest.raises(ValueError):
            ensure_safe_output_paths(c['base']/'safe-parent',c['aliases']['B'],workspace_root=c['workspace'],registered_batch_dirs=[c['b']])
        with pytest.raises(ValueError):
            ensure_safe_output_paths('bad\x00path','bad\x00path/child',workspace_root=c['workspace'],registered_batch_dirs=[])
    assert tree_snapshot(c['base'])==before
