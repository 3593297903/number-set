import pytest
from number_app.jobs.service import generate_batch
from number_app.spec import BatchSpec
from number_app.storage.backup import create_backup,restore_backup,validate_backup
from number_app.storage.files import load_json

def test_backup_restore_fresh15(tmp_path):
    r=generate_batch(BatchSpec(100,40),tmp_path/'daily')
    b=create_backup(tmp_path/'daily',tmp_path/'backups')
    validate_backup(b['backup_dir'])
    restored=restore_backup(b['backup_dir'],tmp_path/'restored')
    assert restored['status']=='RESTORED' and restored['batches'][0]['checks_passed']==15
    assert restored['batches'][0]['audit_id']!=r['audit_id']
    with pytest.raises(ValueError): restore_backup(b['backup_dir'],tmp_path/'daily')
