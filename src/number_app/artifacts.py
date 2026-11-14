import os
import uuid
from pathlib import Path
from number_app import __version__
from number_app.core.formatting import format_group
from number_app.core.percentages import display_percent_units
from number_app.core.pool import split_ids
from number_app.storage.files import canonical,digest,write_bytes,now,data_paths

def write_candidate(batch_dir,spec,quotas,ids,*,batch_id=None,created_at=None):
    folder=Path(batch_dir); folder.mkdir(parents=True,exist_ok=True)
    batch_id=batch_id or folder.name
    req=dict(schema_version=1,batch_id=batch_id,copies=spec.copies,group_count=spec.group_count,
             rules_version='rules_v1',algorithm_version='quota_pair_v1',format_version='direct_amount_v1',
             software_version=__version__,created_at=created_at or now())
    write_bytes(folder/'request.json',canonical(req))
    units=display_percent_units(quotas)
    write_bytes(folder/'quotas.json',canonical(dict(schema_version=1,batch_id=batch_id,groups=[dict(group=i,raw_count=q,display_percent_units=u) for i,(q,u) in enumerate(zip(quotas,units),1)])))
    with (folder/'items.jsonl').open('xb') as f:
        for g,items in enumerate(split_ids(ids,quotas),1):
            codes=[]
            for pos,item in enumerate(items,1):
                code=f'{item%1000:03}'; codes.append(code)
                f.write(canonical(dict(group=g,position=pos,item_id=item,code=code)))
            write_bytes(folder/f'groups/group_{g:03}.txt',format_group(codes,copies=spec.copies).encode())
        f.flush(); os.fsync(f.fileno())
    files=[]
    for name in data_paths(spec.group_count):
        b=(folder/name).read_bytes(); files.append(dict(path=name,size=len(b),sha256=digest(b)))
    mb=canonical(dict(schema_version=1,batch_id=batch_id,files=files))
    write_bytes(folder/'manifest.json',mb)
    return dict(batch_id=batch_id,expected_request_sha256=digest(canonical(req)),expected_manifest_sha256=digest(mb))
