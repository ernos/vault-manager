from dataclasses import dataclass, asdict, fields
from pathlib import Path
import json
from resources import CONFIG_FILE

@dataclass
class Vault:
    name: str
    container: str
    mapper: str
    mount_point: str
    size_bytes: int = 0
    mounted: bool = False
    last_backup: str = ""
    backup_destination: str = ""
    generation_count: int = 0
    recovery_key_file: str = ""
    backups: list = None

    def __post_init__(self):
        if self.backups is None:
            self.backups = []

class VaultStore:
    def __init__(self, path=CONFIG_FILE):
        self.path=path; self.vaults={}; self.load()
    def load(self):
        if not self.path.exists(): return
        try:
            data=json.loads(self.path.read_text(encoding="utf-8"))
            allowed={f.name for f in fields(Vault)}
            self.vaults={x["name"]:Vault(**{k:v for k,v in x.items() if k in allowed}) for x in data}
        except (OSError,ValueError,TypeError,KeyError): self.vaults={}
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps([asdict(v) for v in self.vaults.values()],indent=2),encoding="utf-8")
        tmp.replace(self.path)
    def add(self,v):
        if v.name in self.vaults: raise ValueError("A vault with that name already exists.")
        self.vaults[v.name]=v; self.save()
    def remove(self,name): self.vaults.pop(name,None); self.save()
    def get(self,name): return self.vaults[name]
    def all(self): return list(self.vaults.values())
