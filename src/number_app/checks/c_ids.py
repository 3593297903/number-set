"""C: exact unique-ID bitmap and independent direct-text reconstruction."""
import json
import hashlib
import datetime
from pathlib import Path
from .reports import report_for

def _json(payload):
    def reject_duplicate(pairs):
        obj={}
        for name,value in pairs:
            if name in obj: raise ValueError('C duplicate JSON key')
            obj[name]=value
        return obj
    return json.loads(payload,object_pairs_hook=reject_duplicate)

def check_c(batch_dir,context,round=1,execution_id=None):
    def examine(context):
        home=Path(batch_dir).resolve(); s=context['copies']; k=context['group_count']; n=1000*s
        if type(s) is not int or type(k) is not int or not (100<=s<=300 and 40<=k<=300): raise ValueError('C original parameters')
        manifest_raw=(home/'manifest.json').read_bytes(); manifest=_json(manifest_raw)
        hash_of=lambda b:hashlib.sha256(b).hexdigest()
        if hash_of(manifest_raw)!=context['expected_manifest_sha256']: raise ValueError('C manifest fingerprint')
        if (json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')!=manifest_raw: raise ValueError('C noncanonical manifest')
        if type(manifest['schema_version']) is not int or manifest['schema_version']!=1 or manifest['batch_id']!=context['batch_id']: raise ValueError('C manifest identity')
        allowed={'items.jsonl','request.json','quotas.json'}
        for number in range(k): allowed.add(f'groups/group_{number+1:03d}.txt')
        seen_paths=set(); content={}
        for row in manifest['files']:
            name=row['path']
            if name not in allowed or name in seen_paths: raise ValueError('C illegal/repeated manifest path')
            seen_paths.add(name); file=home/name
            if file.is_symlink() or not file.resolve().is_relative_to(home) or file.stat().st_size>64000000: raise ValueError('C path/size')
            payload=file.read_bytes()
            if type(row['size']) is not int or len(payload)!=row['size'] or hash_of(payload)!=row['sha256']: raise ValueError('C fingerprint '+name)
            content[name]=payload
        if seen_paths!=allowed: raise ValueError('C missing files')
        disk_set=set()
        for file in home.rglob('*'):
            relative=file.relative_to(home)
            if relative.parts[0]!='audits' and file.is_file(): disk_set.add(relative.as_posix())
        if disk_set!=allowed|{'manifest.json'}: raise ValueError('C disk set')
        request=_json(content['request.json'])
        if hash_of(content['request.json'])!=context['expected_request_sha256']: raise ValueError('C request fingerprint')
        if type(request['copies']) is not int or type(request['group_count']) is not int or request['copies']!=s or request['group_count']!=k or request['batch_id']!=context['batch_id']: raise ValueError('C changed request')
        if type(request['schema_version']) is not int or request['schema_version']!=1 or request['format_version']!='direct_amount_v1' or request['rules_version']!='rules_v1' or request['algorithm_version']!='quota_pair_v1': raise ValueError('C unsupported version')
        if type(request['created_at']) is not str or datetime.datetime.fromisoformat(request['created_at']).utcoffset() is None: raise ValueError('C timestamp timezone')
        quota_doc=_json(content['quotas.json'])
        if type(quota_doc['schema_version']) is not int or quota_doc['schema_version']!=1 or quota_doc['batch_id']!=context['batch_id']: raise ValueError('C quota identity')
        quotas=[None]*k; displays=[None]*k
        for entry in quota_doc['groups']:
            group=entry['group']; size=entry['raw_count']; display=entry['display_percent_units']
            if type(group) is not int or type(size) is not int or type(display) is not int or not 1<=group<=k or quotas[group-1] is not None: raise ValueError('C quota type/group')
            if size<2*s or size>30*s: raise ValueError('C quota bounds')
            quotas[group-1]=size; displays[group-1]=display
        if None in quotas or sum(quotas)!=n or sum(displays)!=100000000: raise ValueError('C quota aggregate')
        correct_display=[]; remainders=[]
        for g,size in enumerate(quotas):
            whole,remainder=divmod(100000000*size,n); correct_display.append(whole); remainders.append((remainder,-g))
        remainders.sort(reverse=True)
        for _,negative_g in remainders[:100000000-sum(correct_display)]: correct_display[-negative_g]+=1
        if correct_display!=displays: raise ValueError('C display rounding')
        marks=bytearray(n); positions=[0]*k; frequency=[{} for _ in range(k)]; total=0
        raw=content['items.jsonl']
        if not raw.endswith(b'\n') or b'\r' in raw or raw.startswith(b'\xef\xbb\xbf'): raise ValueError('C JSONL line endings/BOM')
        for line_no,line in enumerate(raw[:-1].split(b'\n'),1):
            if len(line)>1024: raise ValueError('C JSONL line length')
            item=_json(line)
            group=item['group']; position=item['position']; uid=item['item_id']; code=item['code']
            if any(type(v) is not int for v in (group,position,uid)): raise ValueError(f'C integer line {line_no}')
            if group<1 or group>k or uid<0 or uid>=n: raise ValueError(f'C range line {line_no}')
            if marks[uid]: raise ValueError(f'C duplicate item_id {uid} line {line_no}')
            marks[uid]=1
            if type(code) is not str or len(code)!=3 or any(ch<'0' or ch>'9' for ch in code) or int(code)!=uid%1000: raise ValueError(f'C code mapping line {line_no}')
            index=group-1
            if position!=positions[index]+1: raise ValueError(f'C position line {line_no}')
            positions[index]+=1
            if positions[index]>quotas[index]: raise ValueError('C group overflow')
            counts=frequency[index]; counts[code]=counts.get(code,0)+1; total+=1
            if total>n: raise ValueError('C total overflow')
        if total!=n or 0 in marks or positions!=quotas: raise ValueError('C missing IDs/group sizes')
        for index,counts in enumerate(frequency):
            buckets={}
            for code,amount in counts.items():
                if amount>s: raise ValueError('C amount exceeds copies')
                buckets.setdefault(amount,[]).append(code)
            rebuilt=bytearray()
            for amount in sorted(buckets):
                line='.'.join(buckets[amount])+'直选'+str(amount)+'元\n'
                if len(line.encode('utf-8'))-1>8192: raise ValueError('C output line length')
                rebuilt.extend(line.encode('utf-8'))
            if bytes(rebuilt)!=content[f'groups/group_{index+1:03d}.txt']: raise ValueError(f'C reconstructed TXT mismatch group {index+1}')
        return dict(actual_total=total,actual_group_count=k,unique_ids=total,group_raw_counts=positions,files_read=len(content)+1,bytes_read=len(manifest_raw)+sum(len(x) for x in content.values()))
    return report_for('C',context,round,execution_id,examine)
