import json
import pytest
from tests.support.candidate_factory import candidate
from number_app.storage.files import check_snapshot

def test_actual_files(tmp_path):
    ctx=candidate(tmp_path)
    req,m=check_snapshot(tmp_path,ctx['expected_manifest_sha256'],ctx['expected_request_sha256'])
    assert len(m['files'])==43
    assert sum(1 for _ in (tmp_path/'items.jsonl').open())==100000
    assert '直选1元'.encode() in (tmp_path/'groups/group_001.txt').read_bytes()
    (tmp_path/'groups/extra.txt').write_bytes(b'bad')
    with pytest.raises(ValueError): check_snapshot(tmp_path)
