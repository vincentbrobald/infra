# backup: RustFS (S3)

> Reference · [Documentation](../../../README.md#documentation)

Object storage for the Talos clusters' etcd backups (`talosBackup` of
deploy-talos.py).

| | |
|---|---|
| VM | `backup`, 2 vCPU, 2 GiB, 60 GB, AlmaLinux 10 |
| Address | 192.0.2.193 (DHCP, name registered by the router) |
| Runs | RustFS 1.0.1 (RPM, checksum-verified), Caddy 2 |
| Playbook | `ansible/backup.yml` (role `rustfs`; settings in `ansible/inventory/group_vars/s3.yml`) |
| SSH | `ssh -i /root/lab/lab-secrets/backup/id_ed25519 almalinux@backup.example.org` |

## Endpoints

| Endpoint | What |
|---|---|
| `https://backup.example.org` | S3 API (path-style), certificate from step-ca |
| `https://backup.example.org:9443` | RustFS web console (root keys) |

RustFS itself listens on localhost only (S3 :9000, console :9001); data in
`/data/rustfs`; settings `/etc/default/rustfs` (root keys, root-only).

## Buckets and users

| Bucket | Settings |
|---|---|
| `talos-backups` | versioned; object lock GOVERNANCE, every version kept at least 7 days; current versions expire after 30 days, replaced or deleted ones a day after their lock ends |

| User | May |
|---|---|
| `talos-backup` | `PutObject` into `talos-backups` only: no list, read or delete |
| root | everything but deleting a locked version |

Snapshots: `talos-backups/<cluster>/<cluster>-<time>.snap.zst.age`.

The role adds buckets and users but never removes them.

## Files

| `/root/lab/lab-secrets/` | Contents |
|---|---|
| `backup/id_ed25519` (+ `.pub`) | SSH key of the VM |
| `backup/rustfs-root-{access,secret}-key` | RustFS root credentials (also on the VM) |
| `backup/talos-backup-{access,secret}-key` | the write-only user's keys (cluster files' `talosBackup.s3`); also gitops Secret `talos-backup/talos-backup-s3` of each cluster, which wins |
| `backup/talos-backup-age.key` (`.pub`) | the age key pair snapshots are encrypted for. **Without the private key no backup can be restored**: keep a copy off this host |
