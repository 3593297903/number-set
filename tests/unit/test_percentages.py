from number_app.core.percentages import display_percent_units

def test_exact_display():
    for q in [[274]*72+[117272], [600]*299+[120600],[1,1,1]]:
        before=q.copy()
        u=display_percent_units(q)
        assert sum(u)==100000000 and q==before
        assert all(abs(x*sum(q)-n*100000000)<sum(q) for x,n in zip(u,q))
