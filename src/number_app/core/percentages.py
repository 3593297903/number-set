def display_percent_units(quotas):
    if not quotas or any(type(x) is not int or x<=0 for x in quotas): raise ValueError('非法配额')
    n=sum(quotas)
    pairs=[divmod(x*100000000,n) for x in quotas]
    units=[p[0] for p in pairs]
    order=sorted(range(len(units)),key=lambda i:(-pairs[i][1],i))
    for i in order[:100000000-sum(units)]: units[i]+=1
    return units
