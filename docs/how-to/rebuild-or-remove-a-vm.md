# Rebuild or remove a VM

> How-to · [Documentation](../../README.md#documentation)

Re-create a broken VM from the playbooks, or take one away. What comes back
and what doesn't: [Playbooks](../reference/playbooks.md#what-the-playbooks-dont-restore).

## Rebuild

1. Back up its data first if the VM still runs ([Back up the services](back-up-the-services.md)).
2. Remove the VM (below), then run its playbook:

   ```sh
   cd /root/lab/infra/ansible && ansible-playbook <service>.yml
   ```

   It creates the VM (same MAC, so the same address and name), installs the
   service, and restores its configuration and credentials: the same
   certificates (`pki` from its backup), client secrets, tokens and keys.
3. Restore its data from your backup.
4. Check: the service answers ([Getting started, step 1](../tutorials/getting-started.md#1-check-the-shared-services)).

**Never rebuild `forgejo` without a `forgejo dump`**: nothing else holds the
repositories.

## Remove

```sh
virsh destroy <vm>; virsh undefine <vm> --remove-all-storage
```

| VM | Also | Lost with it |
|---|---|---|
| `pki` | | nothing, if `/root/lab/lab-secrets/pki/backup/` is current |
| `oauth` | | users and their group memberships, unless dumped |
| `forgejo` | | **every repository** |
| `backup` | | the etcd backups |
| `registry` | | pushed images and Harbor's database (proxy caches refill; Crossplane recreates projects and robots) |
| `artifacts` | `systemctl disable --now artifact-keeper` first; delete its router entry (`opnsense-dns.py remove --owner infra-ansible:artifact_keeper`) | packages and its database |
| `omni` | remove the group `omni` from the inventory | Omni's data; an imported cluster keeps Omni's documents until its backed-up configs are applied |

## Remove a bucket or a user from RustFS

The role adds buckets and users but never removes them. On `backup`:

```sh
sudo /usr/local/bin/rc bucket remove --force local/<bucket>
sudo /usr/local/bin/rc admin user rm local/<user>
sudo /usr/local/bin/rc admin policy rm local/<policy>
```

Then remove them from `ansible/inventory/group_vars/s3.yml`.
