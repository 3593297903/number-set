import multiprocessing as mp
import time
import uuid
from dataclasses import asdict,is_dataclass
from pathlib import Path
from number_app.checks.reports import report_for
from number_app.storage.files import save_json,load_json,check_snapshot,now,digest

METHODS=('A','B','C')

def _worker(folder,context,method,round_number,execution_id,report_path):
    # Spawn imports no Qt; each method opens all fixed files itself.
    from number_app.checks.a_count import check_a
    from number_app.checks.b_sort import check_b
    from number_app.checks.c_ids import check_c
    report={'A':check_a,'B':check_b,'C':check_c}[method](folder,context,round_number,execution_id)
    save_json(report_path,report)

def validate_report(report,ctx,method,round_number,execution_id,pid,exitcode):
    expected=dict(schema_version=1,batch_id=ctx['batch_id'],audit_id=ctx['audit_id'],method=method,
                  round=round_number,execution_id=execution_id,pid=pid,checker_version=ctx['checker_version'],
                  request_sha256=ctx['expected_request_sha256'],snapshot_digest=ctx['expected_manifest_sha256'],
                  expected_total=ctx['copies']*1000,actual_total=ctx['copies']*1000,
                  expected_group_count=ctx['group_count'],actual_group_count=ctx['group_count'],status='PASS',error_count=0)
    return exitcode==0 and all(type(report.get(key)) is type(value) and report.get(key)==value for key,value in expected.items()) and report.get('errors')==[] and report.get('files_read')==ctx['group_count']+4 and bool(report.get('started_at')) and bool(report.get('finished_at'))

def all_pass(checks):
    return len(checks)==15 and {(c['method'],c['round']) for c in checks}=={(m,r) for m in METHODS for r in range(1,6)} and all(c.get('accepted') is True for c in checks)

def audit_batch(batch_dir,context,*,progress=None,cancel=None,timeout=120,_target=None):
    folder=Path(batch_dir)
    ctx=asdict(context) if is_dataclass(context) else dict(context)
    ctx['audit_id']=uuid.uuid4().hex
    ctx.setdefault('checker_version','2.0.0')
    reports_dir=folder/'audits'/ctx['audit_id']; reports_dir.mkdir(parents=True,exist_ok=False)
    summary=dict(schema_version=1,batch_id=ctx['batch_id'],audit_id=ctx['audit_id'],started_at=now(),
                 snapshot_digest=ctx['expected_manifest_sha256'],request_sha256=ctx['expected_request_sha256'],checks=[],launches=[],status='FAIL')
    processes=[]; report_fingerprints={}
    try:
        spawn=mp.get_context('spawn')
        for round_number in range(1,6):
            running=[]
            for method in METHODS:
                execution=uuid.uuid4().hex; path=reports_dir/f'{method}_{round_number}.json'
                p=spawn.Process(target=_target or _worker,args=(str(folder),ctx,method,round_number,execution,str(path)),daemon=True)
                p.start(); processes.append(p)
                event=dict(method=method,round=round_number,execution_id=execution,pid=p.pid,launched_at=now())
                summary['launches'].append(event)
                running.append((p,event,path,time.monotonic()))
                if progress: progress(dict(stage='AUDITING',status='RUNNING',**event))
            while running:
                for task in running[:]:
                    p,event,path,started=task
                    cancelled=bool(cancel and cancel.is_set())
                    expired=time.monotonic()-started>timeout
                    if p.is_alive() and not expired and not cancelled: continue
                    forced=None
                    if p.is_alive():
                        forced='CANCELLED' if cancelled else 'TIMEOUT'; p.terminate()
                    p.join(10)
                    if p.is_alive(): p.kill(); p.join()
                    try:
                        r=load_json(path)
                        accepted=not forced and validate_report(r,ctx,event['method'],event['round'],event['execution_id'],p.pid,p.exitcode)
                    except Exception as e:
                        def missing_report(_): raise RuntimeError('子进程报告缺失或无法解析: '+str(e))
                        r=report_for(event['method'],ctx,event['round'],event['execution_id'],missing_report)
                        r.update(pid=p.pid,started_at=event['launched_at'],origin='coordinator',status=forced or 'ERROR',duration_ms=int((time.monotonic()-started)*1000))
                        if not path.exists(): save_json(path,r)
                        accepted=False
                    record=dict(r,accepted=bool(accepted),exitcode=p.exitcode)
                    if forced: record.update(status=forced,accepted=False)
                    # Preserve original report and coordinator's independent decision.
                    decision=reports_dir/f"{event['method']}_{event['round']}.decision.json"
                    save_json(decision,record)
                    report_fingerprints[str(path)]=digest(path.read_bytes())
                    report_fingerprints[str(decision)]=digest(decision.read_bytes())
                    summary['checks'].append(record); running.remove(task)
                    if progress: progress(dict(stage='AUDITING',method=event['method'],round=event['round'],status=record['status'] if accepted else record.get('status','ERROR'),accepted=accepted))
                if running: time.sleep(.025)
            if cancel and cancel.is_set(): break
        check_snapshot(folder,ctx['expected_manifest_sha256'],ctx['expected_request_sha256'])
        if any(digest(Path(p).read_bytes())!=sha for p,sha in report_fingerprints.items()): raise ValueError('审查报告在汇总前被修改')
        if all_pass(summary['checks']): summary['status']='PASS'
    except Exception as e:
        summary['error']=str(e)
    finally:
        for p in processes:
            if p.is_alive(): p.terminate()
            p.join()
            p.close()
        if cancel and cancel.is_set(): summary['status']='CANCELLED'
        summary.update(finished_at=now(),checks_passed=sum(c.get('accepted') is True for c in summary['checks']))
        save_json(reports_dir/'summary.json',summary)
        (reports_dir/'summary.txt').write_text('\n'.join([f"{summary['status']} {summary['checks_passed']}/15"]+[f"{r['method']}{r['round']} {r['status']} accepted={r['accepted']} PID={r['pid']} execution={r['execution_id']}" for r in summary['checks']])+'\n',encoding='utf-8',newline='\n')
    return summary
