import multiprocessing
import sys
if __name__=='__main__':
    multiprocessing.freeze_support()
    from number_app.cli import main
    raise SystemExit(main(['verify']+sys.argv[1:]))
