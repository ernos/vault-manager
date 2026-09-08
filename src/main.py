#!/usr/bin/env python3
import sys
from pathlib import Path
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject,Slot,Signal,QThreadPool
from backend import VaultBackend
from worker import Job

class Bridge(QObject):
    vaultsChanged=Signal(); operationError=Signal(str); operationMessage=Signal(str)
    activityAdded=Signal(str); requestSecret=Signal(str,bool); progressChanged=Signal(int,str)
    jobFinished=Signal(str,'QVariant')

    def __init__(self):
        super().__init__();self.pool=QThreadPool.globalInstance();self.jobs=set()
        self.backend=VaultBackend(self._event)
    def _event(self,m): self.activityAdded.emit(m)
    @Slot(result='QVariantList')
    def vaults(self): return [v.__dict__ for v in self.backend.db.all_vaults()]
    @Slot(result='QVariantList')
    def activityLogs(self): return self.backend.db.get_activity_logs()
    @Slot(str)
    def unlockVault(self,n): self.requestSecret.emit(n,False)
    @Slot(str)
    def unlockWithRecoveryKey(self,n): self.requestSecret.emit(n,True)
    @Slot(str,str,bool)
    def unlockWithSecret(self,n,s,r):
        try:self.backend.unlock_vault(n,s,r);self.vaultsChanged.emit()
        except Exception as e:self.operationError.emit(str(e))
    @Slot(str)
    def lockVault(self,n):
        try:self.backend.lock_vault(n);self.vaultsChanged.emit()
        except Exception as e:self.operationError.emit(str(e))
    @Slot(str,str,int,str,bool)
    def createVault(self,n,c,mb,p,make):
        try:
            key=self.backend.generate_recovery_key() if make else ""
            self.backend.create_vault(n,c,int(mb),p,key)
            if key:self.jobFinished.emit("recoveryKey",key)
            self.operationMessage.emit(f"Vault '{n}' created.");self.vaultsChanged.emit()
        except Exception as e:self.operationError.emit(str(e))
    @Slot(str,str)
    def addRecoveryKey(self,n,p,out):
        try:
            key=self.backend.generate_recovery_key()
            v=self.backend.store.get(n)
            self.backend._password(p)
            self.backend._cryptsetup("luksAddKey",v.container,input_text=p+"\\n"+key+"\\n")
            q=Path(out).expanduser();q.write_text(key+"\\n");q.chmod(0o600)
            self.operationMessage.emit(f"Recovery key exported to {q}")
        except Exception as e:self.operationError.emit(str(e))
    def _start(self,label,fn,*args):
        j=Job(fn,*args);self.jobs.add(j)
        j.signals.progress.connect(lambda p:self.progressChanged.emit(p,label))
        j.signals.error.connect(self.operationError.emit)
        j.signals.finished.connect(lambda r:self._done(j,label,r))
        self.pool.start(j)
    def _done(self,j,label,r):
        self.jobs.discard(j);self.operationMessage.emit(label+" completed.")
        self.jobFinished.emit(label,r);self.vaultsChanged.emit()
    @Slot(str,str)
    def startCompleteBackup(self,n,d): self._start("Complete-image backup",self.backend.backup_complete,n,d)
    @Slot(str,str,int)
    def startChunkedBackup(self,n,d,mb): self._start("Chunked backup",self.backend.backup_chunked,n,d,int(mb))
    @Slot(str,str)
    def verifyRawBackup(self,s,b): self._start("Raw backup verification",self.backend.verify_raw_backup,s,b)
    @Slot(str)
    def verifyBtrfs(self,n): self._start("Btrfs scrub",self.backend.verify_btrfs,n)
    @Slot(str,int)
    def resizeVault(self,n,mb): self._start("Vault resize",self.backend.resize_vault,n,int(mb))
    @Slot(str,str)
    def restoreRaw(self,b,d): self._start("Restore",self.backend.restore_raw,b,d)
    @Slot(str)
    def deleteBackup(self,p):
        try:
            self.backend.delete_backup(p)
            self.operationMessage.emit(f"Deleted backup: {p}")
        except Exception as e:
            self.operationError.emit(str(e))

app=QGuiApplication(sys.argv);app.setApplicationName("Vault Manager")
engine=QQmlApplicationEngine();bridge=Bridge()
engine.rootContext().setContextProperty("vaultBackend",bridge)
engine.load(str(Path(__file__).with_name("vaults.qml")))
if not engine.rootObjects():sys.exit(1)
sys.exit(app.exec())
