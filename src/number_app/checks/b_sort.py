"""B: delimiter parsing, bounded expansion and sorted multiset equality."""
from pathlib import Path
from hashlib import sha256
from json import loads,dumps
from datetime import datetime
from .reports import report_for

def _object(entries):
    if len({key for key,_ in entries})!=len(entries): raise ValueError('B duplicate JSON key')
    return dict(entries)

def parse_b(raw,s):
    text=raw.decode('utf-8')
    if not text.endswith('\n') or text.startswith('\ufeff') or '\r' in text: raise ValueError('B text encoding')
    used=set(); result=[]; prior=0
    for line in text.split('\n')[:-1]:
        if len(line.encode('utf-8'))>8192: raise ValueError('B long line')
        parts=line.split('直选')
        if len(parts)!=2 or not parts[1].endswith('元'): raise ValueError('B syntax')
        amount_text=parts[1][:-1]
        if not 1<=len(amount_text)<=3 or amount_text[0]=='0' or any(c not in '0123456789' for c in amount_text): raise ValueError('B amount digits')
        amount=int(amount_text)
        if amount<=prior or amount>s: raise ValueError('B amount order/range')
        prior=amount; codes=parts[0].split('.')
        if len(result)+len(codes)*amount>s*1000: raise ValueError('B expansion cap')
        for code in codes:
            if len(code)!=3 or any(c not in '0123456789' for c in code) or code in used: raise ValueError('B code/duplicate')
            used.add(code); result.extend([code]*amount)
    return result

def check_b(batch_dir,context,round=1,execution_id=None):
    def calculate(c):
        base=Path(batch_dir).resolve(); copies=c['copies']; count=c['group_count']
        if type(copies)!=int or type(count)!=int or copies not in range(100,301) or count not in range(40,301): raise ValueError('B parameters')
        manifest_bytes=(base/'manifest.json').read_bytes()
        if sha256(manifest_bytes).hexdigest()!=c['expected_manifest_sha256']: raise ValueError('B snapshot fingerprint')
        inventory=loads(manifest_bytes,object_pairs_hook=_object)
        if manifest_bytes!=(dumps(inventory,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode(): raise ValueError('B manifest canonical')
        if type(inventory.get('schema_version'))!=int or inventory.get('schema_version')!=1 or inventory.get('batch_id')!=c['batch_id']: raise ValueError('B inventory version')
        wanted=['request.json','quotas.json','items.jsonl']
        wanted.extend('groups/group_%03d.txt'%j for j in range(1,count+1))
        paths=[e['path'] for e in inventory['files']]
        if sorted(paths)!=sorted(wanted): raise ValueError('B paths')
        disk=[]
        for p in base.rglob('*'):
            rel=p.relative_to(base)
            if p.is_file() and rel.parts[0]!='audits': disk.append(rel.as_posix())
        if sorted(disk)!=sorted(wanted+['manifest.json']): raise ValueError('B actual files')
        data={}
        for entry in inventory['files']:
            target=base.joinpath(entry['path'])
            if target.is_symlink() or not target.resolve().is_relative_to(base) or target.stat().st_size>64000000: raise ValueError('B unsafe path/size')
            payload=target.read_bytes()
            if type(entry['size'])!=int or entry['size']!=len(payload) or entry['sha256']!=sha256(payload).hexdigest(): raise ValueError('B file fingerprint '+entry['path'])
            data[entry['path']]=payload
        request=loads(data['request.json'],object_pairs_hook=_object)
        if sha256(data['request.json']).hexdigest()!=c['expected_request_sha256']: raise ValueError('B request fingerprint')
        for key,val in [('copies',copies),('group_count',count)]:
            if type(request.get(key))!=int or request[key]!=val: raise ValueError('B request '+key)
        for key,val in [('batch_id',c['batch_id']),('schema_version',1),('rules_version','rules_v1'),('algorithm_version','quota_pair_v1'),('format_version','direct_amount_v1')]:
            if type(request.get(key))!=type(val) or request.get(key)!=val: raise ValueError('B version/identity '+key)
        timestamp=request['created_at']
        if type(timestamp)!=str or datetime.fromisoformat(timestamp).tzinfo is None: raise ValueError('B timestamp timezone')
        quota_document=loads(data['quotas.json'],object_pairs_hook=_object)
        if quota_document['batch_id']!=c['batch_id'] or type(quota_document['schema_version'])!=int or quota_document['schema_version']!=1: raise ValueError('B quotas identity')
        records=quota_document['groups']; by_group={}
        for record in records:
            group,quantity,display=(record[v] for v in ('group','raw_count','display_percent_units'))
            if any(type(v)!=int for v in (group,quantity,display)): raise ValueError('B quota integer')
            if group in by_group or not 1<=group<=count or not 2*copies<=quantity<=30*copies: raise ValueError('B quota bounds')
            by_group[group]=quantity
        if len(by_group)!=count or sum(by_group.values())!=1000*copies or sum(r['display_percent_units'] for r in records)!=100000000: raise ValueError('B quota totals')
        division={g:divmod(size*100000000,1000*copies) for g,size in by_group.items()}
        residual=100000000-sum(v[0] for v in division.values())
        increments=set(sorted(division,key=lambda g:(-division[g][1],g))[:residual])
        if any(r['display_percent_units']!=division[r['group']][0]+(r['group'] in increments) for r in records): raise ValueError('B rounded percentages')
        expanded=[]; group_sizes=[]
        for group in range(1,count+1):
            part=parse_b(data['groups/group_%03d.txt'%group],copies)
            if len(part)!=by_group[group]: raise ValueError('B raw group count '+str(group))
            if len(expanded)+len(part)>1000*copies: raise ValueError('B global expansion cap')
            group_sizes.append(len(part)); expanded+=part
        standard=[str(number).zfill(3) for number in range(1000) for _ in range(copies)]
        expanded.sort()
        if len(expanded)!=len(standard): raise ValueError('B total length')
        for pos,(actual,expected) in enumerate(zip(expanded,standard)):
            if actual!=expected: raise ValueError(f'B sorted mismatch {pos}: {actual}/{expected}')
        return dict(actual_total=len(expanded),actual_group_count=len(by_group),group_raw_counts=group_sizes,files_read=len(data)+1,bytes_read=len(manifest_bytes)+sum(len(v) for v in data.values()))
    return report_for('B',context,round,execution_id,calculate)
