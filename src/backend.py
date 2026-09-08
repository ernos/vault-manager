from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, shutil, subprocess
from typing import Callable, Optional
from models import Vault
from resources import MOUNT_ROOT, LOG_DIR
from db import Database

class CommandError(RuntimeError):
    pass

class VaultBackend:
    def __init__(self, event_cb: Optional[Callable[[str], None]] = None):
        self.db = Database()
        self.event_cb = event_cb

    def _event(self, message, event_type="info", vault=None, severity="info"):
        stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{stamp}] {message}"
        if self.event_cb: self.event_cb(line)
        self.db.log_activity(message, event_type, vault, severity)
        try:
            with (LOG_DIR / "activity.log").open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError: pass

    @staticmethod
    def _run(args, input_text=None, privileged=False, check=True, timeout=None):
        cmd = [str(x) for x in args]
        if privileged: cmd.insert(0, "pkexec")
        try:
            p = subprocess.run(cmd, input=input_text, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=timeout)
        except FileNotFoundError as e:
            raise CommandError(f"Required command not found: {e.filename}") from e
        except subprocess.TimeoutExpired as e:
            raise CommandError(f"Command timed out: {' '.join(cmd)}") from e
        if check and p.returncode:
            raise CommandError(p.stderr.strip() or p.stdout.strip() or
                               f"exit status {p.returncode}")
        return p.stdout.strip()

    @staticmethod
    def _safe_name(name):
        name = name.strip()
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            raise ValueError("Invalid vault name.")
        if len(name) > 80: raise ValueError("Vault name is too long.")
        return name.replace(" ", "_")

    @staticmethod
    def _password(secret):
        if not secret: raise ValueError("A non-empty secret is required.")
        if "\x00" in secret: raise ValueError("Secret contains NUL.")

    def _cryptsetup(self, *args, input_text=None, check=True):
        return self._run(["cryptsetup", *args], input_text=input_text,
                         privileged=True, check=check)

    def _btrfs(self, *args, check=True):
        return self._run(["btrfs", *args], privileged=True, check=check)

    def generate_recovery_key(self):
        import base64
        return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")

    def create_vault(self, name, container, size_mb, passphrase, recovery_key=""):
        name = self._safe_name(name); self._password(passphrase)
        size_mb = int(size_mb)
        if size_mb < 64: raise ValueError("Vault size must be at least 64 MiB.")
        path = Path(container).expanduser().resolve()
        if path.exists(): raise ValueError("Container already exists.")
        path.parent.mkdir(parents=True, exist_ok=True)
        mapper, mount = f"vault-{name}", MOUNT_ROOT / name
        mount.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as f: f.truncate(size_mb * 1024 * 1024)
            self._cryptsetup("luksFormat", "--type", "luks2", "--batch-mode",
                             str(path), input_text=passphrase + "\n")
            self._cryptsetup("open", str(path), mapper,
                             input_text=passphrase + "\n")
            self._run(["mkfs.btrfs", "-f", "-L", name, f"/dev/mapper/{mapper}"],
                      privileged=True)
            if recovery_key:
                self._cryptsetup("luksAddKey", str(path),
                                 input_text=passphrase + "\n" + recovery_key + "\n")
            self._cryptsetup("close", mapper)
            v = Vault(name, str(path), mapper, str(mount),
                      size_mb * 1024 * 1024, False)
            self.db.add_vault(v)
            if recovery_key:
                rp = path.with_name(path.name + ".recovery.key")
                rp.write_text(recovery_key + "\n", encoding="utf-8")
                os.chmod(rp, 0o600)
                v.recovery_key_file = str(rp)
                self.db.update_vault(v)
            self._event(f"Created vault '{name}'.", "create", name, "success")
            return v
        except Exception as e:
            self._cryptsetup("close", mapper, check=False)
            path.unlink(missing_ok=True); shutil.rmtree(mount, ignore_errors=True)
            self._event(f"Failed to create vault '{name}': {e}", "create", name, "error")
            raise

    def unlock_vault(self, name, secret, is_recovery=False):
        self._password(secret); v = self.db.get_vault(name)
        if v.mounted: return v
        try:
            self._cryptsetup("open", v.container, v.mapper, input_text=secret + "\n")
            self._run(["mount", "-o", "compress=zstd",
                       f"/dev/mapper/{v.mapper}", v.mount_point], privileged=True)
            v.mounted = True; self.db.update_vault(v)
            self._event(f"Unlocked '{name}'" + (" using recovery key." if is_recovery else "."), "unlock", name, "success")
            return v
        except Exception as e:
            self._cryptsetup("close", v.mapper, check=False)
            self._event(f"Failed to unlock '{name}': {e}", "unlock", name, "warning")
            raise

    def lock_vault(self, name):
        v = self.db.get_vault(name)
        if not v.mounted: return v
        self._run(["sync"])
        self._run(["umount", "--", v.mount_point], privileged=True)
        self._cryptsetup("close", v.mapper)
        v.mounted = False; self.db.update_vault(v)
        self._event(f"Locked '{name}'.", "lock", name, "success"); return v

    def resize_vault(self, name, new_size_mb):
        v = self.db.get_vault(name)
        if v.mounted: raise ValueError("Lock the vault before resizing.")
        new = int(new_size_mb) * 1024 * 1024
        old = os.path.getsize(v.container)
        if new <= old: raise ValueError("New size must be larger.")
        with open(v.container, "r+b") as f: f.truncate(new)
        try:
            self._cryptsetup("open", v.container, v.mapper)
            self._cryptsetup("resize", v.mapper)
            self._run(["mount", "-o", "compress=zstd",
                       f"/dev/mapper/{v.mapper}", v.mount_point], privileged=True)
            v.mounted = True
            self._btrfs("filesystem", "resize", "max", v.mount_point)
            self._run(["sync"])
            self._run(["umount", "--", v.mount_point], privileged=True)
            self._cryptsetup("close", v.mapper); v.mounted = False
            v.size_bytes = new; self.db.update_vault(v)
            self._event(f"Resized '{name}' to {int(new_size_mb)} MiB.", "resize", name, "success")
            return v
        except Exception as e:
            self._run(["umount", "--", v.mount_point], privileged=True, check=False)
            self._cryptsetup("close", v.mapper, check=False)
            self._event(f"Failed to resize '{name}': {e}", "resize", name, "error")
            raise

    @staticmethod
    def sha256(path, chunk=8*1024*1024):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while data := f.read(chunk): h.update(data)
        return h.hexdigest()

    def backup_complete(self, name, destination, progress=None):
        v = self.db.get_vault(name)
        if v.mounted: raise ValueError("Lock the vault before an image backup.")
        src = Path(v.container); dst_dir = Path(destination).expanduser().resolve()
        dst_dir.mkdir(parents=True, exist_ok=True)
        final = dst_dir / src.name
        partial = dst_dir / (src.name + ".partial")
        if partial.exists(): partial.unlink()
        total = src.stat().st_size; done = 0
        self._event(f"Starting complete backup of '{name}'.", "backup", name, "info")
        with src.open("rb") as a, partial.open("wb") as b:
            while data := a.read(8*1024*1024):
                b.write(data); done += len(data)
                if progress and total: progress(int(done*80/total))
        os.sync()
        sh = self.sha256(str(src)); bh = self.sha256(str(partial))
        if sh != bh:
            partial.unlink(missing_ok=True)
            self._event(f"Failed to backup '{name}': Raw verification failed.", "backup", name, "error")
            raise CommandError("Raw backup verification failed.")
        gen1, gen2 = dst_dir/(src.name+".gen1"), dst_dir/(src.name+".gen2")
        if gen2.exists(): gen2.unlink()
        if gen1.exists(): gen1.rename(gen2)
        if final.exists(): final.rename(gen1)
        partial.rename(final)
        v.last_backup = datetime.now(timezone.utc).isoformat()
        v.backup_destination = str(dst_dir)
        v.generation_count = sum(p.exists() for p in (final, gen1, gen2))
        v.backups.append({"path": str(final), "type": "full", "date": v.last_backup})
        self.db.update_vault(v)
        if progress: progress(100)
        self._event(f"Backup verified for '{name}'.", "backup", name, "success")
        return {"path": str(final), "sha256": bh, "generations": v.generation_count}

    def backup_chunked(self, name, destination, chunk_mb=1024, progress=None):
        v = self.db.get_vault(name)
        if v.mounted: raise ValueError("Lock the vault before an image backup.")
        src = Path(v.container); dst = Path(destination).expanduser().resolve()
        dst.mkdir(parents=True, exist_ok=True)
        chunk_size = max(64, int(chunk_mb))*1024*1024
        cdir = dst/(src.name+".chunks"); cdir.mkdir(exist_ok=True)
        manifest = {"format":1,"vault":v.name,"container_name":src.name,
                    "source_size":src.stat().st_size,"chunk_size":chunk_size,
                    "source_sha256":None,"chunks":[]}
        total=src.stat().st_size; done=0; source_hash=hashlib.sha256(); idx=0
        with src.open("rb") as f:
            while data := f.read(chunk_size):
                source_hash.update(data); p=cdir/f"{src.name}.part-{idx:06d}"
                tmp=p.with_suffix(".partial"); tmp.write_bytes(data); tmp.replace(p)
                manifest["chunks"].append({"index":idx,"file":p.name,
                    "size":len(data),"sha256":hashlib.sha256(data).hexdigest()})
                idx+=1; done+=len(data)
                if progress and total: progress(int(done*90/total))
        manifest["source_sha256"]=source_hash.hexdigest()
        m_path = dst/(src.name+".chunks.json")
        m_path.write_text(json.dumps(manifest,indent=2))
        v.backups.append({"path": str(m_path), "type": "chunked", "date": datetime.now(timezone.utc).isoformat()})
        self.db.update_vault(v)
        if progress: progress(100)
        self._event(f"Chunked backup verified by per-chunk checksums for '{name}'.", "backup", name, "success")
        return manifest

    def verify_chunked_backup(self, manifest_path, progress=None):
        mf=Path(manifest_path); m=json.loads(mf.read_text())
        root=mf.parent/(m["container_name"]+".chunks"); h=hashlib.sha256()
        total=sum(c["size"] for c in m["chunks"]); done=0
        for c in m["chunks"]:
            p=root/c["file"]
            if not p.is_file(): raise CommandError(f"Missing chunk: {p.name}")
            if self.sha256(str(p)) != c["sha256"]:
                raise CommandError(f"Chunk checksum mismatch: {p.name}")
            with p.open("rb") as f:
                while data := f.read(8*1024*1024): h.update(data); done+=len(data)
            if progress and total: progress(int(done*100/total))
        if h.hexdigest()!=m["source_sha256"]:
            raise CommandError("Combined chunk checksum mismatch.")
        return m

    def verify_raw_backup(self, source, backup):
        a,b=self.sha256(source),self.sha256(backup)
        if a!=b: raise CommandError("Raw image SHA-256 mismatch.")
        return {"source_sha256":a,"backup_sha256":b,"equal":True}

    def verify_btrfs(self, name):
        v=self.db.get_vault(name)
        if not v.mounted: raise ValueError("Unlock the vault first.")
        self._event(f"Starting Btrfs scrub for '{name}'.", "btrfs", name, "info")
        out=self._btrfs("scrub","start","-B",v.mount_point)
        self._event(f"Btrfs scrub completed for '{name}'.", "btrfs", name, "success")
        return out

    def logical_manifest(self, name, progress=None):
        v=self.db.get_vault(name)
        if not v.mounted: raise ValueError("Unlock the vault first.")
        root=Path(v.mount_point); ps=sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink())
        result=[]
        for i,p in enumerate(ps):
            result.append({"path":str(p.relative_to(root)),"size":p.stat().st_size,
                           "sha256":self.sha256(str(p))})
            if progress and ps: progress(int((i+1)*100/len(ps)))
        return result

    @staticmethod
    def compare_manifests(source, backup):
        a={x["path"]:x for x in source}; b={x["path"]:x for x in backup}
        return [{"path":p,"source":a.get(p),"backup":b.get(p),
                 "kind":"missing-in-backup" if p in a and p not in b
                 else "extra-in-backup" if p not in a else "changed"}
                for p in sorted(set(a)|set(b)) if a.get(p)!=b.get(p)]

    def restore_raw(self, backup, destination, progress=None):
        src,dst=Path(backup),Path(destination)
        if not src.is_file(): raise ValueError("Backup does not exist.")
        if dst.exists(): raise ValueError("Refusing to overwrite an existing container.")
        tmp=dst.with_suffix(dst.suffix+".restore-partial"); total=src.stat().st_size; done=0
        self._event(f"Starting restore of '{backup}'.", "restore", None, "info")
        with src.open("rb") as a,tmp.open("wb") as b:
            while data:=a.read(8*1024*1024):
                b.write(data);done+=len(data)
                if progress: progress(int(done*90/total))
        if self.sha256(str(src))!=self.sha256(str(tmp)):
            tmp.unlink(missing_ok=True); raise CommandError("Restore verification failed.")
        tmp.rename(dst)
        if progress: progress(100)
        self._event(f"Restored verified image to '{dst}'.", "restore", None, "success"); return str(dst)

    def delete_backup(self, backup_path):
        path = Path(backup_path).expanduser().resolve()
        if not path.exists(): raise ValueError("Backup does not exist.")
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        self._event(f"Deleted backup: {path}", "delete", None, "success")
