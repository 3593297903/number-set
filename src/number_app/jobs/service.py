import time
import uuid
from pathlib import Path
from number_app.spec import BatchSpec
from number_app.core.quota import generate_quotas
from number_app.core.pool import shuffle_ids
from number_app.artifacts import write_candidate
from number_app.jobs.audit import audit_batch
from number_app.storage.files import now,load_json,check_snapshot,digest
from number_app.storage.catalog import Catalog
from number_app.storage.locking import WorkspaceLock
from number_app.storage.commit import commit_candidate

class Cancelled(Exception): pass

def _context(row):
    return dict(batch_id=row['batch_id'],copies=row['copies'],group_count=row['group_count'],
                expected_request_sha256=row['request_sha256'],expected_manifest_sha256=row['manifest_sha256'],checker_version='2.0.0')

def _generate_batch(spec,data_dir,*,progress=None,cancel=None,_hook=None):
    if not isinstance(spec,BatchSpec): raise ValueError('需要BatchSpec')
    data_dir=Path(data_dir).resolve(); catalog=Catalog(data_dir); start=time.monotonic()
    batch_id=now()[:19].replace(':','').replace('-','').replace('T','_')+'_'+uuid.uuid4().hex[:12]
    path=data_dir/'staging'/batch_id; created=now()
    def phase(state):
        catalog.update(batch_id,status=state)
        if progress: progress(dict(stage=state,batch_id=batch_id,batch_dir=str(path)))
        if _hook: _hook(state,path)
        if cancel and cancel.is_set(): raise Cancelled('任务已取消')
    with WorkspaceLock(data_dir):
        catalog.add(batch_id,spec,path,created)
        try:
            phase('GENERATING'); quotas=generate_quotas(spec); ids=shuffle_ids(spec)
            phase('WRITING')
            ctx=write_candidate(path,spec,quotas,ids,batch_id=batch_id,created_at=created)
            del ids
            ctx.update(copies=spec.copies,group_count=spec.group_count,checker_version='2.0.0')
            catalog.fix(batch_id,ctx,load_json(path/'quotas.json'),load_json(path/'manifest.json'))
            if _hook: _hook('FIXED',path)
            phase('AUDITING')
            summary=audit_batch(path,ctx,progress=progress,cancel=cancel); catalog.record_audit(summary)
            catalog.update(batch_id,last_audit_id=summary['audit_id'])
            if summary['status']!='PASS':
                state='CANCELLED' if summary['status']=='CANCELLED' else 'FAILED'
                catalog.update(batch_id,status=state,message='15次审查未全部通过')
                return dict(status=state,batch_id=batch_id,batch_dir=str(path),audit_id=summary['audit_id'],checks_passed=summary['checks_passed'])
            phase('COMMITTING'); path=commit_candidate(path,data_dir,ctx)
            if _hook: _hook('FILES_COMMITTED',path)
            catalog.update(batch_id,batch_dir=str(path),status='COMPLETED')
            if _hook: _hook('DB_COMMITTED',path)
            result=dict(status='COMPLETED',batch_id=batch_id,batch_dir=str(path),audit_id=summary['audit_id'],copies=spec.copies,
                        group_count=spec.group_count,total_items=spec.total,checks_passed=15,duration_ms=int((time.monotonic()-start)*1000))
            if progress: progress(dict(stage='COMPLETED',**result))
            return result
        except BaseException as e:
            row=catalog.get(batch_id)
            if row['status']!='COMPLETED':
                state='CANCELLED' if isinstance(e,Cancelled) else 'INTERRUPTED' if isinstance(e,(KeyboardInterrupt,SystemExit)) else 'FAILED'
                catalog.update(batch_id,status=state,message=str(e))
            raise

def generate_batch(spec,data_dir,*,progress=None,cancel=None,_hook=None):
    result=_generate_batch(spec,data_dir,progress=progress,cancel=cancel,_hook=_hook)
    if result['status']=='COMPLETED':
        from number_app.storage.backup import auto_backup
        if progress: progress(dict(stage='BACKUP',status='RUNNING'))
        result.update(auto_backup(data_dir))
    return result

def verify_batch(batch_dir,data_dir,*,progress=None,cancel=None):
    folder=Path(batch_dir).resolve(); catalog=Catalog(data_dir)
    with WorkspaceLock(data_dir):
        # Locate the owning history by its actual path, before reading untrusted
        # declarations. A changed batch_id must never downgrade trust to import.
        row=next((r for r in catalog.list() if Path(r['batch_dir']).resolve()==folder),None)
        trusted=bool(row and row['manifest_sha256'] and row['request_sha256'])
        if trusted:
            ctx=_context(row); bid=row['batch_id']
        else:
            request=load_json(folder/'request.json'); spec=BatchSpec(request['copies'],request['group_count']); bid=request['batch_id']
            ctx=dict(batch_id=bid,copies=spec.copies,group_count=spec.group_count,
                 expected_request_sha256=digest((folder/'request.json').read_bytes()),expected_manifest_sha256=digest((folder/'manifest.json').read_bytes()),checker_version='2.0.0')
        summary=audit_batch(folder,ctx,progress=progress,cancel=cancel)
        summary['parameter_source']='trusted_history' if trusted else 'imported_declaration_only'
        catalog.record_audit(summary)
        if trusted:
            values=dict(last_audit_id=summary['audit_id'])
            if summary['status']=='FAIL' and row['status']=='COMPLETED': values.update(status='DAMAGED',message='完整复核不通过')
            catalog.update(bid,**values)
        return dict(status=summary['status'],batch_id=bid,batch_dir=str(folder),audit_id=summary['audit_id'],
                    copies=ctx['copies'],group_count=ctx['group_count'],total_items=ctx['copies']*1000,
                    checks_passed=summary['checks_passed'],parameter_source=summary['parameter_source'])
