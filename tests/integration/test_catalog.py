import sqlite3
import pytest
from number_app.storage.catalog import Catalog
from number_app.storage.locking import WorkspaceLock
from number_app.spec import BatchSpec

def test_states_and_unique(tmp_path):
    c=Catalog(tmp_path); c.add('one',BatchSpec(100,40),tmp_path/'one','2026-11-14')
    with pytest.raises(ValueError): c.update('one',status='COMPLETED')
    c.update('one',status='GENERATING')
    assert c.get('one')['status']=='GENERATING'
    with c.connect() as db:
        db.execute("INSERT INTO audit_checks VALUES('a','A',1,'{}')")
        with pytest.raises(sqlite3.IntegrityError): db.execute("INSERT INTO audit_checks VALUES('a','A',1,'{}')")
    with WorkspaceLock(tmp_path):
        with pytest.raises(RuntimeError):
            with WorkspaceLock(tmp_path): pass
