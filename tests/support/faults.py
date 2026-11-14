import time
import os
from number_app.storage.files import save_json

def absent_report(*args): pass
def crash_worker(*args): os._exit(41)
def slow_worker(*args): time.sleep(2)
def old_report(folder,ctx,method,round_number,execution,path):
    from number_app.jobs.audit import _worker
    _worker(folder,dict(ctx,audit_id='old-audit'),method,round_number,execution,path)

def change_report_after_read(folder,ctx,method,round_number,execution,path):
    from number_app.jobs.audit import _worker
    from pathlib import Path
    from number_app.storage.files import load_json
    _worker(folder,ctx,method,round_number,execution,path)
    if method=='C' and round_number==5:
        first=Path(path).parent/'A_1.json'; report=load_json(first); report['status']='FAIL'; save_json(first,report)

def change_files_after_read(folder,ctx,method,round_number,execution,path):
    from number_app.jobs.audit import _worker
    from pathlib import Path
    _worker(folder,ctx,method,round_number,execution,path)
    if method=='C' and round_number==5: (Path(folder)/'groups/group_001.txt').write_bytes(b'changed during audit')
