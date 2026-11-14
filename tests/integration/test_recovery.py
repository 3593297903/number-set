import pytest
from pathlib import Path
from number_app.jobs.service import generate_batch
from number_app.spec import BatchSpec
from number_app.storage.recovery import inspect_recovery,recover_batch
from number_app.storage.catalog import Catalog

@pytest.mark.parametrize('stage,ready',[('WRITING',False),('FIXED',True),('AUDITING',True),('FILES_COMMITTED',True)])
def test_interrupt_boundaries(tmp_path,stage,ready):
    def interrupt(current,path):
        if current==stage: raise KeyboardInterrupt('injected interruption')
    with pytest.raises(KeyboardInterrupt): generate_batch(BatchSpec(100,40),tmp_path,_hook=interrupt)
    pending=inspect_recovery(tmp_path)
    assert len(pending)==1 and pending[0]['can_resume']==ready
    assert Catalog(tmp_path).list()[0]['status']!='COMPLETED'
    if ready:
        r=recover_batch(pending[0]['batch_id'],tmp_path)
        assert r['status']=='COMPLETED' and r['checks_passed']==15
    else:
        with pytest.raises(ValueError): recover_batch(pending[0]['batch_id'],tmp_path)

def test_completed_damage(tmp_path):
    r=generate_batch(BatchSpec(100,40),tmp_path)
    (Path(r['batch_dir'])/'groups/group_001.txt').write_bytes(b'broken')
    inspect_recovery(tmp_path)
    assert Catalog(tmp_path).get(r['batch_id'])['status']=='DAMAGED'
