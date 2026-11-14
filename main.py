import multiprocessing
if __name__=='__main__':
    multiprocessing.freeze_support()
    from number_app.cli import entry
    raise SystemExit(entry())
