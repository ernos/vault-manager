#!/usr/bin/env python3
import shutil
for x in ("cryptsetup","btrfs","mount","umount","pkexec"):
    print(f"{x:12} {'OK' if shutil.which(x) else 'MISSING'}")
try:
 import PySide6; print(f"{'PySide6':12} OK ({PySide6.__version__})")
except ImportError: print(f"{'PySide6':12} MISSING")
