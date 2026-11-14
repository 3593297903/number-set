from pathlib import Path
import pytest
from number_app.jobs.service import generate_batch
from number_app.spec import BatchSpec
from number_app.storage.export import export_batch,tree_fingerprints

def test_export_fixed_bytes_and_damage(tmp_path):
    root=tmp_path/'data'; r=generate_batch(BatchSpec(100,40),root)
    out=export_batch(r['batch_id'],root,tmp_path/'export')
    assert tree_fingerprints(out['export_dir'])==tree_fingerprints(r['batch_dir'])
    (Path(r['batch_dir'])/'groups/group_001.txt').write_bytes(b'corrupt')
    with pytest.raises(ValueError): export_batch(r['batch_id'],root,tmp_path/'export2')
