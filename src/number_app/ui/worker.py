import threading
from PySide6.QtCore import QThread,Signal

class Worker(QThread):
    progress=Signal(dict)
    result=Signal(dict)
    failed=Signal(str)
    def __init__(self,operation,parent=None):
        super().__init__(parent); self.operation=operation; self.cancel=threading.Event()
    def run(self):
        try: self.result.emit(self.operation(self.progress.emit,self.cancel))
        except BaseException as e:
            from number_app.jobs.service import Cancelled
            if isinstance(e,Cancelled): self.result.emit(dict(status='CANCELLED',checks_passed=0,error=str(e)))
            else: self.failed.emit(str(e) or type(e).__name__)
