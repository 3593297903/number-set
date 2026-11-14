import os
import json
import shutil
import sqlite3
import uuid
from pathlib import Path
from number_app.storage.catalog import Catalog
from number_app.storage.files import save_json,load_json,check_snapshot,digest,now
from number_app.storage.locking import WorkspaceLock
from number_app.storage.output_paths import ensure_safe_output_paths

def _inventory(root):
    result=[]
    for p in sorted(Path(root).rglob('*')):
        if p.is_symlink(): raise ValueError('备份不接受符号链接')
        if p.is_file() and p.name!='BACKUP_COMPLETE.json':
            b=p.read_bytes(); result.append(dict(path=p.relative_to(root).as_posix(),size=len(b),sha256=digest(b)))
    return result

def validate_backup(backup_dir):
    root=Path(backup_dir).resolve(); marker=load_json(root/'BACKUP_COMPLETE.json')
    if marker['schema_version']!=1 or marker['status']!='COMPLETE': raise ValueError('备份未完成')
    if marker['files']!=_inventory(root): raise ValueError('备份文件指纹不一致')
    with sqlite3.connect(root/'history.sqlite') as db:
        db.row_factory=sqlite3.Row
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('备份数据库损坏')
        rows=[dict(r) for r in db.execute('SELECT * FROM batches')]
    if any(r['status']!='COMPLETED' for r in rows): raise ValueError('备份含非完成状态')
    expected={r['batch_id'] for r in rows}
    actual={p.name for p in (root/'batches').iterdir()} if (root/'batches').exists() else set()
    if expected!=actual: raise ValueError('备份目录与索引不一致')
    for r in rows: check_snapshot(root/'batches'/r['batch_id'],r['manifest_sha256'],r['request_sha256'])
    return marker,rows

def create_backup(data_dir,backup_root):
    c=Catalog(data_dir); backup_root=Path(backup_root)
    backup_id=now()[:19].replace(':','').replace('-','').replace('T','_')+'_'+uuid.uuid4().hex[:8]
    target=backup_root/backup_id
    with WorkspaceLock(data_dir):
        try:
            backup_root,target=ensure_safe_output_paths(backup_root,target,workspace_root=c.root,
                registered_batch_dirs=[row['batch_dir'] for row in c.list()])
            backup_root.mkdir(parents=True,exist_ok=True); target.mkdir(exist_ok=False)
            with c.connect() as src,sqlite3.connect(target/'history.sqlite') as dst:
                src.backup(dst)
                dst.execute("DELETE FROM batches WHERE status != 'COMPLETED'")
                for table in ('group_quotas','artifacts','audit_runs'):
                    dst.execute(f'DELETE FROM {table} WHERE batch_id NOT IN (SELECT batch_id FROM batches)')
                dst.execute('DELETE FROM audit_checks WHERE audit_id NOT IN (SELECT audit_id FROM audit_runs)')
                dst.commit()
                dst.row_factory=sqlite3.Row; rows=[dict(r) for r in dst.execute('SELECT * FROM batches')]
            for row in rows:
                source=Path(row['batch_dir']).resolve()
                if backup_root.is_relative_to(source): raise ValueError('备份目录不能在批次内部')
                check_snapshot(source,row['manifest_sha256'],row['request_sha256'])
                shutil.copytree(source,target/'batches'/row['batch_id'])
                check_snapshot(target/'batches'/row['batch_id'],row['manifest_sha256'],row['request_sha256'])
            (target/'batches').mkdir(exist_ok=True)
            inventory=_inventory(target)
            for f in inventory:
                with (target/f['path']).open('rb+') as stream: stream.flush(); os.fsync(stream.fileno())
            save_json(target/'BACKUP_COMPLETE.json',dict(schema_version=1,status='COMPLETE',backup_id=backup_id,created_at=now(),files=inventory))
            validate_backup(target)
            with c.connect() as db: db.execute('INSERT INTO backup_runs VALUES(?,?,?,?,?)',(backup_id,now(),'COMPLETE',str(target),''))
            return dict(status='BACKUP_COMPLETE',backup_id=backup_id,backup_dir=str(target),batch_count=len(rows))
        except Exception as e:
            with c.connect() as db: db.execute('INSERT OR REPLACE INTO backup_runs VALUES(?,?,?,?,?)',(backup_id,now(),'FAILED',str(target),str(e)))
            raise

def auto_backup(data_dir):
    c=Catalog(data_dir); today=now()[:10]
    if c.setting('last_auto_backup_date')==today:
        return dict(backup_status='DAILY_BACKUP_ALREADY_EXISTS',backup_note='今日首次完成备份已存在；新增批次可在设置中手动备份')
    root=c.setting('backup_root',str(Path(data_dir).resolve().parent/(Path(data_dir).name+'_backups')))
    try:
        result=create_backup(data_dir,root); c.set_setting('last_auto_backup_date',today)
        return dict(backup_status='COMPLETE',backup_dir=result['backup_dir'])
    except Exception as e: return dict(backup_status='FAILED',backup_error=str(e))

def restore_backup(backup_dir,destination,*,progress=None,cancel=None):
    backup=Path(backup_dir).resolve(); target=Path(destination).resolve()
    marker,rows=validate_backup(backup)
    if target.exists() and any(target.iterdir()): raise ValueError('恢复目标必须为空目录，以保留现有数据')
    if target.is_relative_to(backup): raise ValueError('恢复目标不能在备份内部')
    target.mkdir(parents=True,exist_ok=True)
    # Rebase and invalidate the copied index before publishing history.sqlite.
    # Killing restoration at any copy boundary cannot expose COMPLETED rows.
    with WorkspaceLock(target):
        staged=target/'.restore-index.sqlite'
        shutil.copy2(backup/'history.sqlite',staged)
        with sqlite3.connect(staged) as db:
            for row in rows: db.execute("UPDATE batches SET batch_dir=?,status='INTERRUPTED',message='备份恢复待完整审查' WHERE batch_id=?",(str(target/'batches'/row['batch_id']),row['batch_id']))
        db.close(); os.replace(staged,target/'history.sqlite')
        shutil.copytree(backup/'batches',target/'batches')
    from number_app.storage.recovery import recover_batch
    results=[]
    for row in rows:
        results.append(recover_batch(row['batch_id'],target,progress=progress,cancel=cancel))
        if results[-1]['status']!='COMPLETED': raise ValueError('恢复复核失败')
    result=dict(status='RESTORED',backup_id=marker['backup_id'],data_dir=str(target),batches=results)
    save_json(target/'restore_result.json',result)
    return result
