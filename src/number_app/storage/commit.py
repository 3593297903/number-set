from pathlib import Path
from .files import check_snapshot

def commit_candidate(source,data_dir,context):
    source=Path(source); target=Path(data_dir)/'batches'/context['batch_id']
    check_snapshot(source,context['expected_manifest_sha256'],context['expected_request_sha256'])
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists(): raise FileExistsError('正式目录已存在')
    source.replace(target)
    check_snapshot(target,context['expected_manifest_sha256'],context['expected_request_sha256'])
    return target
