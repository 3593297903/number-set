from pathlib import Path
from number_app.storage.catalog import Catalog
from number_app.storage.locking import WorkspaceLock
from number_app.storage.files import check_snapshot
from number_app.storage.commit import commit_candidate
from number_app.jobs.audit import audit_batch
from number_app.jobs.service import _context

ACTIVE={'CREATED','GENERATING','WRITING','AUDITING','COMMITTING'}

def inspect_recovery(data_dir):
    c=Catalog(data_dir); result=[]
    with WorkspaceLock(data_dir):
        for row in c.list():
            path=Path(row['batch_dir'])
            final=c.root/'batches'/row['batch_id']
            if not path.exists() and final.exists():
                path=final; c.update(row['batch_id'],batch_dir=str(path))
            if row['status'] in ACTIVE:
                c.update(row['batch_id'],status='INTERRUPTED',message='上次任务未正常完成')
                row['status']='INTERRUPTED'
            if row['status']=='COMPLETED':
                try: check_snapshot(path,row['manifest_sha256'],row['request_sha256'])
                except Exception as e:
                    c.update(row['batch_id'],status='DAMAGED',message=str(e)); row['status']='DAMAGED'
            if row['status'] not in {'COMPLETED','DAMAGED'}:
                ready=False; reason='尚未形成固定完整数据，请新建批次'
                if row['manifest_sha256'] and row['request_sha256']:
                    try:
                        check_snapshot(path,row['manifest_sha256'],row['request_sha256']); ready=True; reason='可重新执行15次完整审查'
                    except Exception as e: reason=str(e)
                result.append(dict(batch_id=row['batch_id'],batch_dir=str(path),status=row['status'],can_resume=ready,message=reason))
    return result

def recover_batch(batch_id,data_dir,*,progress=None,cancel=None):
    c=Catalog(data_dir)
    with WorkspaceLock(data_dir):
        row=c.get(batch_id)
        if not row or row['status']=='COMPLETED': raise ValueError('没有待恢复批次')
        path=Path(row['batch_dir']).resolve(); final=c.root/'batches'/batch_id
        if not path.exists() and final.exists(): path=final
        if path not in [(c.root/'staging'/batch_id).resolve(),final.resolve()]: raise ValueError('恢复路径不属于本数据目录')
        if not row['manifest_sha256'] or not row['request_sha256']: raise ValueError('固定数据不完整，必须新建批次')
        check_snapshot(path,row['manifest_sha256'],row['request_sha256'])
        if row['status'] in ACTIVE: c.update(batch_id,status='INTERRUPTED')
        c.update(batch_id,status='AUDITING',batch_dir=str(path))
        ctx=_context(row); summary=audit_batch(path,ctx,progress=progress,cancel=cancel); c.record_audit(summary)
        c.update(batch_id,last_audit_id=summary['audit_id'])
        if summary['status']!='PASS':
            c.update(batch_id,status='CANCELLED' if summary['status']=='CANCELLED' else 'FAILED')
            return dict(status=summary['status'],checks_passed=summary['checks_passed'],batch_id=batch_id,audit_id=summary['audit_id'])
        c.update(batch_id,status='COMMITTING')
        if path!=final: path=commit_candidate(path,c.root,ctx)
        check_snapshot(path,row['manifest_sha256'],row['request_sha256'])
        c.update(batch_id,status='COMPLETED',batch_dir=str(path),message='中断恢复后重新15次审查通过')
        return dict(status='COMPLETED',batch_id=batch_id,batch_dir=str(path),checks_passed=15,audit_id=summary['audit_id'],copies=row['copies'],group_count=row['group_count'],total_items=row['copies']*1000)
