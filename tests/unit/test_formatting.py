import json
from pathlib import Path
import pytest
from number_app.core.formatting import format_group

def test_fixed_bytes():
    data=json.loads((Path(__file__).parents[2]/'验收样例_直选金额.json').read_text(encoding='utf-8'))
    for c in data['positive_cases']:
        assert len(c['raw_codes']) == c['expected_raw_count']
        assert format_group(c['raw_codes'],copies=300).encode() == c['expected_text'].encode()

@pytest.mark.parametrize('codes', [['7'],['００７'],[7],['007 '],['007']*301])
def test_reject(codes):
    with pytest.raises(ValueError): format_group(codes,copies=300)

def test_golden_weighted_raw_counts_not_distinct():
    from number_app.checks.a_count import parse_a
    from number_app.checks.b_sort import parse_b
    data=json.loads((Path(__file__).parents[2]/'验收样例_直选金额.json').read_text(encoding='utf-8'))
    for case in data['positive_cases']:
        counts,total=parse_a(case['expected_text'].encode(),300)
        expanded=parse_b(case['expected_text'].encode(),300)
        assert total==sum(counts)==len(expanded)==case['expected_raw_count']
        assert sum(n>0 for n in counts)==case['expected_distinct_count']
