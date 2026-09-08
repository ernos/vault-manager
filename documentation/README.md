# Vault Manager — Functional MVP

Python 3 + PySide6 Kubuntu desktop application for LUKS2/Btrfs encrypted
file-container vaults.

## Install

    ./install_kubuntu.sh

## Run

    python3 main.py

## MVP capabilities

- Create LUKS2 vault containers containing Btrfs.
- Unlock/mount and lock/unmount.
- Multiple vaults.
- Passphrase and recovery-key unlocking.
- Recovery-key creation and LUKS key-slot installation.
- Grow vaults upward, including LUKS mapping and Btrfs resize.
- Complete-image backups with SHA-256 verification and two generations.
- Chunked backups with per-chunk and combined verification.
- Raw backup verification.
- Btrfs scrub.
- Logical file manifest and comparison backend.
- Verified non-overwriting raw restore.
- Activity logging.
- Background jobs for long-running operations.

Do not test on irreplaceable data until the workflow has been tested with
disposable vaults and backups.
