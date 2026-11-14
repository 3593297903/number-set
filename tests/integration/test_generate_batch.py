from number_app.spec import BatchSpec
from number_app.jobs.service import generate_batch
from number_app.storage.catalog import Catalog
from number_app.storage.files import load_json,check_snapshot

def test_max_full(tmp_path):
    r=generate_batch(BatchSpec(300,300),tmp_path)
    assert r['status']=='COMPLETED' and r['checks_passed']==15 and r['total_items']==300000
    row=Catalog(tmp_path).get(r['batch_id'])
    assert row['status']=='COMPLETED'
    check_snapshot(r['batch_dir'],row['manifest_sha256'],row['request_sha256'])
