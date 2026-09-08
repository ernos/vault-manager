# Security model

- LUKS2 provides encryption at rest.
- Btrfs is the filesystem inside the encrypted mapping.
- The OS must be trusted while a vault is unlocked.
- The MVP does not protect against root compromise, a malicious kernel, keyloggers,
  malware in the desktop session, or modified cryptsetup.
- Complete-image backups are byte-for-byte encrypted-container copies and are
  SHA-256 verified before generation rotation.
- Chunked backups have per-chunk and combined SHA-256 verification.
- Two local complete-image generations are retained.
- Recovery keys are independent LUKS key material and should have an additional
  offline copy. Never store the only recovery key beside the vault.
- Restores refuse to overwrite an existing container.
