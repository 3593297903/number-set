import random
from collections import Counter
from number_app.spec import BatchSpec
from number_app.core.pool import shuffle_ids,split_ids
from number_app.core.quota import generate_quotas

def test_complete_300000():
    for s,k in [(100,40),(100,300),(300,40),(300,300),(137,73)]:
        spec=BatchSpec(s,k); rng=random.Random(s+k)
        ids=shuffle_ids(spec,rng); q=generate_quotas(spec,rng)
        assert sorted(ids)==list(range(spec.total))
        assert [len(g) for g in split_ids(ids,q)]==q
        assert set(Counter(i%1000 for i in ids).values())=={s}
