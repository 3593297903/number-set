import json
from pathlib import Path
from number_app.storage.files import canonical,digest,load_json

def refingerprint(folder,context):
    manifest=load_json(folder/'manifest.json')
    manifest['files']=[f for f in manifest['files'] if (folder/f['path']).is_file()]
    for entry in manifest['files']:
        data=(folder/entry['path']).read_bytes(); entry.update(size=len(data),sha256=digest(data))
    (folder/'manifest.json').write_bytes(canonical(manifest))
    return dict(context,expected_manifest_sha256=digest(canonical(manifest)))

def mutate(folder,name):
    path=folder/'items.jsonl'; text=folder/'groups/group_001.txt'
    if name in {'delete_item','add_item','duplicate_id','id_negative','id_bool','id_mapping','code_short','code_unicode','position_duplicate','position_missing','empty_jsonl','empty_group','all_zero_to_999','one_code_imbalance','cross_group'}:
        rows=[json.loads(line) for line in path.read_bytes().splitlines()]
        if name=='delete_item': rows.pop(0)
        elif name=='add_item': rows.append(rows[0].copy())
        elif name=='duplicate_id':
            j=next(i for i in range(1,len(rows)) if rows[i]['code']==rows[0]['code']); rows[j]['item_id']=rows[0]['item_id']
        elif name=='id_negative': rows[0]['item_id']=-1
        elif name=='id_bool': rows[0]['item_id']=True
        elif name=='id_mapping': rows[0]['code']=f"{(int(rows[0]['code'])+1)%1000:03}"
        elif name=='code_short': rows[0]['code']='0'
        elif name=='code_unicode': rows[0]['code']='０００'
        elif name=='position_duplicate': rows[1]['position']=1
        elif name=='position_missing': rows[1]['position']=3
        elif name=='empty_jsonl': path.write_bytes(b''); return
        elif name=='empty_group': rows=[r for r in rows if r['group']!=1]
        elif name in {'all_zero_to_999','one_code_imbalance'}:
            if name=='all_zero_to_999':
                for row in rows:
                    if row['code']=='000': row['code']='999'
            else: rows[0]['code']=f"{(int(rows[0]['code'])+1)%1000:03}"
            rebuild_texts(folder,rows)
        elif name=='cross_group':
            a=0; b=next(i for i,r in enumerate(rows) if r['group']!=rows[a]['group'] and r['code']!=rows[a]['code'])
            # Alter only TXT: multiset and quotas remain globally correct; JSONL unchanged.
            other=[dict(r) for r in rows]; other[a]['code'],other[b]['code']=other[b]['code'],other[a]['code']
            rebuild_texts(folder,other); return
        path.write_bytes(b''.join((json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n').encode() for row in rows)); return
    if name=='first_order':
        raw=text.read_bytes(); a,b,tail=raw.split(b'.',2); text.write_bytes(b+b'.'+a+b'.'+tail); return
    if name=='amount_wrong':
        raw=text.read_text(encoding='utf-8'); text.write_bytes(raw.replace('直选1元','直选2元',1).encode()); return
    if name=='missing_group': text.unlink(); return
    if name in {'quota_wrong','quota_duplicate','display_wrong'}:
        p=folder/'quotas.json'; q=load_json(p)
        if name=='quota_wrong': q['groups'][0]['raw_count']+=1; q['groups'][1]['raw_count']-=1
        elif name=='quota_duplicate': q['groups'][1]['group']=q['groups'][0]['group']
        else: q['groups'][0]['display_percent_units']+=1; q['groups'][1]['display_percent_units']-=1
        p.write_bytes(canonical(q)); return
    if name=='duplicate_json_key':
        p=folder/'quotas.json'; data=p.read_bytes(); p.write_bytes(data.replace(b'{',b'{"schema_version":1,',1)); return
    raise ValueError(name)

def rebuild_texts(folder,rows):
    # Deliberately test-owned implementation; expected test assertions are independent.
    groups={}
    for row in rows:
        counts=groups.setdefault(row['group'],{}); code=row['code']; counts[code]=counts.get(code,0)+1
    for group,counts in groups.items():
        rendered=[]
        for amount in sorted(set(counts.values())):
            rendered.append('.'.join(code for code in counts if counts[code]==amount)+'直选'+str(amount)+'元\n')
        (folder/f'groups/group_{group:03}.txt').write_bytes(''.join(rendered).encode())
