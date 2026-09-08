from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool
class JobSignals(QObject):
    started=Signal(); progress=Signal(int); finished=Signal(object); error=Signal(str)
class Job(QRunnable):
    def __init__(self,fn,*args,**kwargs):
        super().__init__();self.fn=fn;self.args=args;self.kwargs=kwargs;self.signals=JobSignals()
    def run(self):
        self.signals.started.emit()
        try:
            kw=dict(self.kwargs)
            if "progress" in self.fn.__code__.co_varnames: kw["progress"]=self.signals.progress.emit
            self.signals.finished.emit(self.fn(*self.args,**kw))
        except Exception as e: self.signals.error.emit(str(e))
class JobRunner:
    def __init__(self): self.pool=QThreadPool.globalInstance()
    def start(self,fn,*args,**kwargs):
        j=Job(fn,*args,**kwargs);self.pool.start(j);return j
