import argparse
import multiprocessing
import sys
from pathlib import Path
from number_app.command_result import write_result

def main(argv=None):
    parser=argparse.ArgumentParser(description='随机号码分组工具 2.0')
    sub=parser.add_subparsers(dest='command',required=True)
    gen=sub.add_parser('generate'); gen.add_argument('--copies',required=True,type=int); gen.add_argument('--groups',required=True,type=int)
    ver=sub.add_parser('verify'); ver.add_argument('--batch-dir',required=True)
    gui=sub.add_parser('gui')
    rec=sub.add_parser('recover'); rec.add_argument('--batch-id',required=True)
    exp=sub.add_parser('export'); exp.add_argument('--batch-id',required=True); exp.add_argument('--destination',required=True)
    bak=sub.add_parser('backup'); bak.add_argument('--backup-dir',required=True)
    restore=sub.add_parser('restore'); restore.add_argument('--backup-dir',required=True); restore.add_argument('--destination',required=True)
    scan=sub.add_parser('inspect-recovery')
    for command in (gen,ver,gui,rec,exp,bak,restore,scan):
        command.add_argument('--data-dir',default='E:/number/data')
        command.add_argument('--result-json')
    args=parser.parse_args(argv)
    try:
        write_result(args.result_json,dict(status='RUNNING',command=args.command))
        if args.command=='generate':
            from number_app.spec import BatchSpec
            from number_app.jobs.service import generate_batch
            try: spec=BatchSpec(args.copies,args.groups)
            except ValueError as e:
                write_result(args.result_json,dict(status='INVALID_INPUT',error=str(e))); return 2
            result=generate_batch(spec,args.data_dir)
        elif args.command=='verify':
            from number_app.jobs.service import verify_batch
            result=verify_batch(args.batch_dir,args.data_dir)
        elif args.command=='recover':
            from number_app.storage.recovery import recover_batch
            result=recover_batch(args.batch_id,args.data_dir)
        elif args.command=='export':
            from number_app.storage.export import export_batch
            result=export_batch(args.batch_id,args.data_dir,args.destination)
        elif args.command=='backup':
            from number_app.storage.backup import create_backup
            result=create_backup(args.data_dir,args.backup_dir)
        elif args.command=='restore':
            from number_app.storage.backup import restore_backup
            result=restore_backup(args.backup_dir,args.destination)
        elif args.command=='inspect-recovery':
            from number_app.storage.recovery import inspect_recovery
            result=dict(status='RECOVERY_READY',pending=inspect_recovery(args.data_dir))
        else:
            from number_app.ui.app import run_gui
            return run_gui(args.data_dir)
        write_result(args.result_json,result)
        if sys.stdout: print(result)
        return 0 if result['status'] in {'COMPLETED','PASS','EXPORTED','BACKUP_COMPLETE','RESTORED','RECOVERY_READY'} else 5 if result['status'] in {'CANCELLED','INTERRUPTED'} else 3
    except (KeyboardInterrupt,SystemExit) as e:
        write_result(args.result_json,dict(status='INTERRUPTED',error=str(e))); return 5
    except Exception as e:
        from number_app.jobs.service import Cancelled
        if isinstance(e,Cancelled):
            write_result(args.result_json,dict(status='CANCELLED',error=str(e))); return 5
        write_result(args.result_json,dict(status='FAIL' if isinstance(e,ValueError) else 'ERROR',error=str(e)))
        if sys.stderr: print(str(e),file=sys.stderr)
        return 3 if isinstance(e,ValueError) else 4

def entry():
    multiprocessing.freeze_support()
    return main(sys.argv[1:] or ['gui'])
