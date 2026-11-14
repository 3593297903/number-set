import sqlite3
import json
from pathlib import Path
from number_app.jobs.state import require_transition
from number_app.storage.files import now

class Catalog:
    def __init__(self,data_dir):
        self.root=Path(data_dir).resolve(); self.root.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            if db.execute('PRAGMA user_version').fetchone()[0] not in (0,1): raise ValueError('不支持该历史数据库版本')
            db.executescript('''
            CREATE TABLE IF NOT EXISTS batches(
              batch_id TEXT PRIMARY KEY,copies INTEGER NOT NULL,group_count INTEGER NOT NULL,
              status TEXT NOT NULL,batch_dir TEXT NOT NULL,created_at TEXT NOT NULL,
              software_version TEXT NOT NULL,request_sha256 TEXT,manifest_sha256 TEXT,
              last_audit_id TEXT,message TEXT DEFAULT '');
            CREATE TABLE IF NOT EXISTS group_quotas(batch_id TEXT,group_no INTEGER,raw_count INTEGER,display_units INTEGER,PRIMARY KEY(batch_id,group_no));
            CREATE TABLE IF NOT EXISTS audit_runs(audit_id TEXT PRIMARY KEY,batch_id TEXT,status TEXT,summary_json TEXT);
            CREATE TABLE IF NOT EXISTS audit_checks(audit_id TEXT,method TEXT,round INTEGER,report_json TEXT,PRIMARY KEY(audit_id,method,round));
            CREATE TABLE IF NOT EXISTS artifacts(batch_id TEXT,path TEXT,size INTEGER,sha256 TEXT,PRIMARY KEY(batch_id,path));
            CREATE TABLE IF NOT EXISTS backup_runs(backup_id TEXT PRIMARY KEY,created_at TEXT,status TEXT,path TEXT,message TEXT);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
            PRAGMA user_version=1;
            ''')

    def connect(self):
        db=sqlite3.connect(self.root/'history.sqlite',timeout=30)
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        return db

    def add(self,batch_id,spec,path,created_at):
        from number_app import __version__
        with self.connect() as db:
            db.execute('INSERT INTO batches(batch_id,copies,group_count,status,batch_dir,created_at,software_version) VALUES(?,?,?,?,?,?,?)',
                       (batch_id,spec.copies,spec.group_count,'CREATED',str(path),created_at,__version__))

    def get(self,batch_id):
        with self.connect() as db:
            row=db.execute('SELECT * FROM batches WHERE batch_id=?',(batch_id,)).fetchone()
            return dict(row) if row else None

    def list(self):
        with self.connect() as db: return [dict(r) for r in db.execute('SELECT * FROM batches ORDER BY created_at DESC')]

    def update(self,batch_id,**values):
        allowed={'status','batch_dir','request_sha256','manifest_sha256','last_audit_id','message'}
        if not values or not set(values)<=allowed: raise ValueError('非法历史字段')
        with self.connect() as db:
            row=db.execute('SELECT status FROM batches WHERE batch_id=?',(batch_id,)).fetchone()
            if not row: raise ValueError('批次不存在')
            if 'status' in values: require_transition(row['status'],values['status'])
            db.execute('UPDATE batches SET '+','.join(k+'=?' for k in values)+' WHERE batch_id=?',(*values.values(),batch_id))

    def fix(self,batch_id,context,quotas,manifest):
        with self.connect() as db:
            db.execute('UPDATE batches SET request_sha256=?,manifest_sha256=? WHERE batch_id=?',
                       (context['expected_request_sha256'],context['expected_manifest_sha256'],batch_id))
            for g in quotas['groups']:
                db.execute('INSERT OR REPLACE INTO group_quotas VALUES(?,?,?,?)',(batch_id,g['group'],g['raw_count'],g['display_percent_units']))
            for f in manifest['files']: db.execute('INSERT OR REPLACE INTO artifacts VALUES(?,?,?,?)',(batch_id,f['path'],f['size'],f['sha256']))

    def record_audit(self,summary):
        with self.connect() as db:
            db.execute('INSERT INTO audit_runs VALUES(?,?,?,?)',(summary['audit_id'],summary['batch_id'],summary['status'],json.dumps(summary,ensure_ascii=False)))
            for r in summary['checks']: db.execute('INSERT INTO audit_checks VALUES(?,?,?,?)',(summary['audit_id'],r['method'],r['round'],json.dumps(r,ensure_ascii=False)))

    def setting(self,key,default=None):
        with self.connect() as db:
            row=db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
            return row[0] if row else default
    def set_setting(self,key,value):
        with self.connect() as db: db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,str(value)))
