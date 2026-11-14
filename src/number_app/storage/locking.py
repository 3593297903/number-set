from pathlib import Path
import msvcrt

class WorkspaceLock:
    def __init__(self,root): self.path=Path(root)/'.coordinator.lock'; self.file=None
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.file=self.path.open('a+b'); self.file.seek(0)
        if self.path.stat().st_size==0: self.file.write(b'0'); self.file.flush()
        self.file.seek(0)
        try: msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            self.file.close(); raise RuntimeError('本数据目录已有任务运行，请等待完成')
        return self
    def __exit__(self,*args):
        self.file.seek(0); msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1); self.file.close()
