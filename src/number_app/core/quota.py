from random import SystemRandom

def generate_quotas(spec, rng=None):
    rng = rng or SystemRandom()
    base,rem = divmod(spec.total,spec.group_count)
    q = [base+(i<rem) for i in range(spec.group_count)]
    for _ in range(100*spec.group_count):
        i,j = rng.sample(range(spec.group_count),2)
        t=q[i]+q[j]
        x=rng.randint(max(spec.lower,t-spec.upper),min(spec.upper,t-spec.lower))
        q[i],q[j]=x,t-x
    rng.shuffle(q)
    if len(q)!=spec.group_count or sum(q)!=spec.total or any(type(n) is not int or not spec.lower<=n<=spec.upper for n in q):
        raise ValueError("配额错误")
    return q
