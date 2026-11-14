import os
import time
import uuid
from dataclasses import dataclass,asdict
from datetime import datetime,timezone,timedelta

@dataclass(frozen=True)
class AuditContext:
    batch_id: str
    audit_id: str
    copies: int
    group_count: int
    expected_request_sha256: str
    expected_manifest_sha256: str
    checker_version: str = '2.0.0'

def report_for(method,context,round,execution_id,work):
    ctx=asdict(context) if isinstance(context,AuditContext) else context
    stamp=lambda: datetime.now(timezone(timedelta(hours=8))).isoformat()
    start=time.monotonic()
    r=dict(schema_version=1,batch_id=ctx['batch_id'],audit_id=ctx['audit_id'],execution_id=execution_id or uuid.uuid4().hex,
           method=method,round=round,status='ERROR',checker_version=ctx['checker_version'],pid=os.getpid(),
           started_at=stamp(),request_sha256=ctx['expected_request_sha256'],snapshot_digest=ctx['expected_manifest_sha256'],
           expected_total=ctx['copies']*1000,actual_total=None,expected_group_count=ctx['group_count'],actual_group_count=None,
           error_count=0,errors=[])
    try:
        r.update(work(ctx)); r['status']='PASS'
    except Exception as e:
        r.update(status='FAIL' if isinstance(e,(ValueError,AssertionError)) else 'ERROR',error_count=1,
                 errors=[dict(type=type(e).__name__,file='candidate',location=str(e),expected='valid fixed batch',actual=str(e))])
    r.update(finished_at=stamp(),duration_ms=round_ms(time.monotonic()-start))
    return r

def round_ms(seconds): return int(seconds*1000)
