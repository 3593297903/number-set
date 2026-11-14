import pytest
from pathlib import Path
from number_app.jobs.service import generate_batch,verify_batch
from number_app.spec import BatchSpec
from number_app.storage.catalog import Catalog
from number_app.storage.files import load_json,canonical,digest

def test_changed_request_does_not_downgrade_trust(tmp_path):
    result=generate_batch(BatchSpec(100,40),tmp_path); root=Path(result['batch_dir'])
    request=load_json(root/'request.json'); request['batch_id']='fake-import'
    (root/'request.json').write_bytes(canonical(request))
    manifest=load_json(root/'manifest.json'); manifest['batch_id']='fake-import'
    for e in manifest['files']:
        b=(root/e['path']).read_bytes(); e.update(size=len(b),sha256=digest(b))
    (root/'manifest.json').write_bytes(canonical(manifest))
    checked=verify_batch(root,tmp_path)
    assert checked['status']=='FAIL' and checked['parameter_source']=='trusted_history'
    assert checked['batch_id']==result['batch_id'] and Catalog(tmp_path).get(result['batch_id'])['status']=='DAMAGED'

@pytest.mark.parametrize('stage',['write','commit'])
def test_io_failure_never_completed(tmp_path,monkeypatch,stage):
    import number_app.jobs.service as service
    def fail(*args,**kwargs): raise PermissionError('injected disk write/rename denied')
    monkeypatch.setattr(service,'write_candidate' if stage=='write' else 'commit_candidate',fail)
    with pytest.raises(PermissionError): generate_batch(BatchSpec(100,40),tmp_path)
    assert Catalog(tmp_path).list()[0]['status']=='FAILED'

def test_interruption_at_real_fsync_boundary(tmp_path,monkeypatch):
    import number_app.storage.files as files
    original=files.os.fsync
    def interrupt_after_sync(handle):
        original(handle)
        raise KeyboardInterrupt('interrupted after actual first-file fsync')
    monkeypatch.setattr(files.os,'fsync',interrupt_after_sync)
    with pytest.raises(KeyboardInterrupt): generate_batch(BatchSpec(100,40),tmp_path)
    row=Catalog(tmp_path).list()[0]
    assert row['status']=='INTERRUPTED'
    assert (Path(row['batch_dir'])/'request.json').exists() and not (Path(row['batch_dir'])/'manifest.json').exists()
