from pathlib import Path
import os

APP_NAME = "vault-manager"
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / APP_NAME
CONFIG_FILE = DATA_DIR / "vaults.json"
LOG_DIR = DATA_DIR / "logs"
MOUNT_ROOT = Path("/run/user") / str(os.getuid()) / APP_NAME

for path in (DATA_DIR, LOG_DIR, MOUNT_ROOT):
    path.mkdir(parents=True, exist_ok=True)
