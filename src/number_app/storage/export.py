import shutil
from pathlib import Path
from number_app.storage.locking import WorkspaceLock
from number_app.storage.files import check_snapshot,digest
from number_app.storage.access import healthy_row
from number_app.storage.output_paths import ensure_safe_output_paths

def tree_fingerprints(folder):
    root=Path(folder)
    return {p.relative_to(root).as_posix():digest(p.read_bytes()) for p in root.rglob('*') if p.is_file()}

def export_batch(batch_id,data_dir,destination):
    from number_app.storage.catalog import Catalog
    c=Catalog(data_dir)
    with WorkspaceLock(data_dir):
        row=healthy_row(c,batch_id); source=Path(row['batch_dir'])
        destination_root,target=ensure_safe_output_paths(Path(destination),Path(destination)/batch_id,workspace_root=c.root,
            registered_batch_dirs=[record['batch_dir'] for record in c.list()])
        if target.exists(): raise FileExistsError('目标批次已存在，请选择另一目录')
        before=tree_fingerprints(source)
        shutil.copytree(source,target)
        check_snapshot(target,row['manifest_sha256'],row['request_sha256'])
        if tree_fingerprints(target)!=before or tree_fingerprints(source)!=before: raise ValueError('复制期间文件变化')
        return dict(status='EXPORTED',batch_id=batch_id,export_dir=str(target),files_copied=len(before))
