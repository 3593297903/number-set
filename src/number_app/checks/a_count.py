"""A: full-line regular expressions and weighted 1000-slot counting.
No imports from generation, storage validators, B, or C.
"""
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from .reports import report_for

def _pairs(pairs):
    d={}
    for k,v in pairs:
        if k in d: raise ValueError('A duplicate JSON key '+k)
        d[k]=v
    return d

def parse_a(data,copies):
    if not data or not data.endswith(b'\n') or b'\r' in data or data.startswith(b'\xef\xbb\xbf'):
        raise ValueError('A UTF8/LF protocol')
    counts=[0]*1000; previous=0; total=0
    for index,line in enumerate(data[:-1].split(b'\n'),1):
        if len(line)>8192: raise ValueError('A long line')
        text=line.decode('utf-8')
        match=re.fullmatch(r'([0-9]{3}(?:\.[0-9]{3})*)直选([1-9][0-9]*)元',text)
        if not match or len(match[2])>3: raise ValueError(f'A syntax line {index}')
        amount=int(match[2])
        if not previous<amount<=copies: raise ValueError('A amount order/range')
        previous=amount
        for code in match[1].split('.'):
            n=int(code)
            if counts[n]: raise ValueError('A duplicate code '+code)
            counts[n]=amount; total+=amount
            if total>copies*1000: raise ValueError('A expansion limit')
    return counts,total

def check_a(batch_dir,context,round=1,execution_id=None):
    def work(ctx):
        root=Path(batch_dir).resolve(); s=ctx['copies']; k=ctx['group_count']; n=s*1000
        if type(s) is not int or type(k) is not int or not 100<=s<=300 or not 40<=k<=300: raise ValueError('A input')
        mb=(root/'manifest.json').read_bytes()
        if hashlib.sha256(mb).hexdigest()!=ctx['expected_manifest_sha256']: raise ValueError('A manifest fingerprint')
        m=json.loads(mb,object_pairs_hook=_pairs)
        if mb!=(json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode(): raise ValueError('A manifest encoding')
        if type(m['schema_version']) is not int or m['schema_version']!=1 or m['batch_id']!=ctx['batch_id']: raise ValueError('A manifest identity')
        names={'request.json','quotas.json','items.jsonl'}|{f'groups/group_{i:03}.txt' for i in range(1,k+1)}
        if len(m['files'])!=len(names) or {e['path'] for e in m['files']}!=names: raise ValueError('A manifest paths')
        actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.relative_to(root).parts[0]!='audits'}
        if actual!=names|{'manifest.json'}: raise ValueError('A file set')
        blobs={}
        for e in m['files']:
            p=root/e['path']
            if p.is_symlink() or not p.resolve().is_relative_to(root) or p.stat().st_size>64000000: raise ValueError('A unsafe file')
            b=p.read_bytes()
            if type(e['size']) is not int or len(b)!=e['size'] or hashlib.sha256(b).hexdigest()!=e['sha256']: raise ValueError('A fingerprint '+e['path'])
            blobs[e['path']]=b
        rb=blobs['request.json']; r=json.loads(rb,object_pairs_hook=_pairs)
        if hashlib.sha256(rb).hexdigest()!=ctx['expected_request_sha256']: raise ValueError('A request fingerprint')
        if type(r['copies']) is not int or type(r['group_count']) is not int or (r['copies'],r['group_count'],r['batch_id'])!=(s,k,ctx['batch_id']): raise ValueError('A request mismatch')
        if type(r['schema_version']) is not int or (r['schema_version'],r['rules_version'],r['algorithm_version'],r['format_version'])!=(1,'rules_v1','quota_pair_v1','direct_amount_v1'): raise ValueError('A version')
        if not isinstance(r['created_at'],str) or datetime.fromisoformat(r['created_at']).utcoffset() is None: raise ValueError('A created_at timezone')
        q=json.loads(blobs['quotas.json'],object_pairs_hook=_pairs)
        if type(q['schema_version']) is not int or q['schema_version']!=1 or q['batch_id']!=ctx['batch_id'] or len(q['groups'])!=k: raise ValueError('A quota identity')
        quota={}; units=[]
        for g in q['groups']:
            i=g['group']; v=g['raw_count']; u=g['display_percent_units']
            if any(type(x) is not int for x in (i,v,u)) or i in quota or not 1<=i<=k or not 2*s<=v<=30*s: raise ValueError('A quota range')
            quota[i]=v; units.append(u)
        if sum(quota.values())!=n or sum(units)!=100000000: raise ValueError('A quota sum')
        ordered=sorted(q['groups'],key=lambda g:g['group'])
        display=[g['raw_count']*100000000//n for g in ordered]
        ranking=sorted(range(k),key=lambda j:(-(ordered[j]['raw_count']*100000000%n),j))
        for j in ranking[:100000000-sum(display)]: display[j]+=1
        if display!=[g['display_percent_units'] for g in ordered]: raise ValueError('A displayed percentages')
        totals=[0]*1000; raw=0; groups=[]
        for i in range(1,k+1):
            counts,size=parse_a(blobs[f'groups/group_{i:03}.txt'],s)
            if size!=quota[i]: raise ValueError(f'A group {i} raw count expected {quota[i]}, actual {size}')
            for code,value in enumerate(counts): totals[code]+=value
            raw+=size; groups.append(size)
        if raw!=n: raise ValueError('A total')
        for code,value in enumerate(totals):
            if value!=s: raise ValueError(f'A code {code:03} expected {s}, actual {value}')
        return dict(actual_total=raw,actual_group_count=k,counts=totals,group_raw_counts=groups,files_read=len(blobs)+1,bytes_read=len(mb)+sum(map(len,blobs.values())))
    return report_for('A',context,round,execution_id,work)
