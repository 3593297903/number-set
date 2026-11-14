import json
import os
import platform
import subprocess
import time
import uuid
from pathlib import Path
import psutil
from number_app.storage.files import load_json,save_json,now,digest

ROOT=Path(__file__).parents[2]/'qa'/'release'
ROOT.mkdir(parents=True,exist_ok=True)

def append_evidence(record):
    path=ROOT/'acceptance.json'
    value=load_json(path) if path.exists() else dict(schema_version=1,host=platform.platform(),python=platform.python_version(),runs=[])
    value['runs'].append(dict(record,recorded_at=now())); save_json(path,value)

def exe_run(dist,arguments,result_file,*,verify=False,timeout=240):
    exe=Path(dist)/('NumberVerify.exe' if verify else 'NumberTool.exe')
    command=[str(exe)]+list(map(str,arguments))+['--result-json',str(result_file)]
    start=time.monotonic(); p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    peak=0
    while p.poll() is None:
        try:
            processes=[psutil.Process(p.pid)]+psutil.Process(p.pid).children(recursive=True)
            memory=0
            for proc in processes:
                try: memory+=proc.memory_info().rss
                except psutil.Error: pass
            peak=max(peak,memory)
        except psutil.Error: pass
        if time.monotonic()-start>timeout:
            for child in psutil.Process(p.pid).children(recursive=True): child.kill()
            p.kill(); p.wait(); raise AssertionError('exe timeout '+str(command))
        time.sleep(.025)
    stdout,stderr=p.communicate()
    result=load_json(result_file)
    append_evidence(dict(kind='exe_command',command=command,exitcode=p.returncode,result=result,duration_ms=int((time.monotonic()-start)*1000),peak_process_tree_rss_bytes_sampled=peak,exe_sha256=digest(exe.read_bytes())))
    return p.returncode,result
