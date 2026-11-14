from random import SystemRandom

def shuffle_ids(spec, rng=None):
    result=list(range(spec.total))
    (rng or SystemRandom()).shuffle(result)
    return result

def split_ids(ids,quotas):
    if sum(quotas)!=len(ids): raise ValueError('切分总数不匹配')
    start=0
    for q in quotas:
        yield ids[start:start+q]
        start+=q
