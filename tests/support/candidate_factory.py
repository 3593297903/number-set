import random
from number_app.spec import BatchSpec
from number_app.core.quota import generate_quotas
from number_app.core.pool import shuffle_ids
from number_app.artifacts import write_candidate
from number_app.storage.files import load_json,canonical,digest

def candidate(path,s=100,k=40):
    spec=BatchSpec(s,k); rng=random.Random(42)
    context=write_candidate(path,spec,generate_quotas(spec,rng),shuffle_ids(spec,rng))
    return dict(context,copies=s,group_count=k,audit_id='test-audit',checker_version='2.0.0')

def refix(path,context):
    m=load_json(path/'manifest.json')
    for e in m['files']:
        b=(path/e['path']).read_bytes(); e.update(size=len(b),sha256=digest(b))
    (path/'manifest.json').write_bytes(canonical(m))
    return dict(context,expected_manifest_sha256=digest(canonical(m)))
