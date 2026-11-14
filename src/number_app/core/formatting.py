import re

def format_group(codes, *, copies):
    if type(copies) is not int or copies < 1: raise ValueError("非法金额上限")
    counts = {}
    for code in codes:
        if not isinstance(code,str) or re.fullmatch(r'[0-9]{3}',code) is None:
            raise ValueError("号码须为三位ASCII数字")
        counts[code] = counts.get(code,0)+1
        if counts[code] > copies: raise ValueError("金额超出原始套数")
    buckets = {}
    for code,n in counts.items(): buckets.setdefault(n,[]).append(code)
    return ''.join('.'.join(buckets[n])+f'直选{n}元\n' for n in sorted(buckets))
