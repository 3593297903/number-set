import pytest
from number_app.spec import BatchSpec

def test_all_52461():
    for s in range(100,301):
        for k in range(40,301):
            x=BatchSpec(s,k)
            assert k*x.lower <= x.total <= k*x.upper

@pytest.mark.parametrize('s,k',[(99,40),(301,40),(100,39),(100,301),(True,40),(100,False),(100.0,40),('100',40)])
def test_invalid(s,k):
    with pytest.raises(ValueError): BatchSpec(s,k)
