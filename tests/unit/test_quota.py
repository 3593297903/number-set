import random
from number_app.spec import BatchSpec
from number_app.core.quota import generate_quotas

def test_four_boundaries_100_each():
    rng=random.Random(4701)
    for s,k in [(100,40),(100,300),(300,40),(300,300)]:
        spec=BatchSpec(s,k)
        for _ in range(100):
            q=generate_quotas(spec,rng)
            assert len(q)==k and sum(q)==1000*s
            assert all(type(x) is int and 2*s<=x<=30*s for x in q)

def test_random_variation():
    spec=BatchSpec(137,73)
    assert generate_quotas(spec)!=generate_quotas(spec)
