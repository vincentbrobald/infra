# Secrets tree

> Reference · [Documentation](../../README.md#documentation)

Credentials live outside the code, in **`/root/lab/lab-secrets`** (mode
700, root-only), which must never be committed. The playbooks find it through
`site_secrets_dir` (`ansible/inventory/group_vars/all.yml`), `/root/lab/lb/lbctl.py`
through `INFRA_SECRETS`. Each VM's page lists its own files.

| Path | Contents |
|---|---|
| `<vm>/id_ed25519` (+ `.pub`) | each VM's SSH key |
| `<vm>/...` | the service's credentials ([VMs](site.md#vms)) |
| `sops/admin.agekey` (`.pub`) | your age key: decrypts and edits every SOPS-encrypted Secret in `alice/gitops`. **Keep a copy off this host** |
| `sops/<cluster>.agekey` (`.pub`) | a cluster's age key (also in the cluster as `argocd/sops-age`) |
| `forgejo/` | Forgejo users' passwords and tokens, webhook secrets, the gitops push key, Keycloak client `forgejo` ([forgejo](vms/forgejo.md#files)) |
| `oauth/backups/`, `forgejo/backups/` | objects as they were before Crossplane took them over (mode 600) |
| `pki/backup/` | CA backups (CA private keys) |
| `backup/talos-backup-age.key` | the etcd backups' decryption key. **Keep a copy off this host** |

Outside the tree (to be moved in): `/root/lab/opnsense_key` (OPNsense API key,
planned as `opnsense/api-key`), `/root/lab/forgejo-test/` (Forgejo `gitadmin`,
`argocd-reader`, the read-only gitops deploy key, the Forgejo VM's key).

Back the tree up separately, e.g. to an encrypted store.
