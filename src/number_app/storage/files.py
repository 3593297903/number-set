import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

def now(): return datetime.now(timezone(timedelta(hours=8))).isoformat()
def digest(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')
def unique_pairs(pairs):
    result={}
    for k,v in pairs:
        if k in result: raise ValueError('重复JSON键: '+k)
        result[k]=v
    return result
def load_json(path): return json.loads(Path(path).read_bytes(),object_pairs_hook=unique_pairs)
def write_bytes(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
def save_json(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.tmp')
    with temp.open('wb') as f:
        f.write(canonical(value)); f.flush(); os.fsync(f.fileno())
    os.replace(temp,path)
def data_paths(k):
    return ['request.json','quotas.json','items.jsonl']+[f'groups/group_{i:03}.txt' for i in range(1,k+1)]
def check_snapshot(folder,expected_manifest=None,expected_request=None):
    folder=Path(folder).resolve()
    mb=(folder/'manifest.json').read_bytes()
    if expected_manifest and digest(mb)!=expected_manifest: raise ValueError('清单指纹变化')
    m=json.loads(mb,object_pairs_hook=unique_pairs)
    if mb!=canonical(m): raise ValueError('清单非规范JSON')
    req=load_json(folder/'request.json'); k=req['group_count']
    from number_app.spec import BatchSpec
    BatchSpec(req['copies'],k)
    expected=set(data_paths(k))
    entries=m['files']
    if len(entries)!=len(expected) or {e['path'] for e in entries}!=expected: raise ValueError('清单集合错误')
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.relative_to(folder).parts[0]!='audits'}
    if actual!=expected|{'manifest.json'}: raise ValueError('实际文件集合错误')
    for e in entries:
        p=folder/e['path']
        if p.is_symlink() or not p.resolve().is_relative_to(folder): raise ValueError('越界文件')
        b=p.read_bytes()
        if len(b)!=e['size'] or digest(b)!=e['sha256']: raise ValueError('文件指纹变化: '+e['path'])
    if expected_request and digest((folder/'request.json').read_bytes())!=expected_request: raise ValueError('参数指纹变化')
    return req,m
